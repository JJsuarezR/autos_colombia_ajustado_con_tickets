# Autos Colombia — Sistema de Gestión de Parqueadero (Con Tickets e Iteración 2)

Aplicación web desarrollada en **Python (Flask)** y **MySQL** bajo arquitectura en 4 capas (`presentacion`, `aplicacion`, `dominio`, `persistencia`).

---

## Paso a paso para ejecutar `app.py`

### Paso 1: Verificar requisitos previos
- Tener instalado **Python 3.10 o superior**.
- Tener instalado y en ejecución **MySQL Server** (puedes verificarlo desde MySQL Workbench o los servicios del sistema operativo).

### Paso 2: Ubicar la carpeta del proyecto en la terminal
Abre una terminal (PowerShell, CMD o Bash) y navega hasta la carpeta donde está `app.py`:
```bash
cd autos_colombia_ajustado_mysql/autos_colombia_ajustado
```

### Paso 3: Crear y activar el entorno virtual de Python
- **En Windows (PowerShell / CMD):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```
- **En Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### Paso 4: Instalar las dependencias del proyecto
Con el entorno virtual activado, instala las librerías listadas en `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Paso 5: Configurar las variables de conexión a MySQL
Configura los datos de acceso a tu servidor MySQL en la misma terminal (por defecto usa `127.0.0.1`, puerto `3306`, usuario `root`, sin contraseña y base de datos `parqueadero`):
- **En Windows (PowerShell):**
  ```powershell
  $env:DB_HOST="127.0.0.1"
  $env:DB_PORT="3306"
  $env:DB_USER="root"
  $env:DB_PASSWORD="tu_clave_mysql"
  $env:DB_NAME="parqueadero"
  ```
- **En Linux / macOS:**
  ```bash
  export DB_HOST=127.0.0.1
  export DB_PORT=3306
  export DB_USER=root
  export DB_PASSWORD=tu_clave_mysql
  export DB_NAME=parqueadero
  ```
*(Nota: No necesitas ejecutar `schema.sql` manualmente a menos que uses un usuario MySQL sin permisos de creación/alteración de tablas; al arrancar `app.py`, el sistema crea o actualiza automáticamente la base `parqueadero` sin borrar datos existentes).*

### Paso 6: Ejecutar la aplicación
```bash
python app.py
```
Verás en consola que el servidor queda activo en: **`http://127.0.0.1:5000`**

### Paso 7: Iniciar sesión con el Administrador inicial
Abre **`http://127.0.0.1:5000`** en tu navegador e ingresa con las credenciales del administrador creado automáticamente en el primer arranque:
- **Usuario:** `admin`
- **Correo electrónico:** `admin@autoscolombia.com`
- **Contraseña:** `Admin123*`

> **Recomendación de seguridad:** Una vez dentro del sistema, ve al menú **Usuarios**, edita el administrador para cambiar la contraseña inicial y crea las cuentas de los operadores.

---

## Funcionalidades principales del sistema

1. **Control de Entrada en dos pasos (`/entrada`)**:
   - **Opción 1 — Registrar vehículo nuevo**: Registra placa (`ABC123` para carro; `ABC12` o `ABC12D` para moto), tipo, marca y color en el catálogo.
   - **Opción 2 — Registrar entrada (vehículo existente)**: Valida que el vehículo exista en el catálogo, asigna la primera celda libre de su tipo y genera el ticket imprimible (`AC-YYYYMMDD-000001`).
2. **Registro de Salida (`/salida`)**:
   - Permite dar salida digitando tanto la **placa del vehículo** como el **código del ticket**, liberando la celda y calculando el tiempo de permanencia.
3. **Gestión de Celdas (`/celdas`)**:
   - Consulta en tiempo real de celdas disponibles y ocupadas, filtros por código/placa/ticket, tipo y zona, edición de celdas disponibles y creación de nuevas celdas (rol Administrador).
4. **Gestión de Usuarios y Protección de Administrador (`/operadores`)**:
   - Inicio de sesión por usuario o correo electrónico, creación, edición, desactivación/reactivación lógica y regla de integridad que impide desactivar o quitar el rol cuando solo queda **1 administrador activo**.
5. **Historial y Auditoría (`/historial`)**:
   - Filtro por placa, ticket y rango de fechas, más registro de trazabilidad (`auditoria_sistema`).
