from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from models import db, Usuario, Categoria, Producto, Entradas, Salidas
from functools import wraps

# Inicializar Flask
app = Flask(__name__)
app.secret_key = "PAPELERIA_EDUVAL_2025"
app.config["EMPLOYEE_REGISTER_KEY"] = "EDUVAL2025"

# Configuración de base de datos
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///EDUVAL.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar SQLAlchemy
db.init_app(app)

# Decorador para roles (sin cambios)
def rol_requerido(*roles_permitidos):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Debes iniciar sesión primero.", "error")
                return redirect(url_for("login"))
            if session["rol"] not in roles_permitidos:
                flash("No tienes permiso para acceder a esta función", "warning")
                return redirect(url_for("catalogo"))
            return func(*args, **kwargs)
        return wrapper
    return decorador

# Rutas (sin cambios mayores, solo ajustes menores en manejo de errores si es necesario)

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/catalogo")
def catalogo():
    productos = Producto.query.filter(Producto.stock > 0).all()
    return render_template("catalogo.html", productos=productos)

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre_usuario = request.form["nombre_usuario"]
        contraseña = request.form["contraseña"]
        rol = request.form.get("rol", "empleado")
        clave_registro = request.form["clave_registro"]

        if clave_registro != app.config["EMPLOYEE_REGISTER_KEY"]:
            flash("Clave de registro incorrecta. Solo personal autorizado puede crear usuarios.", "error")
            return redirect(url_for("registro"))

        if not nombre_usuario or not contraseña:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for("registro"))

        usuario_existente = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
        if usuario_existente:
            flash("El nombre de usuario ya existe. Por favor, elige otro.", "warning")
            return redirect(url_for("registro"))

        hashed_password = generate_password_hash(contraseña)
        nuevo_usuario = Usuario(nombre_usuario=nombre_usuario, contraseña=hashed_password, rol=rol)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash("Registro terminado con éxito. Por favor inicia sesión.", "success")
        return redirect(url_for("login"))
    return render_template("registro.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre_usuario = request.form["nombre_usuario"]
        password = request.form["contraseña"]
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()

        if usuario and check_password_hash(usuario.contraseña, password):
            session["user_id"] = usuario.id
            session["nombre_usuario"] = usuario.nombre_usuario
            session["rol"] = usuario.rol
            flash(f"Bienvenido {usuario.nombre_usuario}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos.", "error")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/productos")
@rol_requerido("administrador", "empleado", "cajero")
def productos():
    orden = request.args.get('orden', 'categoria')
    if orden == 'nombre':
        productos = Producto.query.order_by(Producto.nombre).all()
    elif orden == 'stock':
        productos = Producto.query.order_by(Producto.stock.desc()).all()
    elif orden == 'precio':
        productos = Producto.query.order_by(Producto.precio.desc()).all()
    else:
        productos = Producto.query.join(Categoria).order_by(Categoria.nombre, Producto.nombre).all()
    return render_template("productos.html", productos=productos)

@app.route("/agregar_producto", methods=["GET", "POST"])
@rol_requerido("administrador")
def agregar_producto():
    if request.method == "POST":
        nombre = request.form["nombre"]
        precio = float(request.form["precio"])
        stock = int(request.form["stock"])
        stock_minimo = int(request.form["stock_minimo"])
        categoria_id = int(request.form["categoria_id"])
        imagen_url = request.form.get("imagen_url", "").strip() or None

        nuevo_producto = Producto(
            nombre=nombre, precio=precio, stock=stock,
            stock_minimo=stock_minimo, categoria_id=categoria_id,
            imagen_url=imagen_url
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        flash(f"Producto {nombre} agregado correctamente", "success")
        return redirect(url_for("productos"))

    categorias = Categoria.query.all()
    return render_template("agregar_producto.html", categorias=categorias)

@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
@rol_requerido("administrador")
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    if request.method == "POST":
        producto.nombre = request.form["nombre"]
        producto.precio = float(request.form["precio"])
        producto.stock = int(request.form["stock"])
        producto.stock_minimo = int(request.form["stock_minimo"])
        producto.categoria_id = int(request.form["categoria_id"])
        producto.imagen_url = request.form.get("imagen_url", "").strip() or None
        db.session.commit()
        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("productos"))
    categorias = Categoria.query.all()
    return render_template("editar_producto.html", producto=producto, categorias=categorias)

@app.route("/eliminar_producto/<int:id>", methods=["POST"])
@rol_requerido("administrador")
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash("Producto eliminado correctamente", "success")
    return redirect(url_for("productos"))

@app.route("/entrada_producto/<int:id>", methods=["GET", "POST"])
@rol_requerido("administrador", "empleado")
def entrada_producto(id):
    producto = Producto.query.get_or_404(id)
    if request.method == "POST":
        cantidad = int(request.form["cantidad"])
        producto.stock += cantidad
        nueva_entrada = Entradas(producto_id=producto.id, cantidad=cantidad, usuario_id=session["user_id"])
        db.session.add(nueva_entrada)
        db.session.commit()
        flash(f"Entrada registrada: +{cantidad} unidades de {producto.nombre}", "success")
        return redirect(url_for("productos"))
    return render_template("entrada_producto.html", producto=producto)

@app.route("/salida_producto/<int:id>", methods=["GET", "POST"])
@rol_requerido("administrador", "cajero")
def salida_producto(id):
    producto = Producto.query.get_or_404(id)
    if request.method == "POST":
        cantidad = int(request.form["cantidad"])
        if cantidad > producto.stock:
            flash("No hay suficiente stock para concretar la salida.", "error")
            return redirect(url_for("salida_producto", id=producto.id))
        producto.stock -= cantidad
        nueva_salida = Salidas(producto_id=producto.id, cantidad=cantidad, usuario_id=session["user_id"])
        db.session.add(nueva_salida)
        db.session.commit()
        flash(f"Salida registrada: -{cantidad} unidades de {producto.nombre}", "success")
        return redirect(url_for("productos"))
    return render_template("salida_producto.html", producto=producto)

@app.route("/categorias")
@rol_requerido("administrador")
def categorias():
    orden = request.args.get('orden', 'nombre')
    if orden == 'id':
        categorias = Categoria.query.order_by(Categoria.id).all()
    else:
        categorias = Categoria.query.order_by(Categoria.nombre).all()
    return render_template("categorias.html", categorias=categorias)

@app.route("/agregar_categoria", methods=["GET", "POST"])
@rol_requerido("administrador")
def agregar_categoria():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        if not nombre:
            flash("El nombre de la categoría no puede estar vacío", "warning")
            return redirect(url_for("agregar_categoria"))
        existente = Categoria.query.filter_by(nombre=nombre).first()
        if existente:
            flash("Ya hay una categoría existente con ese nombre", "info")
            return redirect(url_for("categorias"))
        nueva = Categoria(nombre=nombre)
        db.session.add(nueva)
        db.session.commit()
        flash("Categoría creada correctamente.", "success")
        return redirect(url_for("categorias"))
    return render_template("agregar_categoria.html")

@app.route("/editar_categoria/<int:id>", methods=["GET", "POST"])
@rol_requerido("administrador")
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    if request.method == "POST":
        nuevo_nombre = request.form["nombre"].strip()
        if not nuevo_nombre:
            flash("El nombre no puede estar vacío", "warning")
            return redirect(url_for("editar_categoria", id=id))
        categoria.nombre = nuevo_nombre
        db.session.commit()
        flash("La categoría se actualizó correctamente.", "success")
        return redirect(url_for("categorias"))
    return render_template("editar_categoria.html", categoria=categoria)

@app.route("/eliminar_categoria/<int:id>", methods=["POST"])
@rol_requerido("administrador")
def eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    db.session.delete(categoria)
    db.session.commit()
    flash("Categoría eliminada correctamente", "success")
    return redirect(url_for("categorias"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@rol_requerido("administrador")
def dashboard():
    total_productos = Producto.query.count()
    total_categorias = Categoria.query.count()
    total_usuarios = Usuario.query.count()
    productos_bajos = Producto.query.filter(Producto.stock < 5).all()
    return render_template("dashboard.html",
                           total_productos=total_productos,
                           total_categorias=total_categorias,
                           total_usuarios=total_usuarios,
                           productos_bajos=productos_bajos)

@app.route("/usuarios")
@rol_requerido("administrador")
def usuarios():
    orden = request.args.get('orden', 'jerarquia')
    jerarquia_roles = {'administrador': 1, 'empleado': 2, 'cajero': 3}
    if orden == 'jerarquia':
        usuarios = sorted(Usuario.query.all(), key=lambda u: jerarquia_roles.get(u.rol, 999))
    elif orden == 'nombre':
        usuarios = Usuario.query.order_by(Usuario.nombre_usuario).all()
    else:
        usuarios = Usuario.query.order_by(Usuario.id).all()
    return render_template("usuarios.html", usuarios=usuarios)

@app.route("/eliminar_usuario/<int:id>", methods=["POST"])
@rol_requerido("administrador")
def eliminar_usuario(id):
    if id == session["user_id"]:
        flash("No puedes eliminar tu propio usuario", "error")
        return redirect(url_for("usuarios"))
    usuario = Usuario.query.get_or_404(id)
    db.session.delete(usuario)
    db.session.commit()
    flash("Usuario eliminado correctamente", "success")
    return redirect(url_for("usuarios"))

@app.route("/cambiar_rol/<int:id>", methods=["POST"])
@rol_requerido("administrador")
def cambiar_rol(id):
    usuario = Usuario.query.get_or_404(id)
    nuevo_rol = request.form["rol"]
    if nuevo_rol not in ["administrador", "empleado", "cajero"]:
        flash("Rol no válido", "error")
        return redirect(url_for("usuarios"))
    if usuario.id == session["user_id"]:
        flash("No puedes cambiar tu propio rol", "warning")
        return redirect(url_for("usuarios"))
    usuario.rol = nuevo_rol
    db.session.commit()
    flash("Rol actualizado correctamente", "success")
    return redirect(url_for("usuarios"))

# CORRECCIÓN: Crear tablas y seed de datos al iniciar la app (fuera del if __name__)
with app.app_context():
    db.create_all()
    print("Tablas creadas/verificadas en la base de datos.")
    
    # Seed básico: Agregar datos iniciales si no existen (para evitar errores vacíos)
    if not Categoria.query.first():
        db.session.add(Categoria(nombre="Ejemplo"))
        db.session.commit()
        print("Categoría de ejemplo agregada.")
    
    if not Producto.query.first():
        categoria_ejemplo = Categoria.query.first()
        db.session.add(Producto(
            nombre="Producto Ejemplo", precio=10.0, stock=5, stock_minimo=1,
            categoria_id=categoria_ejemplo.id, imagen_url=None
        ))
        db.session.commit()
        print("Producto de ejemplo agregado.")

# Ejecutar app (con puerto dinámico para compatibilidad)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Puerto dinámico para Render/desarrollo
    app.run(host='0.0.0.0', port=port, debug=True)
