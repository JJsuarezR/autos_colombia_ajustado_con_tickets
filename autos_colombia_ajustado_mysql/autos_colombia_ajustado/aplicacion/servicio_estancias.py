"""Reglas de negocio para registrar vehículos, entradas y salidas."""

import math
import re
from datetime import datetime
from persistencia.conexion import conectar
from persistencia.vehiculo_repository import VehiculoRepository
from persistencia.celda_repository import CeldaRepository
from persistencia.estancia_repository import EstanciaRepository
from persistencia.auditoria_repository import AuditoriaRepository

RE_CARRO = re.compile(r"^[A-Z]{3}\d{3}$")       # Ejemplo: ABC123
RE_MOTO = re.compile(r"^[A-Z]{3}\d{2}[A-Z]?$")  # Ejemplo: ABC12 o ABC12D


class ServicioEstancias:
    def __init__(self, config):
        self.config = config
        self.vehiculos = VehiculoRepository()
        self.celdas = CeldaRepository()
        self.estancias = EstanciaRepository()
        self.auditoria = AuditoriaRepository()

    @staticmethod
    def normalizar_placa(placa):
        return re.sub(r"[\s-]", "", (placa or "")).upper()

    @staticmethod
    def normalizar_referencia_salida(valor):
        """Conserva guiones si es un código de ticket (AC-YYYYMMDD-000001) y limpia espacios."""
        return re.sub(r"\s+", "", (valor or "")).upper()

    def registrar_vehiculo(self, placa, tipo, marca, color, operador_id=None):
        """Opción 1 de Entrada: Registra un vehículo nuevo en el catálogo (o completa marca/color si estaba incompleto)."""
        placa = self.normalizar_placa(placa)
        tipo = (tipo or "").strip().upper()
        marca = (marca or "").strip()
        color = (color or "").strip()

        if not placa:
            raise ValueError("Ingrese la placa del vehículo.")
        if tipo not in ("CARRO", "MOTO"):
            raise ValueError("Seleccione si el vehículo es CARRO o MOTO.")

        patron = RE_CARRO if tipo == "CARRO" else RE_MOTO
        if not patron.fullmatch(placa):
            ejemplo = "ABC123" if tipo == "CARRO" else "ABC12 o ABC12D"
            raise ValueError(f"Placa inválida para {tipo.lower()}. Formato esperado: {ejemplo}.")

        if not marca or not color:
            raise ValueError("Debe diligenciar tanto la marca como el color del vehículo.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                existente = self.vehiculos.buscar_por_placa(cur, placa)
                if existente:
                    if existente.get("marca") and existente.get("color"):
                        raise ValueError(
                            f"El vehículo con placa {placa} ya se encuentra registrado ({existente['tipo']} · {existente['marca']} {existente['color']}). Puede darle entrada directamente."
                        )
                    self.vehiculos.completar_datos(cur, existente["id"], marca, color)
                    vehiculo_id = existente["id"]
                    accion = "COMPLETAR_VEHICULO"
                    detalle = f"Completó marca y color del vehículo existente {placa}: {marca} {color}."
                else:
                    vehiculo_id = self.vehiculos.crear(cur, placa, tipo, marca, color)
                    accion = "REGISTRAR_VEHICULO"
                    detalle = f"Registró vehículo nuevo {placa} ({tipo} · {marca} {color})."

                if operador_id:
                    self.auditoria.registrar(cur, operador_id, "VEHICULO", vehiculo_id, accion, detalle)
            conn.commit()
            return placa
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def registrar_entrada(self, placa, operador_id):
        """Opción 2 de Entrada: Registra el ingreso al parqueadero únicamente si el vehículo ya existe en el sistema."""
        placa = self.normalizar_placa(placa)
        if not placa:
            raise ValueError("Ingrese la placa del vehículo que va a ingresar.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                vehiculo = self.vehiculos.buscar_por_placa(cur, placa)
                if not vehiculo:
                    raise ValueError(
                        f"La placa {placa} no está registrada. Regístrela primero en la opción '1. Registrar vehículo nuevo'."
                    )
                if not vehiculo.get("marca") or not vehiculo.get("color"):
                    raise ValueError(
                        f"El vehículo {placa} tiene datos incompletos (marca/color). Complételos primero en '1. Registrar vehículo nuevo'."
                    )

                tipo = vehiculo["tipo"]
                vehiculo_id = vehiculo["id"]

                if self.estancias.vehiculo_tiene_estancia_activa(cur, vehiculo_id):
                    raise ValueError(f"El vehículo {placa} ya tiene una entrada activa en el parqueadero.")

                celda = self.celdas.buscar_disponible(cur, tipo)
                if not celda:
                    raise ValueError(f"No hay celdas disponibles para {tipo.lower()}.")

                ahora = datetime.now().replace(microsecond=0)
                estancia_id = self.estancias.crear(cur, vehiculo_id, celda["id"], operador_id, ahora)
                ticket_codigo = f"AC-{ahora:%Y%m%d}-{estancia_id:06d}"
                self.estancias.asignar_ticket(cur, estancia_id, ticket_codigo)
                self.celdas.cambiar_estado(cur, celda["id"], "Ocupada")
            conn.commit()
            return estancia_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def registrar_salida(self, placa_o_ticket, operador_id):
        """Registra la salida buscando por placa (ej. ABC123) o por código de ticket (ej. AC-20261114-000001)."""
        referencia = self.normalizar_referencia_salida(placa_o_ticket)
        if not referencia:
            raise ValueError("Ingrese la placa del vehículo o el código del ticket.")

        # Si el usuario digitó una placa con espacios o guiones (ej. ABC-123) que no inicia con AC-, la normalizamos como placa
        if not referencia.startswith("AC-"):
            referencia = self.normalizar_placa(referencia)

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                estancia = self.estancias.buscar_activa_por_placa_o_ticket(cur, referencia)
                if not estancia:
                    raise ValueError(
                        f"No existe una entrada activa asociada a la placa o ticket '{referencia}'."
                    )
                ahora = datetime.now().replace(microsecond=0)
                self.estancias.cerrar(cur, estancia["id"], operador_id, ahora)
                self.celdas.cambiar_estado(cur, estancia["celda_id"], "Disponible")
                minutos = max(0, math.ceil((ahora - estancia["fecha_entrada"]).total_seconds() / 60))
                permanencia = f"{minutos // 60} h {minutos % 60:02d} min"
                codigo = estancia["codigo"]
                placa = estancia["placa"]
                ticket = estancia.get("ticket_codigo") or "Sin ticket"
            conn.commit()
            return codigo, permanencia, placa, ticket
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
