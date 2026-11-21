class VehiculoRepository:
    def buscar_por_placa(self, cur, placa):
        cur.execute("""
            SELECT v.id, v.placa, v.tipo, v.marca, v.color, v.propietario,
                   s.id AS suscripcion_id, s.propietario AS suscriptor_nombre,
                   s.fecha_inicio, s.fecha_vencimiento
            FROM vehiculo v
            LEFT JOIN suscripcion s ON s.vehiculo_id = v.id
            WHERE v.placa=%s
        """, (placa,))
        return cur.fetchone()

    def buscar_por_id(self, cur, vehiculo_id, bloquear=False):
        sql = """
            SELECT v.id, v.placa, v.tipo, v.marca, v.color, v.propietario,
                   s.id AS suscripcion_id, s.propietario AS suscriptor_nombre,
                   s.fecha_inicio, s.fecha_vencimiento
            FROM vehiculo v
            LEFT JOIN suscripcion s ON s.vehiculo_id = v.id
            WHERE v.id=%s
        """
        if bloquear:
            sql += " FOR UPDATE"
        cur.execute(sql, (vehiculo_id,))
        return cur.fetchone()

    def existe_otra_placa(self, cur, placa, excluir_id):
        cur.execute("SELECT id FROM vehiculo WHERE placa=%s AND id<>%s", (placa, excluir_id))
        return cur.fetchone()

    def crear(self, cur, placa, tipo, marca, color, propietario=None):
        cur.execute(
            "INSERT INTO vehiculo(placa,tipo,marca,color,propietario) VALUES(%s,%s,%s,%s,%s)",
            (placa, tipo, marca, color, propietario)
        )
        return cur.lastrowid

    def completar_datos(self, cur, vehiculo_id, marca, color, propietario=None):
        if propietario:
            cur.execute(
                "UPDATE vehiculo SET marca=%s, color=%s, propietario=%s WHERE id=%s",
                (marca, color, propietario, vehiculo_id)
            )
        else:
            cur.execute(
                "UPDATE vehiculo SET marca=%s, color=%s WHERE id=%s",
                (marca, color, vehiculo_id)
            )

    def actualizar(self, cur, vehiculo_id, placa, tipo, marca, color, propietario=None):
        cur.execute(
            "UPDATE vehiculo SET placa=%s, tipo=%s, marca=%s, color=%s, propietario=%s WHERE id=%s",
            (placa, tipo, marca, color, propietario, vehiculo_id)
        )

    def actualizar_propietario(self, cur, vehiculo_id, propietario):
        cur.execute(
            "UPDATE vehiculo SET propietario=%s WHERE id=%s",
            (propietario, vehiculo_id)
        )

    def listar(self, cur, filtro_placa=None):
        sql = """
            SELECT v.id, v.placa, v.tipo, v.marca, v.color,
                   COALESCE(s.propietario, v.propietario) AS propietario,
                   s.fecha_vencimiento
            FROM vehiculo v
            LEFT JOIN suscripcion s ON s.vehiculo_id = v.id
            WHERE 1=1
        """
        params = []
        filtro_placa = filtro_placa.strip() if filtro_placa and filtro_placa.strip() else None
        if filtro_placa:
            sql += " AND v.placa LIKE %s"
            params.append(f"%{filtro_placa.upper()}%")
        sql += " ORDER BY v.placa"
        cur.execute(sql, tuple(params))
        return cur.fetchall()
