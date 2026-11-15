"""Reglas de negocio para la gestión y consulta de celdas (Iteración 2)."""

import math
import re
from datetime import datetime
from persistencia.conexion import conectar
from persistencia.celda_repository import CeldaRepository
from persistencia.auditoria_repository import AuditoriaRepository

RE_CODIGO_CELDA = re.compile(r"^[A-Z0-9-]{2,10}$")


class ServicioCeldas:
    def __init__(self, config):
        self.config = config
        self.celdas = CeldaRepository()
        self.auditoria = AuditoriaRepository()

    @staticmethod
    def calcular_permanencia(fecha_entrada):
        if not fecha_entrada:
            return "—"
        ahora = datetime.now().replace(microsecond=0)
        minutos = max(0, math.ceil((ahora - fecha_entrada).total_seconds() / 60))
        return f"{minutos // 60} h {minutos % 60:02d} min"

    def consultar_celdas(self, codigo=None, tipo=None, zona=None, estado=None):
        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                resumen = self.celdas.resumen(cur)
                lista = self.celdas.listar(cur, codigo=codigo, tipo=tipo, zona=zona, estado=estado)
                zonas = self.celdas.listar_zonas(cur)
                for c in lista:
                    c["permanencia_actual"] = (
                        self.calcular_permanencia(c["fecha_entrada"])
                        if c["estado"] == "Ocupada" else "—"
                    )
                return resumen, lista, zonas
        finally:
            conn.close()

    def modificar_celda(self, celda_id, tipo, zona, operador_id):
        tipo = (tipo or "").strip().upper()
        zona = (zona or "").strip()

        if tipo not in ("CARRO", "MOTO"):
            raise ValueError("El tipo de celda debe ser CARRO o MOTO.")
        if not zona or len(zona) > 60:
            raise ValueError("Ingrese una zona o ubicación válida (1 a 60 caracteres).")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                celda = self.celdas.buscar_por_id(cur, celda_id, bloquear=True)
                if not celda:
                    raise ValueError("La celda indicada no existe.")
                if celda["estado"] == "Ocupada":
                    raise ValueError(
                        f"No se puede modificar la celda {celda['codigo']} mientras se encuentre Ocupada."
                    )

                if celda["tipo"] != tipo:
                    duplicada = self.celdas.existe_codigo_o_numero(
                        cur, celda["codigo"], tipo, celda["numero"], excluir_id=celda_id
                    )
                    if duplicada:
                        raise ValueError(
                            f"Ya existe una celda número {celda['numero']} para tipo {tipo}."
                        )

                filas = self.celdas.actualizar(cur, celda_id, tipo, zona)
                if filas == 0:
                    raise ValueError("No fue posible actualizar la celda; verifique su estado.")

                self.auditoria.registrar(
                    cur, operador_id, "CELDA", celda_id, "MODIFICAR",
                    f"Modificó celda {celda['codigo']}: tipo={tipo}, zona='{zona}'."
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def crear_celda(self, codigo, numero, tipo, zona, operador_id):
        codigo = re.sub(r"\s+", "", (codigo or "")).upper()
        tipo = (tipo or "").strip().upper()
        zona = (zona or "").strip()

        if not RE_CODIGO_CELDA.fullmatch(codigo):
            raise ValueError("Código de celda inválido (ej: C-71 o M-11).")
        try:
            numero_int = int(numero)
            if numero_int <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError("El número de celda debe ser un entero positivo.")

        if tipo not in ("CARRO", "MOTO"):
            raise ValueError("El tipo debe ser CARRO o MOTO.")
        if not zona or len(zona) > 60:
            raise ValueError("Ingrese una zona o ubicación válida (1 a 60 caracteres).")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                duplicada = self.celdas.existe_codigo_o_numero(cur, codigo, tipo, numero_int)
                if duplicada:
                    raise ValueError(
                        f"Ya existe una celda con código '{duplicada['codigo']}' o número {numero_int} para {tipo}."
                    )
                nueva_id = self.celdas.crear(cur, codigo, numero_int, tipo, zona)
                self.auditoria.registrar(
                    cur, operador_id, "CELDA", nueva_id, "CREAR",
                    f"Creó celda {codigo} (#{numero_int}, {tipo}, zona='{zona}')."
                )
            conn.commit()
            return nueva_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
