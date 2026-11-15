"""Reglas de negocio para la gestión y autenticación de usuarios/operadores (Iteración 2)."""

import re
from werkzeug.security import check_password_hash, generate_password_hash
from persistencia.conexion import conectar
from persistencia.operador_repository import OperadorRepository
from persistencia.auditoria_repository import AuditoriaRepository

RE_CORREO = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
RE_USUARIO = re.compile(r"^[A-Za-z0-9._-]{3,60}$")


class ServicioUsuarios:
    def __init__(self, config):
        self.config = config
        self.operadores = OperadorRepository()
        self.auditoria = AuditoriaRepository()

    def autenticar(self, identificador, password):
        identificador = (identificador or "").strip()
        if not identificador or not password:
            raise ValueError("Ingrese su correo o usuario y su contraseña.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                operador = self.operadores.buscar_por_identificador_activo(cur, identificador)
                if not operador or not check_password_hash(operador["password_hash"], password):
                    raise ValueError("Credenciales inválidas o usuario inactivo.")
                return operador
        finally:
            conn.close()

    def crear_usuario(self, nombre, usuario, correo, password, rol, admin_id):
        nombre = (nombre or "").strip()
        usuario = (usuario or "").strip()
        correo = (correo or "").strip().lower()
        rol = (rol or "OPERADOR").strip().upper()

        if not nombre or len(nombre) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        if not RE_USUARIO.fullmatch(usuario):
            raise ValueError("El usuario debe tener entre 3 y 60 caracteres (letras, números, punto o guion).")
        if not RE_CORREO.fullmatch(correo):
            raise ValueError("Ingrese un correo electrónico válido.")
        if not password or len(password) < 8:
            raise ValueError("La contraseña debe tener mínimo 8 caracteres.")
        if rol not in ("ADMIN", "OPERADOR"):
            raise ValueError("El rol seleccionado no es válido.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                existente = self.operadores.existe_usuario_o_correo(cur, usuario, correo)
                if existente:
                    if existente["usuario"].lower() == usuario.lower():
                        raise ValueError(f"El nombre de usuario '{usuario}' ya está registrado.")
                    raise ValueError(f"El correo '{correo}' ya está registrado.")

                nuevo_id = self.operadores.crear(
                    cur, nombre, usuario, correo, generate_password_hash(password), rol
                )
                self.auditoria.registrar(
                    cur, admin_id, "USUARIO", nuevo_id, "CREAR",
                    f"Creó usuario '{usuario}' ({correo}) con rol {rol}."
                )
            conn.commit()
            return nuevo_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def modificar_usuario(self, operador_id, nombre, correo, rol, activo, nueva_password, admin_id):
        nombre = (nombre or "").strip()
        correo = (correo or "").strip().lower()
        rol = (rol or "").strip().upper()
        activo_int = 1 if str(activo) in ("1", "true", "True", "on") else 0
        nueva_password = (nueva_password or "").strip()

        if not nombre or len(nombre) < 3:
            raise ValueError("El nombre debe tener al menos 3 caracteres.")
        if not RE_CORREO.fullmatch(correo):
            raise ValueError("Ingrese un correo electrónico válido.")
        if rol not in ("ADMIN", "OPERADOR"):
            raise ValueError("Rol no válido.")
        if nueva_password and len(nueva_password) < 8:
            raise ValueError("La nueva contraseña debe tener mínimo 8 caracteres.")

        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                actual = self.operadores.buscar_por_id(cur, operador_id, bloquear=True)
                if not actual:
                    raise ValueError("El usuario seleccionado no existe.")

                if int(operador_id) == int(admin_id) and activo_int == 0:
                    raise ValueError("No puede desactivar su propio usuario administrador en sesión.")

                if actual["rol"] == "ADMIN" and actual["activo"] == 1 and (rol != "ADMIN" or activo_int == 0):
                    if self.operadores.contar_admins_activos(cur) <= 1:
                        raise ValueError("Operación rechazada: no puede haber menos de 1 administrador activo en el sistema.")

                duplicado = self.operadores.existe_usuario_o_correo(cur, actual["usuario"], correo, excluir_id=operador_id)
                if duplicado:
                    raise ValueError(f"El correo '{correo}' ya pertenece a otro usuario.")

                pw_hash = generate_password_hash(nueva_password) if nueva_password else None
                self.operadores.actualizar(cur, operador_id, nombre, correo, rol, activo_int, pw_hash)
                estado_txt = "Activo" if activo_int == 1 else "Inactivo"
                self.auditoria.registrar(
                    cur, admin_id, "USUARIO", operador_id, "MODIFICAR",
                    f"Modificó usuario '{actual['usuario']}': nombre='{nombre}', correo='{correo}', rol={rol}, estado={estado_txt}."
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def cambiar_estado_usuario(self, operador_id, activo, admin_id):
        activo_int = 1 if activo else 0
        conn = conectar(self.config)
        try:
            with conn.cursor() as cur:
                conn.begin()
                actual = self.operadores.buscar_por_id(cur, operador_id, bloquear=True)
                if not actual:
                    raise ValueError("El usuario no existe.")
                if int(operador_id) == int(admin_id) and activo_int == 0:
                    raise ValueError("No puede desactivar su propio usuario administrador.")
                if actual["rol"] == "ADMIN" and actual["activo"] == 1 and activo_int == 0:
                    if self.operadores.contar_admins_activos(cur) <= 1:
                        raise ValueError("Operación rechazada: no puede haber menos de 1 administrador activo en el sistema.")

                self.operadores.cambiar_estado(cur, operador_id, activo_int)
                accion = "REACTIVAR" if activo_int == 1 else "DESACTIVAR"
                self.auditoria.registrar(
                    cur, admin_id, "USUARIO", operador_id, accion,
                    f"{accion.capitalize()} usuario '{actual['usuario']}' ({actual['nombre']})."
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
