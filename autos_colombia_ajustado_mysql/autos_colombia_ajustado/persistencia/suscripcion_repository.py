class SuscripcionRepository:
    def buscar_por_vehiculo_id(self, cur, vehiculo_id, bloquear=False):
        sql = """
            SELECT s.id, s.vehiculo_id, s.propietario, s.fecha_inicio,
                   s.fecha_vencimiento, s.estado, s.creado_en, s.actualizado_en,
                   v.placa, v.tipo, v.marca, v.color
            FROM suscripcion s
            JOIN vehiculo v ON v.id = s.vehiculo_id
            WHERE s.vehiculo_id=%s
        """
        if bloquear:
            sql += " FOR UPDATE"
        cur.execute(sql, (vehiculo_id,))
        return cur.fetchone()

    def buscar_por_id(self, cur, suscripcion_id, bloquear=False):
        sql = """
            SELECT s.id, s.vehiculo_id, s.propietario, s.fecha_inicio,
                   s.fecha_vencimiento, s.estado, v.placa, v.tipo
            FROM suscripcion s
            JOIN vehiculo v ON v.id = s.vehiculo_id
            WHERE s.id=%s
        """
        if bloquear:
            sql += " FOR UPDATE"
        cur.execute(sql, (suscripcion_id,))
        return cur.fetchone()

    def crear(self, cur, vehiculo_id, propietario, fecha_inicio, fecha_vencimiento):
        cur.execute("""
            INSERT INTO suscripcion(vehiculo_id, propietario, fecha_inicio, fecha_vencimiento, estado)
            VALUES(%s, %s, %s, %s, 'ACTIVA')
        """, (vehiculo_id, propietario, fecha_inicio, fecha_vencimiento))
        return cur.lastrowid

    def actualizar_vigencia(self, cur, suscripcion_id, propietario, fecha_inicio, fecha_vencimiento, estado="ACTIVA"):
        cur.execute("""
            UPDATE suscripcion
            SET propietario=%s, fecha_inicio=%s, fecha_vencimiento=%s,
                estado=%s, actualizado_en=NOW()
            WHERE id=%s
        """, (propietario, fecha_inicio, fecha_vencimiento, estado, suscripcion_id))

    def contar_por_vencer(self, cur, dias=5):
        cur.execute("""
            SELECT COUNT(*) AS total
            FROM suscripcion
            WHERE fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
        """, (dias,))
        return cur.fetchone()["total"]

    def listar_todas(self, cur):
        cur.execute("""
            SELECT s.id, s.vehiculo_id, s.propietario, s.fecha_inicio,
                   s.fecha_vencimiento, s.estado,
                   v.placa, v.tipo, v.marca, v.color
            FROM suscripcion s
            JOIN vehiculo v ON v.id = s.vehiculo_id
            ORDER BY s.fecha_vencimiento ASC, v.placa ASC
        """)
        return cur.fetchall()
