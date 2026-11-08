import os
from flask import Flask
from persistencia.conexion import inicializar_base_datos
from presentacion.controladores import registrar_controladores

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambiar-esta-clave-antes-de-publicar")
app.config["MYSQL_HOST"] = os.getenv("DB_HOST", "127.0.0.1")
app.config["MYSQL_PORT"] = int(os.getenv("DB_PORT", "3306"))
app.config["MYSQL_USER"] = os.getenv("DB_USER", "root")
app.config["MYSQL_PASSWORD"] = os.getenv("DB_PASSWORD", "")
app.config["MYSQL_DATABASE"] = os.getenv("DB_NAME", "parqueadero")

inicializar_base_datos(app.config)
registrar_controladores(app)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
