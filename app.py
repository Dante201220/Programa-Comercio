import os
import pyodbc
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)

# La clave secreta ahora se lee de forma segura desde el entorno
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'clave_temporal_desarrollo_123')

# Configuraciones de seguridad extra para el manejo de sesiones
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # Protege las cookies contra ataques XSS
    SESSION_COOKIE_SAMESITE='Lax',  # Ayuda a mitigar ataques CSRF
)

# ===================================================
#   CONEXIÓN A BASE DE DATOS DINÁMICA
# ===================================================

def get_db_connection():
    try:
        # Extraemos los datos del servidor sin exponerlos en el código
        server = os.environ.get('DB_SERVER')
        database = os.environ.get('DB_NAME')
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'Trusted_Connection=yes;'
        )
        return conn
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# ===================================================
#   HERRAMIENTA TEMPORAL: GENERADOR DE HASH
# ===================================================
# Pasos para usar esto:
# 1. Corré tu app y entrá a http://127.0.0.1:5000/nuevo-hash
# 2. Copiá el código largo encriptado que sale en pantalla.
# 3. Ponelo en tu script SQL para actualizar tu base de datos.
# 4. Una vez hecho esto, podés borrar esta ruta si querés.
@app.route('/nuevo-hash')
def generar_hash_temporal():
    password_original = "admin123"  # Modificá esto si querés usar otra contraseña
    hash_generado = generate_password_hash(password_original)
    return f"""
    <div style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
        <h3>Tu hash seguro para la Base de Datos es:</h3>
        <textarea style="width: 100%; height: 70px; font-family: monospace; font-size: 14px; padding: 10px;" readonly>{hash_generado}</textarea>
        <p style="color: #666; font-size: 13px; margin-top: 10px;">
            Copiá absolutamente todo el texto del cuadro de arriba y usalo en el <code>INSERT</code> de tu base de datos.
        </p>
    </div>
    """

# ===================================================
#   RUTAS PÚBLICAS Y CARRITO (CLIENTE)
# ===================================================

@app.route('/')
def catalogo():
    search = request.args.get('search', '').strip()
    categoria_id = request.args.get('categoria', '').strip()
    
    conn = get_db_connection()
    if not conn:
        return "Error de conexión a la BD", 500
    cursor = conn.cursor()
    
    cursor.execute("SELECT id_categoria, nombre_categoria, descripcion FROM Categorias WHERE estado = 1")
    categorias = cursor.fetchall()
    
    query = "SELECT id_producto, nombre, descripcion, precio_venta, stock, imagen_url FROM Productos WHERE 1=1"
    params = []
    
    if search:
        query += " AND (nombre LIKE ? OR descripcion LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    if categoria_id:
        query += " AND id_categoria = ?"
        params.append(int(categoria_id))
        
    cursor.execute(query, params)
    productos = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('Cliente/catalogo.html', productos=productos, categorias=categorias)

@app.route('/producto/<int:id>')
def detalle_producto(id):
    conn = get_db_connection()
    if not conn: 
        return "Error BD", 500
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Productos WHERE id_producto = ?", (id,))
    producto = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('Cliente/detalle.html', producto=producto)

@app.route('/carrito')
def ver_carrito():
    cart_ids = session.get('cart', [])
    if not cart_ids:
        return render_template('Cliente/carrito.html', productos_carrito=[], total=0)

    conteo = Counter(cart_ids)  
    ids_unicos = list(conteo.keys())

    conn = get_db_connection()
    if not conn:
        flash('Error de conexión al cargar el carrito.', 'danger')
        return redirect(url_for('catalogo'))
        
    cursor = conn.cursor()
    
    format_strings = ','.join(['?'] * len(ids_unicos))
    cursor.execute(f"SELECT id_producto, nombre, precio_venta FROM Productos WHERE id_producto IN ({format_strings})", ids_unicos)
    productos_db = cursor.fetchall()
    cursor.close()
    conn.close()

    productos_carrito = []
    total = 0
    for p in productos_db:
        id_p, nombre, precio = p
        cantidad = conteo[id_p]
        subtotal = precio * cantidad
        total += subtotal
        productos_carrito.append({
            'id': id_p,
            'nombre': nombre,
            'precio': precio,
            'cantidad': cantidad,
            'subtotal': subtotal
        })

    return render_template('Cliente/carrito.html', productos_carrito=productos_carrito, total=total)

