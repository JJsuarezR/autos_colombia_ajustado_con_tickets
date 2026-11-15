"""Entidades principales del dominio Autos Colombia."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Vehiculo:
    id: int
    placa: str
    tipo: str  # CARRO o MOTO
    marca: Optional[str] = None
    color: Optional[str] = None


@dataclass
class Celda:
    id: int
    codigo: str
    numero: int
    tipo: str
    estado: str
    zona: str = "General"


@dataclass
class Operador:
    id: int
    nombre: str
    usuario: str
    rol: str
    correo: Optional[str] = None
    activo: bool = True
    creado_en: Optional[datetime] = None


@dataclass
class Estancia:
    id: int
    vehiculo_id: int
    celda_id: int
    operador_entrada_id: int
    operador_salida_id: Optional[int]
    fecha_entrada: datetime
    fecha_salida: Optional[datetime]
    ticket_codigo: Optional[str] = None


@dataclass
class AuditoriaSistema:
    id: int
    operador_id: Optional[int]
    entidad: str
    entidad_id: Optional[int]
    accion: str
    detalle: str
    creado_en: Optional[datetime] = None
