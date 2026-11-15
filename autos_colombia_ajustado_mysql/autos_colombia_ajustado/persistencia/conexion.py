"""Conexión MySQL e inicialización/migración compatible con el esquema original."""

import pymysql
from werkzeug.security import generate_password_hash


def conectar(config):
    return pymysql.connect(
        host=config["MYSQL_HOST"],
        port=config["MYSQL_PORT"],
        user=config["MYSQL_USER"],
        password=config["MYSQL_PASSWORD"],
        database=config["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def _columna_existe(cursor, tabla, columna):
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s
    """, (tabla, columna))
    return cursor.fetchone()["total"] > 0


def _indice_existe(cursor, tabla, indice):
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s AND INDEX_NAME=%s
    """, (tabla, indice))
    return cursor.fetchone()["total"] > 0


def inicializar_base_datos(config):
    """Agrega las tablas/columnas requeridas sin borrar datos previos."""
    conn = pymysql.connect(
        host=config["MYSQL_HOST"], port=config["MYSQL_PORT"],
        user=config["MYSQL_USER"], password=config["MYSQL_PASSWORD"],
        charset="utf8mb4", autocommit=True
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config['MYSQL_DATABASE']}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        conn.close()

    db = conectar(config)
    try:
        with db.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vehiculo (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    placa VARCHAR(10) NOT NULL UNIQUE,
                    tipo ENUM('CARRO','MOTO') NOT NULL,
                    marca VARCHAR(80) NULL,
                    color VARCHAR(50) NULL
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS celda (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    codigo VARCHAR(10) NOT NULL UNIQUE,
                    numero INT NOT NULL,
                    tipo ENUM('CARRO','MOTO') NOT NULL,
                    zona VARCHAR(60) NOT NULL DEFAULT 'General',
                    estado ENUM('Disponible','Ocupada') NOT NULL DEFAULT 'Disponible'
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS operador (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(120) NOT NULL,
                    usuario VARCHAR(60) NOT NULL UNIQUE,
                    correo VARCHAR(120) NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    rol ENUM('ADMIN','OPERADOR') NOT NULL DEFAULT 'OPERADOR',
                    activo TINYINT(1) NOT NULL DEFAULT 1,
                    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en DATETIME NULL
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS estancia (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    vehiculo_id INT NOT NULL,
                    celda_id INT NOT NULL,
                    vehiculo_activo_id INT NULL UNIQUE,
                    celda_activa_id INT NULL UNIQUE,
                    operador_entrada_id INT NULL,
                    operador_salida_id INT NULL,
                    fecha_entrada DATETIME NOT NULL,
                    fecha_salida DATETIME NULL,
                    ticket_codigo VARCHAR(32) NULL UNIQUE,
                    CONSTRAINT fk_estancia_vehiculo FOREIGN KEY (vehiculo_id) REFERENCES vehiculo(id),
                    CONSTRAINT fk_estancia_celda FOREIGN KEY (celda_id) REFERENCES celda(id)
                ) ENGINE=InnoDB
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auditoria_sistema (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    operador_id INT NULL,
                    entidad VARCHAR(40) NOT NULL,
                    entidad_id INT NULL,
                    accion VARCHAR(40) NOT NULL,
                    detalle VARCHAR(255) NOT NULL,
                    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_auditoria_operador FOREIGN KEY (operador_id) REFERENCES operador(id)
                ) ENGINE=InnoDB
            """)

            # Migra instalaciones existentes sin eliminar vehículos ni movimientos.
            if not _columna_existe(cur, "vehiculo", "marca"):
                cur.execute("ALTER TABLE vehiculo ADD COLUMN marca VARCHAR(80) NULL")
            if not _columna_existe(cur, "vehiculo", "color"):
                cur.execute("ALTER TABLE vehiculo ADD COLUMN color VARCHAR(50) NULL")
            if not _columna_existe(cur, "estancia", "ticket_codigo"):
                cur.execute("ALTER TABLE estancia ADD COLUMN ticket_codigo VARCHAR(32) NULL UNIQUE")

            if not _columna_existe(cur, "estancia", "operador_entrada_id"):
                cur.execute("ALTER TABLE estancia ADD COLUMN operador_entrada_id INT NULL")
            if not _columna_existe(cur, "estancia", "operador_salida_id"):
                cur.execute("ALTER TABLE estancia ADD COLUMN operador_salida_id INT NULL")

            # Columnas Iteración 2
            if not _columna_existe(cur, "operador", "correo"):
                cur.execute("ALTER TABLE operador ADD COLUMN correo VARCHAR(120) NULL AFTER usuario")
            if not _indice_existe(cur, "operador", "uq_operador_correo"):
                cur.execute("ALTER TABLE operador ADD CONSTRAINT uq_operador_correo UNIQUE (correo)")
            if not _columna_existe(cur, "operador", "actualizado_en"):
                cur.execute("ALTER TABLE operador ADD COLUMN actualizado_en DATETIME NULL")

            if not _columna_existe(cur, "celda", "zona"):
                cur.execute("ALTER TABLE celda ADD COLUMN zona VARCHAR(60) NOT NULL DEFAULT 'General' AFTER tipo")

            # Registra las llaves foráneas de operadores solo si aún no existen.
            cur.execute("""
                SELECT COUNT(*) AS total FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estancia'
                  AND CONSTRAINT_NAME='fk_estancia_operador_entrada'
            """)
            if cur.fetchone()["total"] == 0:
                cur.execute("""
                    ALTER TABLE estancia ADD CONSTRAINT fk_estancia_operador_entrada
                    FOREIGN KEY (operador_entrada_id) REFERENCES operador(id)
                """)
            cur.execute("""
                SELECT COUNT(*) AS total FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='estancia'
                  AND CONSTRAINT_NAME='fk_estancia_operador_salida'
            """)
            if cur.fetchone()["total"] == 0:
                cur.execute("""
                    ALTER TABLE estancia ADD CONSTRAINT fk_estancia_operador_salida
                    FOREIGN KEY (operador_salida_id) REFERENCES operador(id)
                """)

            cur.execute("SELECT id, correo FROM operador WHERE usuario=%s", ("admin",))
            admin_row = cur.fetchone()
            if not admin_row:
                cur.execute("""
                    INSERT INTO operador(nombre,usuario,correo,password_hash,rol)
                    VALUES(%s,%s,%s,%s,'ADMIN')
                """, ("Administrador", "admin", "admin@autoscolombia.com", generate_password_hash("Admin123*")))
            elif not admin_row.get("correo"):
                cur.execute("""
                    UPDATE operador SET correo=%s WHERE id=%s
                """, ("admin@autoscolombia.com", admin_row["id"]))

            # Si había estancias antiguas, se asigna el operador administrador como responsable histórico.
            cur.execute("SELECT id FROM operador WHERE usuario=%s", ("admin",))
            admin_id = cur.fetchone()["id"]
            cur.execute("""
                UPDATE estancia SET operador_entrada_id=%s
                WHERE operador_entrada_id IS NULL
            """, (admin_id,))

            # Conserva la distribución original: 10 celdas de moto y 70 de carro.
            for i in range(1, 11):
                cur.execute("""
                    INSERT IGNORE INTO celda(codigo,numero,tipo,zona,estado)
                    VALUES(%s,%s,'MOTO','Zona Motos','Disponible')
                """, (f"M-{i:02d}", i))
            for i in range(1, 71):
                zona = "Zona A" if i <= 20 else ("Zona B" if i <= 40 else "Zona C")
                cur.execute("""
                    INSERT IGNORE INTO celda(codigo,numero,tipo,zona,estado)
                    VALUES(%s,%s,'CARRO',%s,'Disponible')
                """, (f"C-{i:02d}", i, zona))

            cur.execute("UPDATE celda SET zona='Zona Motos' WHERE tipo='MOTO' AND zona='General'")
            cur.execute("UPDATE celda SET zona='Zona A' WHERE tipo='CARRO' AND numero<=20 AND zona='General'")
            cur.execute("UPDATE celda SET zona='Zona B' WHERE tipo='CARRO' AND numero BETWEEN 21 AND 40 AND zona='General'")
            cur.execute("UPDATE celda SET zona='Zona C' WHERE tipo='CARRO' AND numero>=41 AND zona='General'")

            # Recalcula estados desde las estancias activas, no elimina movimientos.
            cur.execute("""
                UPDATE celda c
                LEFT JOIN estancia e ON e.celda_activa_id=c.id
                SET c.estado=IF(e.id IS NULL,'Disponible','Ocupada')
            """)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
