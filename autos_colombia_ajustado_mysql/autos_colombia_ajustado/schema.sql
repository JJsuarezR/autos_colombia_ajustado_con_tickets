-- Autos Colombia. Ejecutar en MySQL Workbench.
-- El script crea el esquema, tablas y 80 celdas iniciales.
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
  estado ENUM('Disponible','Ocupada') NOT NULL DEFAULT 'Disponible'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS operador (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  usuario VARCHAR(60) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  rol ENUM('ADMIN','OPERADOR') NOT NULL DEFAULT 'OPERADOR',
  activo TINYINT(1) NOT NULL DEFAULT 1,
  creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
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

-- Operador administrador inicial: el hash se crea al ejecutar app.py.
-- La tabla operador queda lista y app.py agrega el usuario admin si no existe.

INSERT IGNORE INTO celda(codigo,numero,tipo,estado) VALUES
('M-01',1,'MOTO','Disponible'),('M-02',2,'MOTO','Disponible'),
('M-03',3,'MOTO','Disponible'),('M-04',4,'MOTO','Disponible'),
('M-05',5,'MOTO','Disponible'),('M-06',6,'MOTO','Disponible'),
('M-07',7,'MOTO','Disponible'),('M-08',8,'MOTO','Disponible'),
('M-09',9,'MOTO','Disponible'),('M-10',10,'MOTO','Disponible'),
('C-01',1,'CARRO','Disponible'),('C-02',2,'CARRO','Disponible'),
('C-03',3,'CARRO','Disponible'),('C-04',4,'CARRO','Disponible'),
('C-05',5,'CARRO','Disponible'),('C-06',6,'CARRO','Disponible'),
('C-07',7,'CARRO','Disponible'),('C-08',8,'CARRO','Disponible'),
('C-09',9,'CARRO','Disponible'),('C-10',10,'CARRO','Disponible'),
('C-11',11,'CARRO','Disponible'),('C-12',12,'CARRO','Disponible'),
('C-13',13,'CARRO','Disponible'),('C-14',14,'CARRO','Disponible'),
('C-15',15,'CARRO','Disponible'),('C-16',16,'CARRO','Disponible'),
('C-17',17,'CARRO','Disponible'),('C-18',18,'CARRO','Disponible'),
('C-19',19,'CARRO','Disponible'),('C-20',20,'CARRO','Disponible'),
('C-21',21,'CARRO','Disponible'),('C-22',22,'CARRO','Disponible'),
('C-23',23,'CARRO','Disponible'),('C-24',24,'CARRO','Disponible'),
('C-25',25,'CARRO','Disponible'),('C-26',26,'CARRO','Disponible'),
('C-27',27,'CARRO','Disponible'),('C-28',28,'CARRO','Disponible'),
('C-29',29,'CARRO','Disponible'),('C-30',30,'CARRO','Disponible'),
('C-31',31,'CARRO','Disponible'),('C-32',32,'CARRO','Disponible'),
('C-33',33,'CARRO','Disponible'),('C-34',34,'CARRO','Disponible'),
('C-35',35,'CARRO','Disponible'),('C-36',36,'CARRO','Disponible'),
('C-37',37,'CARRO','Disponible'),('C-38',38,'CARRO','Disponible'),
('C-39',39,'CARRO','Disponible'),('C-40',40,'CARRO','Disponible'),
('C-41',41,'CARRO','Disponible'),('C-42',42,'CARRO','Disponible'),
('C-43',43,'CARRO','Disponible'),('C-44',44,'CARRO','Disponible'),
('C-45',45,'CARRO','Disponible'),('C-46',46,'CARRO','Disponible'),
('C-47',47,'CARRO','Disponible'),('C-48',48,'CARRO','Disponible'),
('C-49',49,'CARRO','Disponible'),('C-50',50,'CARRO','Disponible'),
('C-51',51,'CARRO','Disponible'),('C-52',52,'CARRO','Disponible'),
('C-53',53,'CARRO','Disponible'),('C-54',54,'CARRO','Disponible'),
('C-55',55,'CARRO','Disponible'),('C-56',56,'CARRO','Disponible'),
('C-57',57,'CARRO','Disponible'),('C-58',58,'CARRO','Disponible'),
('C-59',59,'CARRO','Disponible'),('C-60',60,'CARRO','Disponible'),
('C-61',61,'CARRO','Disponible'),('C-62',62,'CARRO','Disponible'),
('C-63',63,'CARRO','Disponible'),('C-64',64,'CARRO','Disponible'),
('C-65',65,'CARRO','Disponible'),('C-66',66,'CARRO','Disponible'),
('C-67',67,'CARRO','Disponible'),('C-68',68,'CARRO','Disponible'),
('C-69',69,'CARRO','Disponible'),('C-70',70,'CARRO','Disponible');
