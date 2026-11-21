"""Controladores HTTP: reciben solicitudes y delegan las reglas a los servicios."""

import csv
import io
from datetime import date
import pymysql
from functools import wraps
from flask import (Response, current_app, flash, redirect, render_template,
                   request, session, url_for)
from persistencia.conexion import conectar
from persistencia.celda_repository import CeldaRepository
from persistencia.estancia_repository import EstanciaRepository
from persistencia.operador_repository import OperadorRepository
from persistencia.vehiculo_repository import VehiculoRepository
from persistencia.suscripcion_repository import SuscripcionRepository
from persistencia.pago_repository import PagoRepository
from persistencia.auditoria_repository import AuditoriaRepository
from aplicacion.servicio_estancias import ServicioEstancias
from aplicacion.servicio_usuarios import ServicioUsuarios
from aplicacion.servicio_celdas import ServicioCeldas
from aplicacion.servicio_pagos import METODOS_PAGO_VALIDOS, TARIFAS_MENSUALIDAD, ServicioPagos


def registrar_controladores(app):
    servicio = ServicioEstancias(app.config)
    servicio_usuarios = ServicioUsuarios(app.config)
    servicio_celdas = ServicioCeldas(app.config)
    servicio_pagos = ServicioPagos(app.config)

    celdas_repo = CeldaRepository()
    estancias_repo = EstanciaRepository()
    operadores_repo = OperadorRepository()
    vehiculos_repo = VehiculoRepository()
    suscripciones_repo = SuscripcionRepository()
    pagos_repo = PagoRepository()
    auditoria_repo = AuditoriaRepository()

    def conexion():
        return conectar(current_app.config)

    def requiere_sesion(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            if not session.get("operador_id"):
                return redirect(url_for("login"))
            return func(*args, **kwargs)
        return envoltura

    def requiere_admin(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            if not session.get("operador_id"):
                return redirect(url_for("login"))
            if session.get("operador_rol") != "ADMIN":
                flash("Esta opción está disponible solo para el administrador.", "error")
                return redirect(url_for("panel"))
            return func(*args, **kwargs)
        return envoltura

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            identificador = request.form.get("usuario", "").strip()
            password = request.form.get("password", "")
            try:
                operador = servicio_usuarios.autenticar(identificador, password)
                session.clear()
                session["operador_id"] = operador["id"]
                session["operador_nombre"] = operador["nombre"]
                session["operador_rol"] = operador["rol"]
                return redirect(url_for("panel"))
            except ValueError as err:
                flash(str(err), "error")
        return render_template("login.html")

    @app.get("/cerrar-sesion")
    def cerrar_sesion():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @requiere_sesion
    def panel():
        conn = conexion()
        try:
            with conn.cursor() as cur:
                resumen = celdas_repo.resumen(cur)
                celdas = celdas_repo.listar(cur)
                activos = estancias_repo.listar_activas(cur)
                historial = estancias_repo.ultimas_salidas(cur)
                kpis_pagos = pagos_repo.resumen_kpis_mes_actual(cur)
                por_vencer = suscripciones_repo.contar_por_vencer(cur, dias=5)
        finally:
            conn.close()
        return render_template(
            "index.html",
            resumen=resumen,
            celdas=celdas,
            activos=activos,
            historial=historial,
            kpis_pagos=kpis_pagos,
            por_vencer=por_vencer,
        )

    @app.route("/entrada", methods=["GET", "POST"])
    @requiere_sesion
    def entrada():
        placa_preseleccionada = servicio.normalizar_placa(request.args.get("placa", ""))
        buscar_placa = servicio.normalizar_placa(request.args.get("buscar_placa", ""))
        editar_id = request.args.get("editar_vehiculo", "").strip()

        if request.method == "POST":
            accion = request.form.get("accion", "entrada")
            if accion == "registrar_vehiculo":
                try:
                    placa_reg = servicio.registrar_vehiculo(
                        request.form.get("placa"),
                        request.form.get("tipo"),
                        request.form.get("marca"),
                        request.form.get("color"),
                        request.form.get("propietario"),
                        session["operador_id"],
                    )
                    flash(
                        f"Vehículo {placa_reg} registrado correctamente. Recuerde que debe contar con mensualidad vigente para ingresar.",
                        "ok",
                    )
                    return redirect(url_for("entrada", placa=placa_reg))
                except (ValueError, pymysql.err.IntegrityError) as error:
                    flash(str(error) or "No se pudo registrar el vehículo.", "error")
                    return redirect(url_for("entrada"))
            else:
                try:
                    estancia_id = servicio.registrar_entrada(
                        request.form.get("placa"),
                        session["operador_id"],
                    )
                    return redirect(url_for("ticket", estancia_id=estancia_id))
                except (ValueError, pymysql.err.IntegrityError) as error:
                    flash(str(error) or "No se pudo registrar la entrada.", "error")
                    return redirect(url_for("entrada", placa=servicio.normalizar_placa(request.form.get("placa"))))

        conn = conexion()
        try:
            with conn.cursor() as cur:
                vehiculos_todos = vehiculos_repo.listar(cur)
                vehiculos_filtrados = (
                    vehiculos_repo.listar(cur, filtro_placa=buscar_placa)
                    if buscar_placa else vehiculos_todos
                )
                vehiculo_editar = (
                    vehiculos_repo.buscar_por_id(cur, int(editar_id))
                    if editar_id.isdigit() else None
                )
        finally:
            conn.close()
        return render_template(
            "entrada.html",
            vehiculos=vehiculos_filtrados,
            vehiculos_todos=vehiculos_todos,
            vehiculo_editar=vehiculo_editar,
            buscar_placa=buscar_placa,
            placa_preseleccionada=placa_preseleccionada,
            hoy=date.today(),
        )

    @app.post("/vehiculos/<int:vehiculo_id>/editar")
    @requiere_sesion
    def editar_vehiculo(vehiculo_id):
        try:
            placa_act = servicio.editar_vehiculo(
                vehiculo_id,
                request.form.get("placa"),
                request.form.get("tipo"),
                request.form.get("marca"),
                request.form.get("color"),
                request.form.get("propietario"),
                session["operador_id"],
            )
            flash(f"Información del vehículo {placa_act} actualizada correctamente.", "ok")
        except (ValueError, pymysql.err.IntegrityError) as error:
            flash(str(error) or "No se pudo actualizar la información del vehículo.", "error")
            return redirect(url_for("entrada", editar_vehiculo=vehiculo_id))
        return redirect(url_for("entrada"))

    @app.get("/ticket/<int:estancia_id>")
    @requiere_sesion
    def ticket(estancia_id):
        conn = conexion()
        try:
            with conn.cursor() as cur:
                datos = estancias_repo.obtener_ticket(cur, estancia_id)
        finally:
            conn.close()
        if not datos:
            flash("No se encontró el ticket solicitado.", "error")
            return redirect(url_for("panel"))
        return render_template("ticket.html", ticket=datos)

    @app.route("/salida", methods=["GET", "POST"])
    @requiere_sesion
    def salida():
        if request.method == "POST":
            try:
                codigo, permanencia, placa, ticket_cod = servicio.registrar_salida(
                    request.form.get("placa"), session["operador_id"]
                )
                flash(
                    f"Salida registrada para {placa} (Ticket: {ticket_cod}). Celda {codigo} liberada. Permanencia: {permanencia}.",
                    "ok",
                )
            except ValueError as error:
                flash(str(error), "error")
            return redirect(url_for("salida"))
        conn = conexion()
        try:
            with conn.cursor() as cur:
                activos = estancias_repo.listar_activas(cur)
        finally:
            conn.close()
        return render_template("salida.html", activos=activos)

    @app.get("/historial")
    @requiere_sesion
    def historial():
        placa = servicio.normalizar_referencia_salida(request.args.get("placa", ""))
        desde = request.args.get("desde", "")
        hasta = request.args.get("hasta", "")
        if desde and hasta and desde > hasta:
            flash("La fecha inicial no puede ser posterior a la fecha final.", "error")
            return redirect(url_for("historial"))
        conn = conexion()
        try:
            with conn.cursor() as cur:
                registros = estancias_repo.filtrar_historial(cur, placa, desde, hasta)
        finally:
            conn.close()
        return render_template("historial.html", registros=registros,
                               placa=placa, desde=desde, hasta=hasta)

    # --- ITERACIÓN 2: Gestión de Celdas (Edición y creación exclusivas del Administrador) ---
    @app.get("/celdas")
    @requiere_sesion
    def celdas():
        codigo = request.args.get("codigo", "").strip()
        tipo = request.args.get("tipo", "").strip()
        zona = request.args.get("zona", "").strip()
        estado = request.args.get("estado", "").strip()

        resumen, lista_celdas, zonas = servicio_celdas.consultar_celdas(
            codigo=codigo, tipo=tipo, zona=zona, estado=estado
        )
        conn = conexion()
        try:
            with conn.cursor() as cur:
                auditorias = auditoria_repo.listar_recientes(cur, entidad="CELDA", limite=10)
        finally:
            conn.close()

        return render_template(
            "celdas.html",
            resumen=resumen,
            celdas=lista_celdas,
            zonas=zonas,
            auditorias=auditorias,
            filtro_codigo=codigo,
            filtro_tipo=tipo,
            filtro_zona=zona,
            filtro_estado=estado,
        )

    @app.post("/celdas/crear")
    @requiere_admin
    def crear_celda():
        try:
            servicio_celdas.crear_celda(
                request.form.get("codigo"),
                request.form.get("numero"),
                request.form.get("tipo"),
                request.form.get("zona"),
                session["operador_id"],
            )
            flash("Celda creada correctamente.", "ok")
        except (ValueError, pymysql.err.IntegrityError) as err:
            flash(str(err) or "No se pudo crear la celda.", "error")
        return redirect(url_for("celdas"))

    @app.post("/celdas/<int:celda_id>/editar")
    @requiere_admin
    def editar_celda(celda_id):
        try:
            servicio_celdas.modificar_celda(
                celda_id,
                request.form.get("tipo"),
                request.form.get("zona"),
                request.form.get("estado"),
                session["operador_id"],
            )
            flash("Celda actualizada correctamente.", "ok")
        except (ValueError, pymysql.err.IntegrityError) as err:
            flash(str(err) or "No se pudo modificar la celda.", "error")
        return redirect(url_for("celdas"))

    # --- ITERACIÓN 3: Gestión de Pagos y Mensualidades ---
    @app.route("/pagos", methods=["GET", "POST"])
    @requiere_sesion
    def pagos():
        es_admin = session.get("operador_rol") == "ADMIN"
        tab = request.args.get("tab", "registrar").strip()
        if tab in ("historial", "reporte") and not es_admin:
            flash("Las pestañas de historial y reportes financieros son exclusivas del administrador.", "error")
            return redirect(url_for("pagos", tab="registrar"))

        if request.method == "POST":
            try:
                pago_id = servicio_pagos.registrar_pago_mensual(
                    request.form.get("placa"),
                    request.form.get("propietario"),
                    request.form.get("metodo_pago"),
                    session["operador_id"],
                )
                flash("Pago de mensualidad registrado y vigencia actualizada correctamente.", "ok")
                return redirect(url_for("comprobante_pago", pago_id=pago_id))
            except (ValueError, pymysql.err.IntegrityError) as err:
                flash(str(err) or "No se pudo registrar el pago.", "error")
                placa_err = servicio_pagos.normalizar_placa(request.form.get("placa"))
                return redirect(url_for("pagos", tab="registrar", placa=placa_err))

        placa_consulta = servicio_pagos.normalizar_placa(request.args.get("placa", ""))
        info_suscripcion = None
        if placa_consulta:
            try:
                info_suscripcion = servicio_pagos.consultar_suscripcion(placa_consulta)
            except ValueError as err:
                flash(str(err), "error")

        criterio_hist = request.args.get("criterio", "").strip()
        desde_hist = request.args.get("desde", "").strip()
        hasta_hist = request.args.get("hasta", "").strip()
        estado_hist = request.args.get("estado_pago", "").strip()

        desde_rep = request.args.get("rep_desde", "").strip()
        hasta_rep = request.args.get("rep_hasta", "").strip()
        tipo_rep = request.args.get("rep_tipo", "").strip()

        if desde_hist and hasta_hist and desde_hist > hasta_hist:
            flash("La fecha inicial no puede ser posterior a la fecha final.", "error")
            return redirect(url_for("pagos", tab="historial"))
        if desde_rep and hasta_rep and desde_rep > hasta_rep:
            flash("La fecha inicial del reporte no puede ser posterior a la fecha final.", "error")
            return redirect(url_for("pagos", tab="reporte"))

        conn = conexion()
        try:
            with conn.cursor() as cur:
                kpis = pagos_repo.resumen_kpis_mes_actual(cur)
                por_vencer = suscripciones_repo.contar_por_vencer(cur, dias=5)
                vehiculos_catalogo = vehiculos_repo.listar(cur)
                suscripciones_lista = suscripciones_repo.listar_todas(cur)

                historial_pagos = []
                reporte_resumen = None
                reporte_metodos = []
                auditorias_pagos = []
                if es_admin:
                    historial_pagos = pagos_repo.listar_historial(
                        cur, criterio=criterio_hist, desde=desde_hist, hasta=hasta_hist, estado=estado_hist
                    )
                    reporte_resumen, reporte_metodos = pagos_repo.reporte_ingresos(
                        cur, desde=desde_rep, hasta=hasta_rep, tipo_vehiculo=tipo_rep
                    )
                    auditorias_pagos = auditoria_repo.listar_recientes(cur, entidad="PAGO", limite=12)
        finally:
            conn.close()

        return render_template(
            "pagos.html",
            tab=tab,
            es_admin=es_admin,
            tarifas=TARIFAS_MENSUALIDAD,
            metodos_pago=METODOS_PAGO_VALIDOS,
            kpis=kpis,
            por_vencer=por_vencer,
            placa_consulta=placa_consulta,
            info_suscripcion=info_suscripcion,
            vehiculos_catalogo=vehiculos_catalogo,
            suscripciones_lista=suscripciones_lista,
            historial_pagos=historial_pagos,
            criterio_hist=criterio_hist,
            desde_hist=desde_hist,
            hasta_hist=hasta_hist,
            estado_hist=estado_hist,
            reporte_resumen=reporte_resumen,
            reporte_metodos=reporte_metodos,
            desde_rep=desde_rep,
            hasta_rep=hasta_rep,
            tipo_rep=tipo_rep,
            auditorias_pagos=auditorias_pagos,
            hoy=date.today(),
        )

    @app.get("/comprobante/<int:pago_id>")
    @requiere_sesion
    def comprobante_pago(pago_id):
        conn = conexion()
        try:
            with conn.cursor() as cur:
                pago = pagos_repo.buscar_por_id(cur, pago_id)
        finally:
            conn.close()
        if not pago:
            flash("No se encontró el comprobante de pago solicitado.", "error")
            return redirect(url_for("pagos"))
        return render_template("comprobante_pago.html", pago=pago)

    @app.post("/pagos/<int:pago_id>/anular")
    @requiere_admin
    def anular_pago(pago_id):
        motivo = request.form.get("motivo", "")
        try:
            servicio_pagos.anular_pago(pago_id, motivo, session["operador_id"])
            flash("Pago anulado correctamente. Se registró auditoría y se actualizó la vigencia.", "ok")
        except ValueError as err:
            flash(str(err), "error")
        return redirect(url_for("pagos", tab="historial"))

    @app.get("/pagos/exportar-csv")
    @requiere_admin
    def exportar_pagos_csv():
        criterio = request.args.get("criterio", "").strip()
        desde = request.args.get("desde", "").strip()
        hasta = request.args.get("hasta", "").strip()
        estado = request.args.get("estado_pago", "").strip()

        conn = conexion()
        try:
            with conn.cursor() as cur:
                registros = pagos_repo.listar_historial(
                    cur, criterio=criterio, desde=desde, hasta=hasta, estado=estado
                )
        finally:
            conn.close()

        salida_csv = io.StringIO()
        writer = csv.writer(salida_csv, delimiter=";")
        writer.writerow([
            "Comprobante", "Placa", "Tipo", "Propietario", "Periodo",
            "Inicio Periodo", "Fin Periodo", "Valor", "Metodo Pago",
            "Estado", "Fecha Pago", "Operador", "Motivo Anulacion"
        ])
        for r in registros:
            writer.writerow([
                r["comprobante_codigo"],
                r["placa"],
                r["tipo_vehiculo"],
                r["propietario"],
                r["periodo_etiqueta"],
                r["fecha_inicio_periodo"],
                r["fecha_fin_periodo"],
                int(r["valor"]),
                r["metodo_pago"],
                r["estado"],
                r["fecha_pago"],
                r["operador_nombre"] or "—",
                r["motivo_anulacion"] or "",
            ])

        contenido = "﻿" + salida_csv.getvalue()
        return Response(
            contenido,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=historial_pagos_autos_colombia.csv"},
        )

    @app.get("/pagos/exportar-reporte")
    @requiere_admin
    def exportar_reporte_ingresos():
        desde = request.args.get("rep_desde", "").strip()
        hasta = request.args.get("rep_hasta", "").strip()
        tipo = request.args.get("rep_tipo", "").strip().upper()

        conn = conexion()
        try:
            with conn.cursor() as cur:
                resumen, metodos = pagos_repo.reporte_ingresos(
                    cur, desde=desde, hasta=hasta, tipo_vehiculo=tipo
                )
                detalle_pagos = pagos_repo.listar_historial(
                    cur, desde=desde, hasta=hasta
                )
                if tipo in ("CARRO", "MOTO"):
                    detalle_pagos = [p for p in detalle_pagos if p["tipo_vehiculo"] == tipo]
        finally:
            conn.close()

        salida_csv = io.StringIO()
        writer = csv.writer(salida_csv, delimiter=";")
        writer.writerow(["REPORTE DE INGRESOS POR MENSUALIDADES - AUTOS COLOMBIA"])
        writer.writerow(["Filtro Fecha Inicio", desde or "Todo el historial", "Filtro Fecha Fin", hasta or "Hoy", "Filtro Tipo", tipo or "TODOS"])
        writer.writerow([])
        writer.writerow(["RESUMEN FINANCIERO"])
        writer.writerow(["Concepto", "Cantidad", "Monto COP"])
        writer.writerow(["Ingreso Neto Recaudado (Aprobados)", int(resumen["cantidad_aprobados"] or 0), int(resumen["ingreso_neto"] or 0)])
        writer.writerow(["Ingresos Carros ($250.000)", int(resumen["pagos_carro"] or 0), int(resumen["ingresos_carro"] or 0)])
        writer.writerow(["Ingresos Motos ($100.000)", int(resumen["pagos_moto"] or 0), int(resumen["ingresos_moto"] or 0)])
        writer.writerow(["Pagos Anulados", int(resumen["cantidad_anulados"] or 0), int(resumen["total_anulado"] or 0)])
        writer.writerow([])
        writer.writerow(["DISTRIBUCION POR METODO DE PAGO (APROBADOS)"])
        writer.writerow(["Metodo de Pago", "Cantidad de Pagos", "Total Recaudado COP"])
        for m in metodos:
            writer.writerow([m["metodo_pago"], int(m["cantidad"]), int(m["total"])])
        writer.writerow([])
        writer.writerow(["DETALLE DE TRANSACCIONES DEL REPORTE"])
        writer.writerow([
            "Comprobante", "Placa", "Tipo", "Propietario", "Periodo",
            "Valor COP", "Metodo Pago", "Estado", "Fecha Pago", "Operador"
        ])
        for p in detalle_pagos:
            writer.writerow([
                p["comprobante_codigo"],
                p["placa"],
                p["tipo_vehiculo"],
                p["propietario"],
                p["periodo_etiqueta"],
                int(p["valor"]),
                p["metodo_pago"],
                p["estado"],
                p["fecha_pago"],
                p["operador_nombre"] or "—",
            ])

        contenido = "﻿" + salida_csv.getvalue()
        return Response(
            contenido,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=reporte_ingresos_autos_colombia.csv"},
        )

    # --- ITERACIÓN 2: Gestión de Usuarios / Operadores ---
    @app.route("/operadores", methods=["GET", "POST"])
    @requiere_admin
    def operadores():
        if request.method == "POST":
            try:
                servicio_usuarios.crear_usuario(
                    request.form.get("nombre"),
                    request.form.get("usuario"),
                    request.form.get("correo"),
                    request.form.get("password"),
                    request.form.get("rol"),
                    session["operador_id"],
                )
                flash("Usuario creado correctamente.", "ok")
            except (ValueError, pymysql.err.IntegrityError) as err:
                flash(str(err) or "No se pudo crear el usuario.", "error")
            return redirect(url_for("operadores"))

        filtro = request.args.get("q", "").strip()
        estado = request.args.get("estado", "").strip()
        editar_id = request.args.get("editar", "").strip()

        conn = conexion()
        try:
            with conn.cursor() as cur:
                lista = operadores_repo.listar(cur, filtro=filtro, estado=estado)
                admins_activos = operadores_repo.contar_admins_activos(cur)
                usuario_editar = (
                    operadores_repo.buscar_por_id(cur, int(editar_id))
                    if editar_id.isdigit() else None
                )
                auditorias = auditoria_repo.listar_recientes(cur, entidad="USUARIO", limite=12)
        finally:
            conn.close()

        return render_template(
            "operadores.html",
            operadores=lista,
            admins_activos=admins_activos,
            usuario_editar=usuario_editar,
            auditorias=auditorias,
            filtro_q=filtro,
            filtro_estado=estado,
        )

    @app.post("/operadores/<int:operador_id>/editar")
    @requiere_admin
    def editar_operador(operador_id):
        try:
            servicio_usuarios.modificar_usuario(
                operador_id,
                request.form.get("nombre"),
                request.form.get("correo"),
                request.form.get("rol"),
                request.form.get("activo"),
                request.form.get("password"),
                session["operador_id"],
            )
            flash("Usuario actualizado correctamente.", "ok")
        except (ValueError, pymysql.err.IntegrityError) as err:
            flash(str(err) or "No se pudo actualizar el usuario.", "error")
        return redirect(url_for("operadores"))

    @app.post("/operadores/<int:operador_id>/estado")
    @requiere_admin
    def cambiar_estado_operador(operador_id):
        activar = request.form.get("accion") == "activar"
        try:
            servicio_usuarios.cambiar_estado_usuario(
                operador_id, activar, session["operador_id"]
            )
            flash(
                "Usuario reactivado correctamente." if activar
                else "Usuario desactivado. Su acceso ha sido revocado y se conserva su trazabilidad.",
                "ok",
            )
        except ValueError as err:
            flash(str(err), "error")
        return redirect(url_for("operadores"))