@app.route('/carrito/add/<int:id>', methods=['GET', 'POST'])
def add_to_cart(id):
    cart = session.get('cart', [])
    
    if request.method == 'POST':
        cantidad_a_agregar = int(request.form.get('cantidad', 1))
    else:
        cantidad_a_agregar = request.args.get('cantidad', 1, type=int)
        
    if cantidad_a_agregar < 1:
        cantidad_a_agregar = 1
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT stock, nombre FROM Productos WHERE id_producto = ?", (id,))
        producto = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if producto:
            stock, nombre = producto
            cantidad_en_carrito = cart.count(id)
            
            if stock >= (cantidad_en_carrito + cantidad_a_agregar):
                for _ in range(cantidad_a_agregar):
                    cart.append(id)
                session['cart'] = cart
                session.modified = True
                flash(f'¡Se agregaron {cantidad_a_agregar} unidades de "{nombre}" al carrito!', 'success')
            else:
                disponibles = stock - cantidad_en_carrito
                if disponibles > 0:
                    flash(f'No podés agregar {cantidad_a_agregar} unidades. Solo quedan {disponibles} disponibles en stock.', 'danger')
                else:
                    flash(f'Lo sentimos, no hay más stock disponible de "{nombre}".', 'danger')
        else:
            flash('El producto seleccionado no existe.', 'danger')
    else:
        flash('Error de conexión al procesar el carrito.', 'danger')
        
    return redirect(request.referrer or url_for('catalogo'))

@app.route('/carrito/remove/<int:id>')
def remove_from_cart(id):
    cart = session.get('cart', [])
    if id in cart:
        cart.remove(id)  
        session['cart'] = cart
        session.modified = True
        flash('Producto quitado del carrito.', 'info')
    return redirect(url_for('ver_carrito'))

@app.route('/carrito/clear')
def clear_cart():
    session.pop('cart', None)
    flash('El carrito fue vaciado con éxito.', 'info')
    return redirect(url_for('ver_carrito'))

@app.route('/carrito/checkout', methods=['POST'])
def checkout():
    cart_ids = session.get('cart', [])
    if not cart_ids:
        flash('Tu carrito está vacío.', 'warning')
        return redirect(url_for('catalogo'))

    cliente_nombre = request.form.get('cliente_nombre', 'Cliente General').strip()
    conteo = Counter(cart_ids)

    conn = get_db_connection()
    if not conn:
        flash('Error al procesar la compra. Reintentá luego.', 'danger')
        return redirect(url_for('ver_carrito'))

    try:
        cursor = conn.cursor()
        
        ids_unicos = list(conteo.keys())
        format_strings = ','.join(['?'] * len(ids_unicos))
        cursor.execute(f"SELECT id_producto, nombre, precio_venta, stock FROM Productos WHERE id_producto IN ({format_strings})", ids_unicos)
        productos = cursor.fetchall()

        total = 0
        items_a_vender = []

        for p in productos:
            id_p, nombre, precio, stock = p
            cantidad = conteo[id_p]
            if stock < cantidad:
                raise ValueError(f"No hay suficiente stock de '{nombre}' (Stock disponible: {stock})")
            
            total += precio * cantidad
            items_a_vender.append((id_p, cantidad, precio))

        cursor.execute("""
            INSERT INTO Ventas (total_venta, cliente_nombre) 
            OUTPUT INSERTED.id_venta 
            VALUES (?, ?)
        """, (total, cliente_nombre))
        id_venta = cursor.fetchone()[0]

        for id_p, cantidad, precio in items_a_vender:
            cursor.execute("""
                INSERT INTO Detalle_Ventas (id_venta, id_producto, cantidad, precio_unitario) 
                VALUES (?, ?, ?, ?)
            """, (id_venta, id_p, cantidad, precio))
            
            cursor.execute("""
                UPDATE Productos SET stock = stock - ? WHERE id_producto = ?
            """, (cantidad, id_p))

        conn.commit()
        session.pop('cart', None)  
        flash('¡Compra realizada con éxito! Muchas gracias.', 'success')
        return redirect(url_for('catalogo'))

    except Exception as e:
        conn.rollback()  
        flash(f'No se pudo completar la compra: {str(e)}', 'danger')
        return redirect(url_for('ver_carrito'))
    finally:
        cursor.close()
        conn.close()

