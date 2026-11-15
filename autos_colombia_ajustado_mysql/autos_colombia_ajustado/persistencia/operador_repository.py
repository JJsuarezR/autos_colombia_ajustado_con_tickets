class OperadorRepository:
    def buscar_por_identificador_activo(self, cur, identificador):
        """Busca un operador activo por usuario o correo electrónico (RF-06)."""
        cur.execute("""
            SELECT id, nombre, usuario, correo, password_hash, rol, activo
            FROM operador
            WHERE (usuario=%s OR LOWER(correo)=LOWER(%s)) AND activo=1
        """, (identificador, identificador))
        return cur.fetchone()

    def buscar_por_usuario(self, cur, usuario):
        return self.buscar_por_identificador_activo(cur, usuario)

    def buscar_por_id(self, cur, operador_id, bloquear=False):
        sql = """
            SELECT id, nombre, usuario, correo, rol, activo, creado_en, actualizado_en
            FROM operador
            WHERE id=%s
        """
        if bloquear:
            sql += " FOR UPDATE"
        cur.execute(sql, (operador_id,))
        return cur.fetchone()

    def existe_usuario_o_correo(self, cur, usuario, correo, excluir_id=None):
        if excluir_id:
            cur.execute("""
                SELECT id, usuario, correo
                FROM operador
                WHERE (LOWER(usuario)=LOWER(%s) OR (correo IS NOT NULL AND LOWER(correo)=LOWER(%s)))
                  AND id<>%s
            """, (usuario, correo, excluir_id))
        else:
            cur.execute("""
                SELECT id, usuario, correo
                FROM operador
                WHERE LOWER(usuario)=LOWER(%s) OR (correo IS NOT NULL AND LOWER(correo)=LOWER(%s))
            """, (usuario, correo))
        return cur.fetchone()

    def contar_admins_activos(self, cur):
        cur.execute("""
            SELECT COUNT(*) AS total
            FROM operador
            WHERE rol='ADMIN' AND activo=1
        """)
        return cur.fetchone()["total"]

    def listar(self, cur, filtro=None, estado=None):
        sql = """
            SELECT id, nombre, usuario, correo, rol, activo, creado_en, actualizado_en
            FROM operador
            WHERE 1=1
        """
        params = []
        filtro = filtro.strip() if filtro and filtro.strip() else None
        if filtro:
            if filtro.isdigit():
                sql += " AND (id=%s OR nombre LIKE %s OR usuario LIKE %s OR correo LIKE %s)"
                like = f"%{filtro}%"
                params.extend([int(filtro), like, like, like])
            else:
                sql += " AND (nombre LIKE %s OR usuario LIKE %s OR correo LIKE %s)"
                like = f"%{filtro}%"
                params.extend([like, like, like])

        if estado == "1":
            sql += " AND activo=1"
        elif estado == "0":
            sql += " AND activo=0"

        sql += " ORDER BY activo DESC, nombre ASC"
        cur.execute(sql, tuple(params))
        return cur.fetchall()

    def crear(self, cur, nombre, usuario, correo, password_hash, rol):
        cur.execute("""
            INSERT INTO operador(nombre, usuario, correo, password_hash, rol, activo)
            VALUES(%s, %s, %s, %s, %s, 1)
        """, (nombre, usuario, correo, password_hash, rol))
        return cur.lastrowid

    def actualizar(self, cur, operador_id, nombre, correo, rol, activo, password_hash=None):
        if password_hash:
            cur.execute("""
                UPDATE operador
                SET nombre=%s, correo=%s, rol=%s, activo=%s, password_hash=%s, actualizado_en=NOW()
                WHERE id=%s
            """, (nombre, correo, rol, activo, password_hash, operador_id))
        else:
            cur.execute("""
                UPDATE operador
                SET nombre=%s, correo=%s, rol=%s, activo=%s, actualizado_en=NOW()
                WHERE id=%s
            """, (nombre, correo, rol, activo, operador_id))

    def cambiar_estado(self, cur, operador_id, activo):
        cur.execute("""
            UPDATE operador
            SET activo=%s, actualizado_en=NOW()
            WHERE id=%s
        """, (activo, operador_id))
