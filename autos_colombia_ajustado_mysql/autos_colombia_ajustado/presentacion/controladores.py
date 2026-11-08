"""Controladores HTTP: reciben solicitudes y delegan las reglas al servicio."""

import pymysql
from functools import wraps
from flask import (current_app, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from persistencia.conexion import conectar
from persistencia.celda_repository import CeldaRepository
from persistencia.estancia_repository import EstanciaRepository
from persistencia.operador_repository import OperadorRepository
from aplicacion.servicio_estancias import ServicioEstancias

def registrar_controladores(app):
    servicio = ServicioEstancias(app.config)
    celdas_repo = CeldaRepository()
    estancias_repo = EstanciaRepository()
    operadores_repo = OperadorRepository()

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
            usuario = request.form.get("usuario", "").strip()
            password = request.form.get("password", "")
            conn = conexion()
            try:
                with conn.cursor() as cur:
                    operador = operadores_repo.buscar_por_usuario(cur, usuario)
            finally:
                conn.close()
            if operador and check_password_hash(operador["password_hash"], password):
                session.clear()
                session["operador_id"] = operador["id"]
                session["operador_nombre"] = operador["nombre"]
                session["operador_rol"] = operador["rol"]
                return redirect(url_for("panel"))
            flash("Usuario o contraseña incorrectos.", "error")
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
        if request.method == "POST":
            try:
                estancia_id = servicio.registrar_entrada(
                    request.form.get("placa"), request.form.get("tipo"),
                    session["operador_id"], request.form.get("marca"),
                    request.form.get("color")
                )
                return redirect(url_for("ticket", estancia_id=estancia_id))
            except (ValueError, pymysql.err.IntegrityError) as error:
                flash(str(error) or "No se pudo registrar la entrada.", "error")
            return redirect(url_for("entrada"))
        return render_template("entrada.html")

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
                codigo, permanencia = servicio.registrar_salida(
                    request.form.get("placa"), session["operador_id"]
                )
                flash(f"Salida registrada. Celda {codigo} liberada. Permanencia: {permanencia}.", "ok")
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
        placa = servicio.normalizar_placa(request.args.get("placa", ""))
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

    @app.route("/operadores", methods=["GET", "POST"])
    @requiere_admin
    def operadores():
        if request.method == "POST":
            nombre = request.form.get("nombre", "").strip()
            usuario = request.form.get("usuario", "").strip()
            password = request.form.get("password", "")
            rol = request.form.get("rol", "OPERADOR")
            if not nombre or not usuario or len(password) < 8:
                flash("Complete los campos. La contraseña debe tener mínimo 8 caracteres.", "error")
            elif rol not in ("ADMIN", "OPERADOR"):
                flash("Rol no válido.", "error")
            else:
                conn = conexion()
                try:
                    with conn.cursor() as cur:
                        operadores_repo.crear(cur, nombre, usuario,
                            generate_password_hash(password), rol)
                    conn.commit()
                    flash("Operador creado correctamente.", "ok")
                except pymysql.err.IntegrityError:
                    conn.rollback()
                    flash("El nombre de usuario ya existe.", "error")
                finally:
                    conn.close()
            return redirect(url_for("operadores"))
        conn = conexion()
        try:
            with conn.cursor() as cur:
                lista = operadores_repo.listar(cur)
        finally:
            conn.close()
        return render_template("operadores.html", operadores=lista)
