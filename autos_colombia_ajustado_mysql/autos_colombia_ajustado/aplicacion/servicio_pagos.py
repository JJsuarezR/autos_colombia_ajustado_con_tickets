"""Reglas de negocio para pagos de mensualidad, suscripciones y reportes (Iteración 3)."""

import calendar
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from persistencia.conexion import conectar
from persistencia.vehiculo_repository import VehiculoRepository
from persistencia.suscripcion_repository import SuscripcionRepository
from persistencia.pago_repository import PagoRepository
from persistencia.auditoria_repository import AuditoriaRepository

TARIFAS_MENSUALIDAD = {
    "CARRO": Decimal("250000"),
    "MOTO": Decimal("100000"),
}

METODOS_PAGO_VALIDOS = (
    "Efectivo",
    "Tarjeta débito/crédito",
    "Transferencia",
)

MESES_ES = (
    "", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
)


class ServicioPagos:
    def __init__(self, config):
        self.config = config
        self.vehiculos = VehiculoRepository()
        self.suscripciones = SuscripcionRepository()
        self.pagos = PagoRepository()
        self.auditoria = AuditoriaRepository()

    @staticmethod
    def normalizar_placa(placa):
        return re.sub(r"[\s-]", "", (placa or "")).upper()

    @staticmethod
    def calcular_tarifa(tipo_vehiculo):
        tipo = (tipo_vehiculo or "").strip().upper()
        if tipo not in TARIFAS_MENSUALIDAD:
            raise ValueError("Tipo de vehículo inválido para cálculo de tarifa.")
        return TARIFAS_MENSUALIDAD[tipo]

    @staticmethod
    def sumar_un_mes(fecha_base):
        """Calcula el vencimiento exacto a 1 mes calendario manteniendo el día válido."""
        anio = fecha_base.year + (1 if fecha_base.month == 12 else 0)
        mes = 1 if fecha_base.month == 12 else fecha_base.month + 1
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        dia = min(fecha_base.day, ultimo_dia)
        return date(anio, mes, dia)

    @staticmethod
    def formatear_periodo(fecha_inicio, fecha_fin):
        return (
            f"{MESES_ES[fecha_inicio.month]} {fecha_inicio.day:02d}, {fecha_inicio.year} — "
            f"{MESES_ES[fecha_fin.month]} {fecha_fin.day:02d}, {fecha_fin.year}"
        )

    def _evaluar_vigencia(self, fecha_vencimiento):
        hoy = date.today()
        if not fecha_vencimiento:
            return {
                "tiene_suscripcion": False,
                "activa": False,
                "estado_texto": "SIN SUSCRIPCIÓN",
                "dias_restantes": 0,
            }
        dias = (fecha_vencimiento - hoy).days
        activa = fecha_vencimiento >= hoy
        return {
            "tiene_suscripcion": True,
            "activa": activa,
            "estado_texto": "ACTIVA" if activa else "VENCIDA",
            "dias_restantes": dias,
        }

    def consultar_suscripcion(self, placa):
        """Consulta vehículo, vigencia de suscripción y cálculo de tarifa/periodo siguiente (HU-02)."""
        placa = self.normalizar_placa(placa)
        if not placa:
            raise ValueError("Ingrese la placa del vehículo a consultar.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                vehiculo = self.vehiculos.buscar_por_placa(cur, placa)
                if not vehiculo:
                    raise ValueError(
                        f"El vehículo con placa {placa} no está registrado en el sistema. Regístrelo primero en el módulo Entrada."
                    )
                suscripcion = self.suscripciones.buscar_por_vehiculo_id(cur, vehiculo["id"])
                vigencia = self._evaluar_vigencia(
                    suscripcion["fecha_vencimiento"] if suscripcion else None
                )
                tarifa = self.calcular_tarifa(vehiculo["tipo"])
                hoy = date.today()

                # Si la suscripción está vigente, la renovación extiende desde el vencimiento actual; si no, desde hoy.
                if suscripcion and suscripcion["fecha_vencimiento"] >= hoy:
                    inicio_sugerido = suscripcion["fecha_vencimiento"] + timedelta(days=1)
                else:
                    inicio_sugerido = hoy
                fin_sugerido = self.sumar_un_mes(inicio_sugerido)

                return {
                    "vehiculo": vehiculo,
                    "suscripcion": suscripcion,
                    "vigencia": vigencia,
                    "tarifa": tarifa,
                    "inicio_sugerido": inicio_sugerido,
                    "fin_sugerido": fin_sugerido,
                    "periodo_sugerido": self.formatear_periodo(inicio_sugerido, fin_sugerido),
                    "propietario_sugerido": (
                        (suscripcion["propietario"] if suscripcion else None)
                        or vehiculo.get("propietario")
                        or ""
                    ),
                }
        finally:
            conn.close()

    def registrar_pago_mensual(self, placa, propietario, metodo_pago, operador_id):
        """Valida vehículo, calcula tarifa fija ($250.000 carro / $100.000 moto), actualiza vigencia y genera comprobante (HU-01)."""
        placa = self.normalizar_placa(placa)
        propietario = (propietario or "").strip()
        metodo_pago = (metodo_pago or "").strip()

        if not placa:
            raise ValueError("Ingrese la placa del vehículo.")
        if not propietario or len(propietario) < 3:
            raise ValueError("Ingrese el nombre completo del propietario / suscriptor.")
        if metodo_pago not in METODOS_PAGO_VALIDOS:
            raise ValueError("Seleccione un método de pago válido.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                vehiculo = self.vehiculos.buscar_por_placa(cur, placa)
                if not vehiculo:
                    raise ValueError(
                        f"El vehículo {placa} no existe en el sistema. Regístrelo primero en Entrada antes de cobrar la mensualidad."
                    )

                tarifa = self.calcular_tarifa(vehiculo["tipo"])
                hoy = date.today()
                ahora = datetime.now().replace(microsecond=0)

                suscripcion = self.suscripciones.buscar_por_vehiculo_id(
                    cur, vehiculo["id"], bloquear=True
                )

                if not suscripcion:
                    fecha_inicio_periodo = hoy
                    fecha_fin_periodo = self.sumar_un_mes(fecha_inicio_periodo)
                    suscripcion_id = self.suscripciones.crear(
                        cur, vehiculo["id"], propietario, fecha_inicio_periodo, fecha_fin_periodo
                    )
                else:
                    suscripcion_id = suscripcion["id"]
                    if suscripcion["fecha_vencimiento"] >= hoy:
                        fecha_inicio_periodo = suscripcion["fecha_vencimiento"] + timedelta(days=1)
                        nueva_fecha_inicio_suscripcion = suscripcion["fecha_inicio"]
                    else:
                        fecha_inicio_periodo = hoy
                        nueva_fecha_inicio_suscripcion = hoy
                    fecha_fin_periodo = self.sumar_un_mes(fecha_inicio_periodo)

                    duplicado = self.pagos.existe_pago_periodo_activo(
                        cur, vehiculo["id"], fecha_inicio_periodo, fecha_fin_periodo
                    )
                    if duplicado:
                        raise ValueError(
                            f"Ya existe un pago aprobado ({duplicado['comprobante_codigo']}) para ese mismo periodo."
                        )

                    self.suscripciones.actualizar_vigencia(
                        cur,
                        suscripcion_id,
                        propietario,
                        nueva_fecha_inicio_suscripcion,
                        fecha_fin_periodo,
                        estado="ACTIVA",
                    )

                self.vehiculos.actualizar_propietario(cur, vehiculo["id"], propietario)

                periodo_etiqueta = self.formatear_periodo(fecha_inicio_periodo, fecha_fin_periodo)
                pago_id = self.pagos.crear(
                    cur,
                    f"TMP-{ahora:%Y%m%d%H%M%S}-{vehiculo['id']}",
                    suscripcion_id,
                    vehiculo["id"],
                    propietario,
                    vehiculo["tipo"],
                    periodo_etiqueta,
                    fecha_inicio_periodo,
                    fecha_fin_periodo,
                    tarifa,
                    metodo_pago,
                    operador_id,
                    ahora,
                )
                comprobante_codigo = f"PAG-{ahora:%Y%m%d}-{pago_id:05d}"
                self.pagos.asignar_comprobante(cur, pago_id, comprobante_codigo)

                self.auditoria.registrar(
                    cur,
                    operador_id,
                    "PAGO",
                    pago_id,
                    "REGISTRAR_PAGO",
                    f"Registró pago {comprobante_codigo} para {placa} ({vehiculo['tipo']}) por ${int(tarifa):,} ({metodo_pago}). Vigencia hasta {fecha_fin_periodo}."
                )
            conn.commit()
            return pago_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def anular_pago(self, pago_id, motivo, admin_id):
        """Anula un pago por error (solo Administrador), registra auditoría y recalcula vigencia (RF-08, RNF-06)."""
        motivo = (motivo or "").strip()
        if not motivo or len(motivo) < 5:
            raise ValueError("Debe indicar un motivo claro de anulación (mínimo 5 caracteres).")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                pago = self.pagos.buscar_por_id(cur, pago_id, bloquear=True)
                if not pago:
                    raise ValueError("El pago seleccionado no existe.")
                if pago["estado"] == "ANULADO":
                    raise ValueError(f"El comprobante {pago['comprobante_codigo']} ya se encuentra anulado.")

                filas = self.pagos.anular(cur, pago_id, admin_id, motivo)
                if filas == 0:
                    raise ValueError("No fue posible anular el pago.")

                # Recalcular vigencia de la suscripción con base en el último pago aprobado restante
                suscripcion = self.suscripciones.buscar_por_id(cur, pago["suscripcion_id"], bloquear=True)
                ultimo_valido = self.pagos.buscar_ultimo_pago_aprobado(
                    cur, pago["suscripcion_id"], excluir_pago_id=pago_id
                )
                hoy = date.today()
                if ultimo_valido:
                    nueva_venc = ultimo_valido["fecha_fin_periodo"]
                    nuevo_estado = "ACTIVA" if nueva_venc >= hoy else "VENCIDA"
                    self.suscripciones.actualizar_vigencia(
                        cur,
                        suscripcion["id"],
                        suscripcion["propietario"],
                        suscripcion["fecha_inicio"],
                        nueva_venc,
                        estado=nuevo_estado,
                    )
                else:
                    venc_vencida = hoy - timedelta(days=1)
                    self.suscripciones.actualizar_vigencia(
                        cur,
                        suscripcion["id"],
                        suscripcion["propietario"],
                        suscripcion["fecha_inicio"],
                        venc_vencida,
                        estado="VENCIDA",
                    )

                self.auditoria.registrar(
                    cur,
                    admin_id,
                    "PAGO",
                    pago_id,
                    "ANULAR_PAGO",
                    f"Anuló pago {pago['comprobante_codigo']} ({pago['placa']}, ${int(pago['valor']):,}). Motivo: {motivo}"
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
