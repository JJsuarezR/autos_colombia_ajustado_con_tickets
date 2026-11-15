class AuditoriaRepository:
    def registrar(self, cur, operador_id, entidad, entidad_id, accion, detalle):
        cur.execute("""
            INSERT INTO auditoria_sistema(operador_id, entidad, entidad_id, accion, detalle)
            VALUES(%s, %s, %s, %s, %s)
        """, (operador_id, entidad, entidad_id, accion, detalle[:255]))

    def listar_recientes(self, cur, entidad=None, limite=20):
        sql = """
            SELECT a.id, a.entidad, a.entidad_id, a.accion, a.detalle, a.creado_en,
                   o.nombre AS operador_nombre, o.usuario AS operador_usuario
            FROM auditoria_sistema a
            LEFT JOIN operador o ON o.id = a.operador_id
            WHERE 1=1
        """
        params = []
        if entidad:
            sql += " AND a.entidad=%s"
            params.append(entidad)
        sql += " ORDER BY a.creado_en DESC, a.id DESC LIMIT %s"
        params.append(limite)
        cur.execute(sql, tuple(params))
        return cur.fetchall()
