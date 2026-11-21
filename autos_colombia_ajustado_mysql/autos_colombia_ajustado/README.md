# Autos Colombia — Sistema de Gestión de Parqueadero (Iteración 1, 2 y 3)

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
*(Nota: Al arrancar `app.py`, el sistema crea o actualiza automáticamente la base `parqueadero` y sus tablas sin borrar datos previos).*

### Paso 6: Ejecutar la aplicación
```bash
python app.py
```
El servidor quedará activo en **`http://127.0.0.1:5000`**.

### Paso 7: Iniciar sesión con el Administrador inicial
Abre **`http://127.0.0.1:5000`** en tu navegador e ingresa con las credenciales del administrador inicial:
- **Usuario:** `admin`
- **Correo electrónico:** `admin@autoscolombia.com`
- **Contraseña:** `Admin123*`

---

## Funcionalidades por Iteración

### Iteración 1 — Entradas, Salidas y Tickets
- Registro de vehículos nuevos (`ABC123` para carro; `ABC12` o `ABC12D` para moto) con marca, color y propietario.
- Registro de entrada con asignación automática de celda y generación de ticket imprimible en 80 mm (`AC-YYYYMMDD-000001`).
- Registro de salida digitando **placa** o **código de ticket**, liberando celda y calculando permanencia.

### Iteración 2 — Gestión de Celdas y Usuarios
- **Celdas (`/celdas`)**: Consulta en tiempo real de celdas disponibles y ocupadas; **la modificación y creación de celdas es exclusiva del rol Administrador** (el operador solo tiene vista de consulta).
- **Usuarios (`/operadores`)**: Inicio de sesión por correo o usuario, creación, edición, desactivación/reactivación lógica y protección que impide dejar menos de **1 administrador activo**.

### Iteración 3 — Pagos de Mensualidad y Suscripciones (`/pagos`)
- **Modelo de suscripción mensual**: Tarifas fijas automáticas de **$250.000 para Carros** y **$100.000 para Motos** (sin cobros por hora o día).
- **Control de acceso en Entrada**: Si el vehículo no cuenta con una mensualidad vigente, el sistema bloquea el ingreso al parqueadero.
- **Operaciones de Operador y Administrador**: Validar vehículo, calcular tarifa, consultar estado de suscripción, registrar pago mensual (Efectivo, Tarjeta o Transferencia), actualizar vigencia y generar comprobante imprimible (`PAG-YYYYMMDD-00001`).
- **Funciones exclusivas de Administrador**: Consultar historial completo de pagos, buscar por placa/propietario/comprobante/fecha, exportar CSV, anular pagos con motivo obligatorio y auditoría (`auditoria_sistema`), y generar reportes financieros de ingresos.