# ===================================================
#   PANEL ADMINISTRADOR & AUTENTICACIÓN OPTIMIZADOS
# ===================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        
        conn = get_db_connection()
        if not conn:
            flash('Error de conexión: No se pudo conectar al servidor.', 'danger')
            return render_template('Administrador/login.html')
            
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id_usuario, u.nombre_completo, u.contrasena_hash, r.nombre_rol 
            FROM Usuarios u
            JOIN Roles r ON u.id_rol = r.id_role
            WHERE u.email = ?
        """, (email,))
        usuario = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Mensaje genérico para no dar pistas si el correo existe o no
        mensaje_error = 'Credenciales inválidas. Por favor verifique los datos.'
        
        if not usuario:
            flash(mensaje_error, 'danger')
            return render_template('Administrador/login.html')
            
        db_id, db_nombre, db_hash, db_rol = usuario
        
        # Se eliminó la validación en texto plano. Comparamos solo usando hashes seguros.
        if not check_password_hash(db_hash, password):
            flash(mensaje_error, 'danger')
            return render_template('Administrador/login.html')
            
        if db_rol.lower().strip() not in ['admin', 'administrador']:
            flash('Tu usuario no tiene permisos de Administrador.', 'danger')
            return render_template('Administrador/login.html')
            
        # Limpieza y regeneración de sesión (Mitiga la fijación de sesiones)
        session.clear()
        session['usuario_id'] = db_id
        session['rol'] = 'admin'
        session['nombre'] = db_nombre
        session['admin_name'] = db_nombre
        flash(f'¡Bienvenido, {db_nombre}!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('Administrador/login.html')

@app.route('/admin/dashboard')
def dashboard():
    if session.get('rol') != 'admin':
        flash('Por favor, iniciá sesión para acceder al panel.', 'warning')
        return redirect(url_for('login'))
    return render_template('Administrador/dashboard.html')

@app.route('/admin/logout')
def logout():
    session.clear()
    flash('Cerraste sesión correctamente.', 'info')
    return redirect(url_for('login'))

# HISTORIAL DE VENTAS DEL ADMINISTRADOR
@app.route('/admin/ventas')
def admin_ventas():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('dashboard'))

    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.id_venta, v.fecha_hora, v.total_venta, v.cliente_nombre, 
                p.nombre, d.cantidad, d.precio_unitario
        FROM Ventas v
        LEFT JOIN Detalle_Ventas d ON v.id_venta = d.id_venta
        LEFT JOIN Productos p ON d.id_producto = p.id_producto
        ORDER BY v.id_venta DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    ventas = {}
    for r in rows:
        id_v = r[0]
        if id_v not in ventas:
            ventas[id_v] = {
                'id_venta': r[0],
                'fecha': r[1],      
                'total': r[2],      
                'cliente': r[3],    
                'detalles': []
            }
        if r[4]:  
            ventas[id_v]['detalles'].append({
                'producto': r[4],
                'cantidad': r[5],
                'precio': r[6]
            })

    return render_template('Administrador/ventas.html', ventas=ventas)

# ===================================================
#   PRODUCTOS - ABM
# ===================================================

@app.route('/admin/productos', methods=['GET', 'POST'])
def admin_productos():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('Error de conexión a la base de datos', 'danger')
        return redirect(url_for('admin_productos'))
    
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'delete':
                pid = request.form.get('id_producto')
                cursor.execute("DELETE FROM Productos WHERE id_producto = ?", (pid,))
                flash('Producto eliminado', 'success')

            elif action in ['create', 'edit']:
                nombre = request.form.get('nombre')
                descripcion = request.form.get('descripcion')
                precio_compra = float(request.form.get('precio_compra') or 0)
                precio_venta = float(request.form.get('precio_venta') or 0)
                stock = int(request.form.get('stock') or 0)
                id_categoria = int(request.form.get('id_categoria'))
                imagen_url = request.form.get('imagen_url')

                if precio_compra < 0 or precio_venta < 0 or stock < 0:
                    raise ValueError("Los precios y el stock no pueden ser negativos.")

                if action == 'create':
                    cursor.execute("""
                        INSERT INTO Productos 
                        (nombre, descripcion, precio_compra, precio_venta, stock, id_categoria, imagen_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (nombre, descripcion, precio_compra, precio_venta, stock, id_categoria, imagen_url))
                    flash('Producto creado correctamente', 'success')
                    
                elif action == 'edit':
                    pid = int(request.form.get('id_producto'))
                    cursor.execute("""
                        UPDATE Productos SET nombre=?, descripcion=?, precio_compra=?, 
                        precio_venta=?, stock=?, id_categoria=?, imagen_url=?
                        WHERE id_producto=?
                    """, (nombre, descripcion, precio_compra, precio_venta, stock, id_categoria, imagen_url, pid))
                    flash('Producto actualizado correctamente', 'success')

            conn.commit()
        except Exception as e:
            conn.rollback()
            flash(f'Error al procesar producto: {str(e)}', 'danger')
        
        cursor.close()
        conn.close()
        return redirect(url_for('admin_productos'))

    cursor.execute("SELECT id_categoria, nombre_categoria FROM Categorias WHERE estado = 1 ORDER BY nombre_categoria")
    categorias = cursor.fetchall()

    cursor.execute("""
        SELECT p.id_producto, p.nombre, p.descripcion, p.precio_compra, p.precio_venta, 
            p.stock, c.nombre_categoria, p.id_categoria, p.imagen_url 
        FROM Productos p
        LEFT JOIN Categorias c ON p.id_categoria = c.id_categoria
        ORDER BY p.id_producto DESC
    """)
    productos = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('Administrador/producto.html', categorias=categorias, productos=productos)

