# Autos Colombia — versión ajustada sobre el proyecto original

Esta versión conserva la lógica funcional del ZIP original: entrada automática, validación de placa, asignación de la primera celda libre del tipo correspondiente, bloqueo de doble entrada, salida por placa, liberación de celda, cálculo de permanencia, vista de celdas y últimas salidas.

## Ajustes solicitados
- Arquitectura separada en `presentacion`, `aplicacion`, `persistencia` y `dominio`.
- Base de datos MySQL, administrable desde MySQL Workbench.
- Salida digitando la placa, igual que en el original.
- Registro de marca y color por placa; los vehículos existentes se reconocen por su placa y no requieren volver a diligenciar esos datos.
- Ticket de ingreso numerado, guardado en la estancia y con opción de impresión (formato adaptable a impresora térmica de 80 mm).
- Operadores con inicio de sesión; cada estancia registra operador de entrada y operador de salida.
- Solo dos tipos: CARRO y MOTO.
- Cuatro paneles principales: panel principal, registro de entrada, registro de salida e historial.
- Historial filtrable por placa, fecha inicial y fecha final.
- Se conserva la capacidad inicial: 70 celdas de carro y 10 de moto.

## Requisitos
- Python 3.10 o superior.
- MySQL Server instalado y en ejecución.
- MySQL Workbench (para administrar/consultar la base de datos).

## Configuración de MySQL
1. Abra MySQL Workbench y conéctese a su servidor local.
2. Abra `schema.sql` y ejecútelo con el botón del rayo. Crea la base `parqueadero`, tablas y 80 celdas.
3. Configure su conexión a MySQL (los mismos datos de Workbench) con variables de entorno:
   - Windows (PowerShell): `$env:DB_USER="root"; $env:DB_PASSWORD="su_clave"`
   - Linux/macOS: `export DB_USER=root DB_PASSWORD=su_clave`

   (Opcionales: `DB_HOST`, `DB_PORT`, `DB_NAME`; por defecto `127.0.0.1`, `3306`, `parqueadero`.)
   ```
   Si su usuario no tiene contraseña, puede dejar `DB_PASSWORD` vacío.
4. Instale y ejecute:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python app.py
   ```
5. Abra `http://127.0.0.1:5000`.

### Nuevas funciones de ingreso y ticket
- En **Entrada**, escriba la placa. Si la placa ya está registrada y tiene marca/color, solo necesita la placa; el sistema recupera automáticamente tipo, marca y color.
- Si la placa es nueva, complete también marca, color y tipo de vehículo. Si la placa existía de una versión anterior pero no tenía marca/color, el sistema solicitará completar esos dos datos una sola vez.
- Al confirmar el ingreso, se crea un código de ticket único (`AC-fecha-id`) asociado a la estancia y se abre el comprobante imprimible. Use **Imprimir ticket**; puede seleccionar una impresora normal o térmica de 80 mm en el diálogo del navegador.
- El ticket puede volver a abrirse desde la lista de vehículos dentro del parqueadero y desde el historial. Los ingresos anteriores a esta actualización no tienen ticket retroactivo.
- Al iniciar la versión actualizada, la aplicación agrega automáticamente las columnas `marca`, `color` y `ticket_codigo` a la base existente. No borra los vehículos ni las estancias. Aun así, haga una copia de seguridad antes de actualizar.

## Primer acceso
- Usuario: `admin`
- Contraseña: `Admin123*`

El primer arranque crea el operador administrador si no existe. Inicie sesión y cree los demás operadores desde el menú **Operadores**. Las contraseñas se almacenan como hash, no en texto plano. Cambie la contraseña inicial antes de exponer el sistema.

## Reglas de placas
- Carro: `ABC123`.
- Moto: `ABC12` o `ABC12D`.
Se aceptan espacios o guiones al digitar y se normalizan.

## Nota para bases existentes
La inicialización agrega las columnas de operador que falten a `estancia`, marca y color a `vehiculo`, y el código de ticket a `estancia`; crea la tabla `operador`, crea celdas faltantes y conserva los registros previos. Los vehículos que ya existían antes de agregar marca y color conservarán esos campos vacíos hasta que se actualicen. Las estancias antiguas sin operador de origen se atribuyen al administrador inicial para no dejar los campos históricos sin responsable. Haga copia de seguridad antes de actualizar una base que ya tenga información.

## Capas
- `presentacion/controladores.py`: controladores Flask y navegación.
- `aplicacion/servicio_estancias.py`: reglas de negocio de entrada y salida.
- `persistencia/*_repository.py`: consultas e inserciones por entidad.
- `persistencia/conexion.py`: conexión, creación y actualización del esquema.
- `dominio/entidades.py`: entidades del negocio.

## Alcance conservado
No se incorporan pagos, mensualidades ni novedades porque no hacen parte de las funciones del ZIP original que se pidió conservar.
