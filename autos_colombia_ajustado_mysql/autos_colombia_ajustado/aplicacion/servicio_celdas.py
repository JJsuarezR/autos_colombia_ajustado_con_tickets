"""Reglas de negocio para la gestión de celdas y disponibilidad (Iteración 2)."""

import re
from persistencia.conexion import conectar
from persistencia.celda_repository import CeldaRepository
from persistencia.auditoria_repository import AuditoriaRepository

RE_CODIGO_CELDA = re.compile(r"^[A-Z]{1,3}-?\d{1,4}$")


class ServicioCeldas:
    def __init__(self, config):
        self.config = config
        self.celdas = CeldaRepository()
        self.auditoria = AuditoriaRepository()

    def consultar_celdas(self, codigo=None, tipo=None, zona=None, estado=None):
        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                resumen = self.celdas.resumen(cur)
                lista = self.celdas.listar(cur, codigo=codigo, tipo=tipo, zona=zona, estado=estado)
                zonas = self.celdas.listar_zonas(cur)
                for item in lista:
                    mins = item.get("minutos_transcurridos")
                    if mins is not None and mins >= 0:
                        item["permanencia_actual"] = f"{mins // 60} h {mins % 60:02d} min"
                    else:
                        item["permanencia_actual"] = None
                return resumen, lista, zonas
        finally:
            conn.close()

    def crear_celda(self, codigo, numero, tipo, zona, admin_id):
        codigo = (codigo or "").strip().upper()
        tipo = (tipo or "").strip().upper()
        zona = (zona or "").strip()

        if not RE_CODIGO_CELDA.fullmatch(codigo):
            raise ValueError("Código inválido. Use un formato como C-71 o M-11.")
        try:
            numero_int = int(numero)
            if numero_int <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError("El número de celda debe ser un entero positivo.")

        if tipo not in ("CARRO", "MOTO"):
            raise ValueError("Seleccione si la celda es para CARRO o MOTO.")
        if not zona or len(zona) < 2:
            raise ValueError("Indique la zona o ubicación de la celda (ej. Zona A).")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                dup = self.celdas.existe_codigo_o_numero(cur, codigo, tipo, numero_int)
                if dup:
                    raise ValueError(f"Ya existe una celda con código '{dup['codigo']}' o número {numero_int} para {tipo.lower()}.")

                celda_id = self.celdas.crear(cur, codigo, numero_int, tipo, zona)
                self.auditoria.registrar(
                    cur, admin_id, "CELDA", celda_id, "CREAR",
                    f"Creó celda {codigo} (N° {numero_int}, {tipo}, {zona})."
                )
            conn.commit()
            return celda_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def modificar_celda(self, celda_id, tipo, zona, estado, admin_id):
        """Permite al Administrador editar tipo, zona y estado (Disponible/Ocupada) de una celda."""
        tipo = (tipo or "").strip().upper()
        zona = (zona or "").strip()
        estado = (estado or "").strip().capitalize()

        if tipo not in ("CARRO", "MOTO"):
            raise ValueError("El tipo de vehículo de la celda debe ser CARRO o MOTO.")
        if not zona or len(zona) < 2:
            raise ValueError("Indique una zona o ubicación válida para la celda.")
        if estado not in ("Disponible", "Ocupada"):
            raise ValueError("El estado de la celda debe ser Disponible u Ocupada.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                actual = self.celdas.buscar_por_id(cur, celda_id, bloquear=True)
                if not actual:
                    raise ValueError("La celda seleccionada no existe.")

                # Verificar si tiene una estancia activa asociada
                cur.execute("SELECT id FROM estancia WHERE celda_activa_id=%s", (celda_id,))
                estancia_activa = cur.fetchone()

                if estancia_activa:
                    if actual["tipo"] != tipo:
                        raise ValueError(
                            f"La celda {actual['codigo']} tiene un vehículo activo dentro; no puede cambiar su tipo de vehículo hasta registrar la salida."
                        )
                    if estado == "Disponible":
                        raise ValueError(
                            f"La celda {actual['codigo']} tiene un vehículo con estancia activa dentro. Para liberarla registre la salida del vehículo en el módulo 'Salida'."
                        )

                self.celdas.actualizar(cur, celda_id, tipo, zona, estado)
                self.auditoria.registrar(
                    cur, admin_id, "CELDA", celda_id, "MODIFICAR",
                    f"Modificó celda {actual['codigo']}: tipo {actual['tipo']}->{tipo}, zona '{actual['zona']}'->'{zona}', estado {actual['estado']}->{estado}."
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