# ===================================================
#   CATEGORÍAS - ABM
# ===================================================

@app.route('/admin/categorias', methods=['GET', 'POST'])
def admin_categories():
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn:
        flash('Error de conexión', 'danger')
        return redirect(url_for('admin_categories'))
    
    cursor = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        nombre = request.form.get('nombre_categoria')
        
        try:
            if action == 'delete':
                cid = request.form.get('id_categoria')
                cursor.execute("UPDATE Categorias SET estado = 0 WHERE id_categoria = ?", (cid,))
                flash('Categoría desactivada correctamente', 'success')

            elif nombre:
                if action == 'create':
                    cursor.execute("INSERT INTO Categorias (nombre_categoria) VALUES (?)", (nombre,))
                    flash('¡Categoría creada con éxito!', 'success')
                elif action == 'edit':
                    cid = request.form.get('id_categoria')
                    cursor.execute("UPDATE Categorias SET nombre_categoria = ? WHERE id_categoria = ?", 
                                    (nombre, cid))
                    flash('Categoría actualizada correctamente', 'success')
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            flash(f'Error al procesar categoría: {str(e)}', 'danger')

        cursor.close()
        conn.close()
        return redirect(url_for('admin_categories'))

    cursor.execute("SELECT id_categoria, nombre_categoria FROM Categorias WHERE estado = 1 ORDER BY nombre_categoria")
    categorias = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('Administrador/categorias.html', categorias=categorias)

if __name__ == '__main__':
    app.run(debug=True)