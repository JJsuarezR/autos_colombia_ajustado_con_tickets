"""Controladores HTTP: reciben solicitudes y delegan las reglas a los servicios."""

import pymysql
from functools import wraps
from flask import (current_app, flash, redirect, render_template, request,
                   session, url_for)
from persistencia.conexion import conectar
from persistencia.celda_repository import CeldaRepository
from persistencia.estancia_repository import EstanciaRepository
from persistencia.operador_repository import OperadorRepository
from persistencia.vehiculo_repository import VehiculoRepository
from persistencia.auditoria_repository import AuditoriaRepository
from aplicacion.servicio_estancias import ServicioEstancias
from aplicacion.servicio_usuarios import ServicioUsuarios
from aplicacion.servicio_celdas import ServicioCeldas


def registrar_controladores(app):
    servicio = ServicioEstancias(app.config)
    servicio_usuarios = ServicioUsuarios(app.config)
    servicio_celdas = ServicioCeldas(app.config)
    celdas_repo = CeldaRepository()
    estancias_repo = EstanciaRepository()
    operadores_repo = OperadorRepository()
    vehiculos_repo = VehiculoRepository()
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
        finally:
            conn.close()
        return render_template("index.html", resumen=resumen, celdas=celdas,
                               activos=activos, historial=historial)

    @app.route("/entrada", methods=["GET", "POST"])
    @requiere_sesion
    def entrada():
        placa_preseleccionada = servicio.normalizar_placa(request.args.get("placa", ""))
        if request.method == "POST":
            accion = request.form.get("accion", "entrada")
            if accion == "registrar_vehiculo":
                try:
                    placa_reg = servicio.registrar_vehiculo(
                        request.form.get("placa"),
                        request.form.get("tipo"),
                        request.form.get("marca"),
                        request.form.get("color"),
                        session["operador_id"],
                    )
                    flash(
                        f"Vehículo {placa_reg} registrado correctamente. Ahora puede darle entrada.",
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
                vehiculos = vehiculos_repo.listar(cur)
        finally:
            conn.close()
        return render_template(
            "entrada.html",
            vehiculos=vehiculos,
            placa_preseleccionada=placa_preseleccionada,
        )

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

    # --- ITERACIÓN 2: Gestión de Celdas ---
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
    @requiere_sesion
    def editar_celda(celda_id):
        try:
            servicio_celdas.modificar_celda(
                celda_id,
                request.form.get("tipo"),
                request.form.get("zona"),
                session["operador_id"],
            )
            flash("Celda actualizada correctamente.", "ok")
        except (ValueError, pymysql.err.IntegrityError) as err:
            flash(str(err) or "No se pudo modificar la celda.", "error")
        return redirect(url_for("celdas"))

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
