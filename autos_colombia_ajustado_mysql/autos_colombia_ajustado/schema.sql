-- Autos Colombia (Iteración 1 con Tickets + Iteración 2). Ejecutar en MySQL Workbench.
-- El script crea o actualiza el esquema, tablas, trazabilidad y 80 celdas iniciales sin borrar datos.
CREATE DATABASE IF NOT EXISTS parqueadero
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE parqueadero;

CREATE TABLE IF NOT EXISTS vehiculo (
  id INT AUTO_INCREMENT PRIMARY KEY,
  placa VARCHAR(10) NOT NULL UNIQUE,
  tipo ENUM('CARRO','MOTO') NOT NULL,
  marca VARCHAR(80) NULL,
  color VARCHAR(50) NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS celda (
  id INT AUTO_INCREMENT PRIMARY KEY,
  codigo VARCHAR(10) NOT NULL UNIQUE,
  numero INT NOT NULL,
  tipo ENUM('CARRO','MOTO') NOT NULL,
  zona VARCHAR(60) NOT NULL DEFAULT 'General',
  estado ENUM('Disponible','Ocupada') NOT NULL DEFAULT 'Disponible'
) ENGINE=InnoDB;

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
) ENGINE=InnoDB;

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
  CONSTRAINT fk_estancia_celda FOREIGN KEY (celda_id) REFERENCES celda(id),
  CONSTRAINT fk_estancia_operador_entrada FOREIGN KEY (operador_entrada_id) REFERENCES operador(id),
  CONSTRAINT fk_estancia_operador_salida FOREIGN KEY (operador_salida_id) REFERENCES operador(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS auditoria_sistema (
  id INT AUTO_INCREMENT PRIMARY KEY,
  operador_id INT NULL,
  entidad VARCHAR(40) NOT NULL,
  entidad_id INT NULL,
  accion VARCHAR(40) NOT NULL,
  detalle VARCHAR(255) NOT NULL,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_auditoria_operador FOREIGN KEY (operador_id) REFERENCES operador(id)
) ENGINE=InnoDB;

-- Operador administrador inicial: el hash se crea automáticamente al ejecutar app.py.
-- Usuario: admin | Correo: admin@autoscolombia.com | Clave inicial: Admin123*

INSERT IGNORE INTO celda(codigo,numero,tipo,zona,estado) VALUES
('M-01',1,'MOTO','Zona Motos','Disponible'),('M-02',2,'MOTO','Zona Motos','Disponible'),
('M-03',3,'MOTO','Zona Motos','Disponible'),('M-04',4,'MOTO','Zona Motos','Disponible'),
('M-05',5,'MOTO','Zona Motos','Disponible'),('M-06',6,'MOTO','Zona Motos','Disponible'),
('M-07',7,'MOTO','Zona Motos','Disponible'),('M-08',8,'MOTO','Zona Motos','Disponible'),
('M-09',9,'MOTO','Zona Motos','Disponible'),('M-10',10,'MOTO','Zona Motos','Disponible'),
('C-01',1,'CARRO','Zona A','Disponible'),('C-02',2,'CARRO','Zona A','Disponible'),
('C-03',3,'CARRO','Zona A','Disponible'),('C-04',4,'CARRO','Zona A','Disponible'),
('C-05',5,'CARRO','Zona A','Disponible'),('C-06',6,'CARRO','Zona A','Disponible'),
('C-07',7,'CARRO','Zona A','Disponible'),('C-08',8,'CARRO','Zona A','Disponible'),
('C-09',9,'CARRO','Zona A','Disponible'),('C-10',10,'CARRO','Zona A','Disponible'),
('C-11',11,'CARRO','Zona A','Disponible'),('C-12',12,'CARRO','Zona A','Disponible'),
('C-13',13,'CARRO','Zona A','Disponible'),('C-14',14,'CARRO','Zona A','Disponible'),
('C-15',15,'CARRO','Zona A','Disponible'),('C-16',16,'CARRO','Zona A','Disponible'),
('C-17',17,'CARRO','Zona A','Disponible'),('C-18',18,'CARRO','Zona A','Disponible'),
('C-19',19,'CARRO','Zona A','Disponible'),('C-20',20,'CARRO','Zona A','Disponible'),
('C-21',21,'CARRO','Zona B','Disponible'),('C-22',22,'CARRO','Zona B','Disponible'),
('C-23',23,'CARRO','Zona B','Disponible'),('C-24',24,'CARRO','Zona B','Disponible'),
('C-25',25,'CARRO','Zona B','Disponible'),('C-26',26,'CARRO','Zona B','Disponible'),
('C-27',27,'CARRO','Zona B','Disponible'),('C-28',28,'CARRO','Zona B','Disponible'),
('C-29',29,'CARRO','Zona B','Disponible'),('C-30',30,'CARRO','Zona B','Disponible'),
('C-31',31,'CARRO','Zona B','Disponible'),('C-32',32,'CARRO','Zona B','Disponible'),
('C-33',33,'CARRO','Zona B','Disponible'),('C-34',34,'CARRO','Zona B','Disponible'),
('C-35',35,'CARRO','Zona B','Disponible'),('C-36',36,'CARRO','Zona B','Disponible'),
('C-37',37,'CARRO','Zona B','Disponible'),('C-38',38,'CARRO','Zona B','Disponible'),
('C-39',39,'CARRO','Zona B','Disponible'),('C-40',40,'CARRO','Zona B','Disponible'),
('C-41',41,'CARRO','Zona C','Disponible'),('C-42',42,'CARRO','Zona C','Disponible'),
('C-43',43,'CARRO','Zona C','Disponible'),('C-44',44,'CARRO','Zona C','Disponible'),
('C-45',45,'CARRO','Zona C','Disponible'),('C-46',46,'CARRO','Zona C','Disponible'),
('C-47',47,'CARRO','Zona C','Disponible'),('C-48',48,'CARRO','Zona C','Disponible'),
('C-49',49,'CARRO','Zona C','Disponible'),('C-50',50,'CARRO','Zona C','Disponible'),
('C-51',51,'CARRO','Zona C','Disponible'),('C-52',52,'CARRO','Zona C','Disponible'),
('C-53',53,'CARRO','Zona C','Disponible'),('C-54',54,'CARRO','Zona C','Disponible'),
('C-55',55,'CARRO','Zona C','Disponible'),('C-56',56,'CARRO','Zona C','Disponible'),
('C-57',57,'CARRO','Zona C','Disponible'),('C-58',58,'CARRO','Zona C','Disponible'),
('C-59',59,'CARRO','Zona C','Disponible'),('C-60',60,'CARRO','Zona C','Disponible'),
('C-61',61,'CARRO','Zona C','Disponible'),('C-62',62,'CARRO','Zona C','Disponible'),
('C-63',63,'CARRO','Zona C','Disponible'),('C-64',64,'CARRO','Zona C','Disponible'),
('C-65',65,'CARRO','Zona C','Disponible'),('C-66',66,'CARRO','Zona C','Disponible'),
('C-67',67,'CARRO','Zona C','Disponible'),('C-68',68,'CARRO','Zona C','Disponible'),
('C-69',69,'CARRO','Zona C','Disponible'),('C-70',70,'CARRO','Zona C','Disponible');
