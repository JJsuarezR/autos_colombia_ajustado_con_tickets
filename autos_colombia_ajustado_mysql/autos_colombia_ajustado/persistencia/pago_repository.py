class PagoRepository:
    def crear(self, cur, comprobante_codigo, suscripcion_id, vehiculo_id, propietario,
              tipo_vehiculo, periodo_etiqueta, fecha_inicio_periodo, fecha_fin_periodo,
              valor, metodo_pago, operador_id, fecha_pago):
        cur.execute("""
            INSERT INTO pago_mensualidad(
                comprobante_codigo, suscripcion_id, vehiculo_id, propietario,
                tipo_vehiculo, periodo_etiqueta, fecha_inicio_periodo,
                fecha_fin_periodo, valor, metodo_pago, estado, operador_id, fecha_pago
            ) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'APROBADO', %s, %s)
        """, (
            comprobante_codigo, suscripcion_id, vehiculo_id, propietario,
            tipo_vehiculo, periodo_etiqueta, fecha_inicio_periodo,
            fecha_fin_periodo, valor, metodo_pago, operador_id, fecha_pago
        ))
        return cur.lastrowid

    def asignar_comprobante(self, cur, pago_id, comprobante_codigo):
        cur.execute(
            "UPDATE pago_mensualidad SET comprobante_codigo=%s WHERE id=%s",
            (comprobante_codigo, pago_id)
        )

    def buscar_por_id(self, cur, pago_id, bloquear=False):
        sql = """
            SELECT p.*, v.placa, v.marca, v.color,
                   s.fecha_inicio AS suscripcion_inicio,
                   s.fecha_vencimiento AS suscripcion_vencimiento,
                   op.nombre AS operador_nombre,
                   oa.nombre AS anulado_por_nombre
            FROM pago_mensualidad p
            JOIN vehiculo v ON v.id = p.vehiculo_id
            JOIN suscripcion s ON s.id = p.suscripcion_id
            LEFT JOIN operador op ON op.id = p.operador_id
            LEFT JOIN operador oa ON oa.id = p.anulado_por_id
            WHERE p.id=%s
        """
        if bloquear:
            sql += " FOR UPDATE"
        cur.execute(sql, (pago_id,))
        return cur.fetchone()

    def existe_pago_periodo_activo(self, cur, vehiculo_id, fecha_inicio_periodo, fecha_fin_periodo):
        """Evita duplicidades de pago aprobado sobre el mismo periodo (RNF-02)."""
        cur.execute("""
            SELECT id, comprobante_codigo
            FROM pago_mensualidad
            WHERE vehiculo_id=%s AND estado='APROBADO'
              AND fecha_inicio_periodo=%s AND fecha_fin_periodo=%s
            LIMIT 1
        """, (vehiculo_id, fecha_inicio_periodo, fecha_fin_periodo))
        return cur.fetchone()

    def buscar_ultimo_pago_aprobado(self, cur, suscripcion_id, excluir_pago_id=None):
        if excluir_pago_id:
            cur.execute("""
                SELECT id, fecha_inicio_periodo, fecha_fin_periodo
                FROM pago_mensualidad
                WHERE suscripcion_id=%s AND estado='APROBADO' AND id<>%s
                ORDER BY fecha_fin_periodo DESC, id DESC
                LIMIT 1
            """, (suscripcion_id, excluir_pago_id))
        else:
            cur.execute("""
                SELECT id, fecha_inicio_periodo, fecha_fin_periodo
                FROM pago_mensualidad
                WHERE suscripcion_id=%s AND estado='APROBADO'
                ORDER BY fecha_fin_periodo DESC, id DESC
                LIMIT 1
            """, (suscripcion_id,))
        return cur.fetchone()

    def anular(self, cur, pago_id, admin_id, motivo):
        cur.execute("""
            UPDATE pago_mensualidad
            SET estado='ANULADO', anulado_por_id=%s,
                fecha_anulacion=NOW(), motivo_anulacion=%s
            WHERE id=%s AND estado='APROBADO'
        """, (admin_id, motivo, pago_id))
        return cur.rowcount

    def listar_historial(self, cur, criterio=None, desde=None, hasta=None, estado=None):
        sql = """
            SELECT p.*, v.placa, v.marca, v.color,
                   op.nombre AS operador_nombre,
                   oa.nombre AS anulado_por_nombre
            FROM pago_mensualidad p
            JOIN vehiculo v ON v.id = p.vehiculo_id
            LEFT JOIN operador op ON op.id = p.operador_id
            LEFT JOIN operador oa ON oa.id = p.anulado_por_id
            WHERE 1=1
        """
        params = []
        criterio = criterio.strip() if criterio and criterio.strip() else None
        desde = desde.strip() if desde and desde.strip() else None
        hasta = hasta.strip() if hasta and hasta.strip() else None
        estado = estado.strip().upper() if estado and estado.strip() else None

        if criterio:
            sql += " AND (v.placa LIKE %s OR p.propietario LIKE %s OR p.comprobante_codigo LIKE %s)"
            like = f"%{criterio}%"
            params.extend([like, like, like])
        if desde:
            sql += " AND DATE(p.fecha_pago) >= %s"
            params.append(desde)
        if hasta:
            sql += " AND DATE(p.fecha_pago) <= %s"
            params.append(hasta)
        if estado in ("APROBADO", "ANULADO"):
            sql += " AND p.estado = %s"
            params.append(estado)

        sql += " ORDER BY p.fecha_pago DESC, p.id DESC"
        cur.execute(sql, tuple(params))
        return cur.fetchall()

    def resumen_kpis_mes_actual(self, cur):
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN estado='APROBADO' THEN valor ELSE 0 END), 0) AS recaudo_mes,
                COUNT(*) AS total_pagos_mes,
                COALESCE(SUM(estado='APROBADO'), 0) AS aprobados_mes,
                COALESCE(SUM(estado='ANULADO'), 0) AS anulados_mes
            FROM pago_mensualidad
            WHERE YEAR(fecha_pago) = YEAR(CURDATE())
              AND MONTH(fecha_pago) = MONTH(CURDATE())
        """)
        return cur.fetchone()

    def reporte_ingresos(self, cur, desde=None, hasta=None, tipo_vehiculo=None):
        sql = """
            SELECT
                COUNT(*) AS total_transacciones,
                COALESCE(SUM(estado='APROBADO'), 0) AS cantidad_aprobados,
                COALESCE(SUM(estado='ANULADO'), 0) AS cantidad_anulados,
                COALESCE(SUM(CASE WHEN estado='APROBADO' THEN valor ELSE 0 END), 0) AS ingreso_neto,
                COALESCE(SUM(CASE WHEN estado='ANULADO' THEN valor ELSE 0 END), 0) AS total_anulado,
                COALESCE(SUM(valor), 0) AS recaudo_bruto,
                COALESCE(SUM(CASE WHEN estado='APROBADO' AND tipo_vehiculo='CARRO' THEN valor ELSE 0 END), 0) AS ingresos_carro,
                COALESCE(SUM(CASE WHEN estado='APROBADO' AND tipo_vehiculo='CARRO' THEN 1 ELSE 0 END), 0) AS pagos_carro,
                COALESCE(SUM(CASE WHEN estado='APROBADO' AND tipo_vehiculo='MOTO' THEN valor ELSE 0 END), 0) AS ingresos_moto,
                COALESCE(SUM(CASE WHEN estado='APROBADO' AND tipo_vehiculo='MOTO' THEN 1 ELSE 0 END), 0) AS pagos_moto
            FROM pago_mensualidad
            WHERE 1=1
        """
        params = []
        if desde:
            sql += " AND DATE(fecha_pago) >= %s"
            params.append(desde)
        if hasta:
            sql += " AND DATE(fecha_pago) <= %s"
            params.append(hasta)
        if tipo_vehiculo in ("CARRO", "MOTO"):
            sql += " AND tipo_vehiculo = %s"
            params.append(tipo_vehiculo)

        cur.execute(sql, tuple(params))
        resumen = cur.fetchone()

        # Desglose por método de pago
        sql_metodo = """
            SELECT metodo_pago,
                   COUNT(*) AS cantidad,
                   COALESCE(SUM(valor), 0) AS total
            FROM pago_mensualidad
            WHERE estado='APROBADO'
        """
        params_m = []
        if desde:
            sql_metodo += " AND DATE(fecha_pago) >= %s"
            params_m.append(desde)
        if hasta:
            sql_metodo += " AND DATE(fecha_pago) <= %s"
            params_m.append(hasta)
        if tipo_vehiculo in ("CARRO", "MOTO"):
            sql_metodo += " AND tipo_vehiculo = %s"
            params_m.append(tipo_vehiculo)
        sql_metodo += " GROUP BY metodo_pago ORDER BY total DESC"
        cur.execute(sql_metodo, tuple(params_m))
        por_metodo = cur.fetchall()

        return resumen, por_metodo
