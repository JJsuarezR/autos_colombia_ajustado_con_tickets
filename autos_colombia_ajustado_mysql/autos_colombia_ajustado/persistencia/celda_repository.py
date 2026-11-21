class CeldaRepository:
    def resumen(self, cur):
        cur.execute("""
            SELECT COUNT(*) total,
                   COALESCE(SUM(estado='Disponible'),0) disponibles,
                   COALESCE(SUM(estado='Ocupada'),0) ocupadas
            FROM celda
        """)
        return cur.fetchone()

    def buscar_disponible(self, cur, tipo):
        cur.execute("""
            SELECT id,codigo FROM celda
            WHERE tipo=%s AND estado='Disponible'
            ORDER BY numero, codigo LIMIT 1 FOR UPDATE
        """, (tipo,))
        return cur.fetchone()

    def buscar_por_id(self, cur, celda_id, bloquear=False):
        sql = "SELECT id, codigo, numero, tipo, zona, estado FROM celda WHERE id=%s"
        if bloquear:
            sql += " FOR UPDATE"
        cur.execute(sql, (celda_id,))
        return cur.fetchone()

    def existe_codigo_o_numero(self, cur, codigo, tipo, numero):
        cur.execute("""
            SELECT id, codigo, numero
            FROM celda
            WHERE UPPER(codigo)=UPPER(%s) OR (tipo=%s AND numero=%s)
        """, (codigo, tipo, numero))
        return cur.fetchone()

    def crear(self, cur, codigo, numero, tipo, zona):
        cur.execute("""
            INSERT INTO celda(codigo, numero, tipo, zona, estado)
            VALUES(%s, %s, %s, %s, 'Disponible')
        """, (codigo, numero, tipo, zona))
        return cur.lastrowid

    def actualizar(self, cur, celda_id, tipo, zona, estado=None):
        if estado in ("Disponible", "Ocupada"):
            cur.execute(
                "UPDATE celda SET tipo=%s, zona=%s, estado=%s WHERE id=%s",
                (tipo, zona, estado, celda_id)
            )
        else:
            cur.execute(
                "UPDATE celda SET tipo=%s, zona=%s WHERE id=%s",
                (tipo, zona, celda_id)
            )

    def cambiar_estado(self, cur, celda_id, estado):
        cur.execute("UPDATE celda SET estado=%s WHERE id=%s", (estado, celda_id))

    def listar_zonas(self, cur):
        cur.execute("SELECT DISTINCT zona FROM celda WHERE zona IS NOT NULL AND zona<>'' ORDER BY zona")
        return [r["zona"] for r in cur.fetchall()]

    def listar(self, cur, codigo=None, tipo=None, zona=None, estado=None):
        sql = """
            SELECT c.id, c.codigo, c.numero, c.tipo, c.zona, c.estado,
                   e.id AS estancia_id,
                   e.ticket_codigo,
                   v.placa, v.marca, v.color,
                   e.fecha_entrada,
                   TIMESTAMPDIFF(MINUTE, e.fecha_entrada, NOW()) AS minutos_transcurridos
            FROM celda c
            LEFT JOIN estancia e ON e.celda_activa_id=c.id
            LEFT JOIN vehiculo v ON v.id=e.vehiculo_id
            WHERE 1=1
        """
        params = []
        codigo = codigo.strip() if codigo and codigo.strip() else None
        tipo = tipo.strip().upper() if tipo and tipo.strip() else None
        zona = zona.strip() if zona and zona.strip() else None
        estado = estado.strip() if estado and estado.strip() else None

        if codigo:
            sql += " AND (c.codigo LIKE %s OR v.placa LIKE %s OR e.ticket_codigo LIKE %s)"
            like = f"%{codigo}%"
            params.extend([like, like, like])
        if tipo in ("CARRO", "MOTO"):
            sql += " AND c.tipo = %s"
            params.append(tipo)
        if zona:
            sql += " AND c.zona LIKE %s"
            params.append(f"%{zona}%")
        if estado in ("Disponible", "Ocupada"):
            sql += " AND c.estado = %s"
            params.append(estado)

        sql += " ORDER BY c.tipo, c.numero, c.codigo"
        cur.execute(sql, tuple(params))
        return cur.fetchall()
