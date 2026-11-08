class VehiculoRepository:
    def buscar_por_placa(self, cur, placa):
        cur.execute("SELECT id, placa, tipo, marca, color FROM vehiculo WHERE placa=%s", (placa,))
        return cur.fetchone()

    def crear(self, cur, placa, tipo, marca, color):
        cur.execute(
            "INSERT INTO vehiculo(placa,tipo,marca,color) VALUES(%s,%s,%s,%s)",
            (placa, tipo, marca, color)
        )
        return cur.lastrowid

    def completar_datos(self, cur, vehiculo_id, marca, color):
        cur.execute(
            "UPDATE vehiculo SET marca=%s, color=%s WHERE id=%s",
            (marca, color, vehiculo_id)
        )

    def listar(self, cur):
        cur.execute("SELECT id,placa,tipo,marca,color FROM vehiculo ORDER BY placa")
        return cur.fetchall()
