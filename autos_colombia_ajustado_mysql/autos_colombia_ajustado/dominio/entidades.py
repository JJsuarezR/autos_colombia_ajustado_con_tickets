"""Entidades principales del dominio Autos Colombia."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Vehiculo:
    id: int
    placa: str
    tipo: str  # CARRO o MOTO
    marca: Optional[str] = None
    color: Optional[str] = None
    propietario: Optional[str] = None


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
class Suscripcion:
    id: int
    vehiculo_id: int
    propietario: str
    fecha_inicio: date
    fecha_vencimiento: date
    estado: str  # ACTIVA o VENCIDA


@dataclass
class PagoMensualidad:
    id: int
    comprobante_codigo: str
    suscripcion_id: int
    vehiculo_id: int
    propietario: str
    tipo_vehiculo: str
    periodo_etiqueta: str
    fecha_inicio_periodo: date
    fecha_fin_periodo: date
    valor: Decimal
    metodo_pago: str
    estado: str  # APROBADO o ANULADO
    operador_id: int
    fecha_pago: datetime
    anulado_por_id: Optional[int] = None
    fecha_anulacion: Optional[datetime] = None
    motivo_anulacion: Optional[str] = None


@dataclass
class AuditoriaSistema:
    id: int
    operador_id: Optional[int]
    entidad: str
    entidad_id: Optional[int]
    accion: str
    detalle: str
    creado_en: Optional[datetime] = None
