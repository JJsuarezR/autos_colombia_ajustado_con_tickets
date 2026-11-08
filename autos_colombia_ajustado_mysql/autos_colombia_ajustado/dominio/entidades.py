"""Entidades principales del dominio Autos Colombia."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Vehiculo:
    id: int
    placa: str
    tipo: str  # CARRO o MOTO

@dataclass
class Celda:
    id: int
    codigo: str
    numero: int
    tipo: str
    estado: str

@dataclass
class Operador:
    id: int
    nombre: str
    usuario: str
    rol: str

@dataclass
class Estancia:
    id: int
    vehiculo_id: int
    celda_id: int
    operador_entrada_id: int
    operador_salida_id: Optional[int]
    fecha_entrada: datetime
    fecha_salida: Optional[datetime]
