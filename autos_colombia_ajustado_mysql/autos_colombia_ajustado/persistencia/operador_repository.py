class OperadorRepository:
    def buscar_por_usuario(self, cur, usuario):
        cur.execute("""
            SELECT id,nombre,usuario,password_hash,rol,activo
            FROM operador WHERE usuario=%s AND activo=1
        """, (usuario,))
        return cur.fetchone()

    def listar(self, cur):
        cur.execute("SELECT id,nombre,usuario,rol,activo FROM operador ORDER BY nombre")
        return cur.fetchall()

    def crear(self, cur, nombre, usuario, password_hash, rol):
        cur.execute("""
            INSERT INTO operador(nombre,usuario,password_hash,rol)
            VALUES(%s,%s,%s,%s)
        """, (nombre,usuario,password_hash,rol))
