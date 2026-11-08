"""Reglas de negocio para registrar entradas y salidas."""

import math
import re
from datetime import datetime
from persistencia.conexion import conectar
from persistencia.vehiculo_repository import VehiculoRepository
from persistencia.celda_repository import CeldaRepository
from persistencia.estancia_repository import EstanciaRepository

RE_CARRO = re.compile(r"^[A-Z]{3}\d{3}$")       # Ejemplo: ABC123
RE_MOTO = re.compile(r"^[A-Z]{3}\d{2}[A-Z]?$")  # Ejemplo: ABC12 o ABC12D

class ServicioEstancias:
    def __init__(self, config):
        self.config = config
        self.vehiculos = VehiculoRepository()
        self.celdas = CeldaRepository()
        self.estancias = EstanciaRepository()

    @staticmethod
    def normalizar_placa(placa):
        return re.sub(r"[\s-]", "", (placa or "")).upper()

    def registrar_entrada(self, placa, tipo, operador_id, marca=None, color=None):
        placa = self.normalizar_placa(placa)
        if not placa:
            raise ValueError("Ingrese la placa del vehículo.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                vehiculo = self.vehiculos.buscar_por_placa(cur, placa)
                if not vehiculo:
                    if tipo not in ("CARRO", "MOTO"):
                        raise ValueError("Seleccione si el vehículo es carro o moto.")
                    patron = RE_CARRO if tipo == "CARRO" else RE_MOTO
                    if not patron.fullmatch(placa):
                        ejemplo = "ABC123" if tipo == "CARRO" else "ABC12 o ABC12D"
                        raise ValueError(f"Placa inválida para {tipo.lower()}. Formato esperado: {ejemplo}.")
                    marca = (marca or "").strip()
                    color = (color or "").strip()
                    if not marca or not color:
                        raise ValueError("Para registrar un vehículo nuevo debe indicar la marca y el color.")
                    vehiculo_id = self.vehiculos.crear(cur, placa, tipo, marca, color)
                else:
                    tipo = vehiculo["tipo"]
                    vehiculo_id = vehiculo["id"]
                    if not vehiculo.get("marca") or not vehiculo.get("color"):
                        marca = (marca or "").strip()
                        color = (color or "").strip()
                        if not marca or not color:
                            raise ValueError("Esta placa ya existe, pero faltan la marca o el color. Complete ambos datos para continuar.")
                        self.vehiculos.completar_datos(cur, vehiculo_id, marca, color)
                if self.estancias.vehiculo_tiene_estancia_activa(cur, vehiculo_id):
                    raise ValueError(f"El vehículo {placa} ya tiene una entrada activa.")
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

    def registrar_salida(self, placa, operador_id):
        placa = self.normalizar_placa(placa)
        if not placa:
            raise ValueError("Ingrese la placa del vehículo.")
        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                estancia = self.estancias.buscar_activa_por_placa(cur, placa)
                if not estancia:
                    raise ValueError(f"No existe una entrada activa para la placa {placa}.")
                ahora = datetime.now().replace(microsecond=0)
                self.estancias.cerrar(cur, estancia["id"], operador_id, ahora)
                self.celdas.cambiar_estado(cur, estancia["celda_id"], "Disponible")
                minutos = max(0, math.ceil((ahora - estancia["fecha_entrada"]).total_seconds()/60))
                permanencia = f"{minutos // 60} h {minutos % 60:02d} min"
                codigo = estancia["codigo"]
            conn.commit()
            return codigo, permanencia
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
