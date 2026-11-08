class CeldaRepository:
    def buscar_disponible(self, cur, tipo):
        cur.execute("""
            SELECT id,codigo FROM celda
            WHERE tipo=%s AND estado='Disponible'
            ORDER BY numero LIMIT 1 FOR UPDATE
        """, (tipo,))
        return cur.fetchone()

    def cambiar_estado(self, cur, celda_id, estado):
        cur.execute("UPDATE celda SET estado=%s WHERE id=%s", (estado,celda_id))

    def listar(self, cur):
        cur.execute("""
            SELECT c.id,c.codigo,c.numero,c.tipo,c.estado,v.placa
            FROM celda c
            LEFT JOIN estancia e ON e.celda_activa_id=c.id
            LEFT JOIN vehiculo v ON v.id=e.vehiculo_id
            ORDER BY c.tipo DESC,c.numero
        """)
        return cur.fetchall()

    def resumen(self, cur):
        cur.execute("""
            SELECT COUNT(*) AS total,
              SUM(estado='Disponible') AS disponibles,
              SUM(estado='Ocupada') AS ocupadas
            FROM celda
        """)
        return cur.fetchone()
