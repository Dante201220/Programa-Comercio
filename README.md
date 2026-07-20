Markdown
# 🛒 Sistema de Gestión para Comercio

¡Hola! Este es un sistema de gestión y ventas desarrollado con **Flask** y **SQL Server**. Está pensado para resolver el día a día de un negocio: controlar el acceso de usuarios, gestionar el carrito de compras y procesar las ventas de forma ágil y segura. 

El foco principal de este proyecto no fue solo que funcione bien, sino que esté construido siguiendo las **buenas prácticas de seguridad y arquitectura** que se usan en el mundo profesional.

---

## 🛠️ Tecnologías utilizadas

* **Backend:** Python con Flask (sencillo, rápido y potente).
* **Base de Datos:** SQL Server (robusta y lista para manejar relaciones complejas).
* **Frontend:** HTML5, CSS3 y JavaScript para una experiencia limpia en el navegador.

---

## 🔒 Seguridad

A la hora de desarrollar el backend, me enfoqué en blindar la aplicación para que sea segura desde el día uno:

1. **Contraseñas encriptadas (Hashing):** En este sistema **nadie** conoce la contraseña real del usuario, ni siquiera el administrador de la base de datos. Usando la librería `werkzeug.security`, las claves se transforman en un hash seguro (`scrypt`) antes de guardarse en SQL Server. Al iniciar sesión, el sistema compara los hashes, nunca el texto plano.
2. **Variables de Entorno (.env):** Las credenciales de la base de datos y las claves secretas de la sesión de Flask están completamente aisladas del código principal. Usando `python-dotenv`, el sistema lee las configuraciones de forma local y el archivo sensible está protegido por `.gitignore`, asegurando que jamás se suban datos críticos a GitHub.

---

## 📂 Estructura del Proyecto

El código está organizado de forma limpia y escalable:
* `/templates`: Toda la interfaz visual (`carrito.html`, `ventas.html`, login, etc.).
* `/static`: Los estilos y scripts que le dan vida al diseño.
* `app.py`: El cerebro del backend, donde se manejan las rutas, la lógica de negocio y la conexión a la base de datos.
* `Create_Comercio.sql`: El script de estructura listo para montar la base de datos desde cero.

---

## 🚀 Cómo correrlo en tu computadora

Si querés probar el proyecto de forma local, necesitás tener instalado Python y SQL Server.

1. **Cloná este repositorio:**
   ```bash
   git clone [https://github.com/Dante201220/Programa-Comercio.git](https://github.com/Dante201220/Programa-Comercio.git)
Instalá las dependencias:

Bash
pip install flask pyodbc python-dotenv
Configurá tus variables de entorno:
Creá un archivo .env en la raíz del proyecto con la siguiente estructura (reemplazando con tus datos reales):

Fragmento de código
FLASK_SECRET_KEY=tu_clave_secreta_aqui
DB_SERVER=TU_SERVIDOR_SQL\SQLEXPRESS
DB_NAME=Gestion Comercio
Ejecutá la aplicación:

Bash
python app.py
¡Listo! Abrí tu navegador en http://127.0.0.1:5000


---

### ¿Cómo lo subís ahora?
Una vez que crees el archivo y pegues esto, volvés a tu Git Bash y tirás estos tres comandos para actualizar tu GitHub:

```bash
git add README.md
git commit -m "Docs: Agregar README detallado para el portafolio"
git push origin main
