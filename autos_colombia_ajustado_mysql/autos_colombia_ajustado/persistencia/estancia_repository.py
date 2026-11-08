class EstanciaRepository:
    def vehiculo_tiene_estancia_activa(self, cur, vehiculo_id):
        cur.execute("SELECT id FROM estancia WHERE vehiculo_activo_id=%s", (vehiculo_id,))
        return cur.fetchone()

    def crear(self, cur, vehiculo_id, celda_id, operador_id, fecha):
        cur.execute("""
            INSERT INTO estancia
              (vehiculo_id,celda_id,vehiculo_activo_id,celda_activa_id,
               operador_entrada_id,fecha_entrada)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (vehiculo_id,celda_id,vehiculo_id,celda_id,operador_id,fecha))
        return cur.lastrowid

    def asignar_ticket(self, cur, estancia_id, codigo):
        cur.execute("UPDATE estancia SET ticket_codigo=%s WHERE id=%s", (codigo, estancia_id))

    def obtener_ticket(self, cur, estancia_id):
        cur.execute("""
            SELECT e.id, e.ticket_codigo, e.fecha_entrada, e.fecha_salida,
                   v.placa, v.tipo, v.marca, v.color, c.codigo AS celda,
                   o.nombre AS operador_entrada
            FROM estancia e
            JOIN vehiculo v ON v.id=e.vehiculo_id
            JOIN celda c ON c.id=e.celda_id
            LEFT JOIN operador o ON o.id=e.operador_entrada_id
            WHERE e.id=%s
        """, (estancia_id,))
        return cur.fetchone()

    def buscar_activa_por_placa(self, cur, placa):
        cur.execute("""
            SELECT e.id,e.celda_id,e.fecha_entrada,c.codigo
            FROM estancia e
            JOIN vehiculo v ON v.id=e.vehiculo_id
            JOIN celda c ON c.id=e.celda_id
            WHERE v.placa=%s AND e.fecha_salida IS NULL
            FOR UPDATE
        """, (placa,))
        return cur.fetchone()

    def cerrar(self, cur, estancia_id, operador_id, fecha):
        cur.execute("""
            UPDATE estancia
            SET fecha_salida=%s,vehiculo_activo_id=NULL,celda_activa_id=NULL,
                operador_salida_id=%s
            WHERE id=%s AND fecha_salida IS NULL
        """, (fecha,operador_id,estancia_id))

    def listar_activas(self, cur):
        cur.execute("""
            SELECT e.id,e.ticket_codigo,v.placa,v.tipo,v.marca,v.color,c.codigo AS celda,e.fecha_entrada,
                   oe.nombre AS operador_entrada
            FROM estancia e
            JOIN vehiculo v ON v.id=e.vehiculo_id
            JOIN celda c ON c.id=e.celda_id
            LEFT JOIN operador oe ON oe.id=e.operador_entrada_id
            WHERE e.fecha_salida IS NULL ORDER BY e.fecha_entrada
        """)
        return cur.fetchall()

    def ultimas_salidas(self, cur, limite=15):
        cur.execute("""
            SELECT e.id,e.ticket_codigo,v.placa,v.tipo,v.marca,v.color,c.codigo AS celda,e.fecha_entrada,e.fecha_salida,
                   oe.nombre AS operador_entrada, os.nombre AS operador_salida
            FROM estancia e
            JOIN vehiculo v ON v.id=e.vehiculo_id
            JOIN celda c ON c.id=e.celda_id
            LEFT JOIN operador oe ON oe.id=e.operador_entrada_id
            LEFT JOIN operador os ON os.id=e.operador_salida_id
            WHERE e.fecha_salida IS NOT NULL
            ORDER BY e.fecha_salida DESC LIMIT %s
        """, (limite,))
        return cur.fetchall()

    def filtrar_historial(self, cur, placa=None, desde=None, hasta=None):
        sql = """
            SELECT e.id, e.ticket_codigo, v.placa, v.tipo, v.marca, v.color, c.codigo AS celda, e.fecha_entrada, e.fecha_salida,
                   oe.nombre AS operador_entrada, os.nombre AS operador_salida
            FROM estancia e
            JOIN vehiculo v ON v.id = e.vehiculo_id
            JOIN celda c ON c.id = e.celda_id
            LEFT JOIN operador oe ON oe.id = e.operador_entrada_id
            LEFT JOIN operador os ON os.id = e.operador_salida_id
            WHERE 1=1
        """
        params = []

        # Sanitizar valores de entrada convirtiendo cadenas vacías o espacios a None
        placa = placa.strip() if placa and placa.strip() else None
        desde = desde.strip() if desde and desde.strip() else None
        hasta = hasta.strip() if hasta and hasta.strip() else None

        if placa:
            sql += " AND v.placa LIKE %s"
            params.append(f"%{placa}%")

        if desde:
            sql += " AND DATE(e.fecha_entrada) >= %s"
            params.append(desde)

        if hasta:
            sql += " AND DATE(e.fecha_entrada) <= %s"
            params.append(hasta)

        sql += " ORDER BY e.fecha_entrada DESC"

        cur.execute(sql, tuple(params))
        return cur.fetchall()
