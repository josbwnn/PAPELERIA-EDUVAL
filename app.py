from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime  
import os
from models.models import db, Usuario, Categoria, Producto, Entradas, Salidas

#FLASK SE EJECUTA DENTRO DE APP
app = Flask(__name__)

#SECRET KEY
app.secret_key = "PAPELERIA_EDUVAL_2025"
app.config["EMPLOYEE_REGISTER_KEY"] = "EDUVAL2025"

#DECORADOR PARA GESTIONAR LOS ROLOES DE CADA USUARIO 
#Un decorador es una función que modifica o extiende el comportamiento de otra
#función sin cambiar su código interno.
#FUNCTOOLS : modulo de python con herramientas que sirve para trabajar con funciones y decoradores
#WRAPS: es un decorador que preserva la informacion original de una funcion cuando la envuelves en otra
from functools import wraps
def rol_requerido(*roles_permitidos):
    #este decorador restringira el acceso dependiendo del rol del usuario
    def decorador(func):
        @wraps(func)
        #*args: esto permite que una funcion reciba cualquier cantidad de argumento
        #**kwargs: permite que una funcion reciba cualquier cantidad de argumentos con nombre
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Debes iniciar sesion primero.", "error")
                return redirect(url_for("login"))
            if session["rol"] not in roles_permitidos:
                flash("No tienes permiso para acceder a esta funcion", "warning")
                return redirect(url_for("catalogo"))
            return func(*args, **kwargs)
        return wrapper
    return decorador

#RUTA PRINCIPAL
@app.route("/")
def home():
    # Si el usuario ya está logueado, redirigir al dashboard
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    
    # Si no está logueado, mostrar la página de inicio
    return render_template("index.html")

app.config["EMPLOYEE_REGISTER_KEY"] = "EDUVAL2025"
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///EDUVAL.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar la base de datos
db.init_app(app)

#RUTA REQUERIDA PARA EL CATALOGO PARA LOS CLIENTES
@app.route("/catalogo")
def catalogo():
    productos = Producto.query.filter(Producto.stock>0).all() 
    return render_template("catalogo.html" , productos = productos)



# flash("Operación exitosa", "success")    # Verde 
# flash("Algo salió mal", "error")         # Rojo 
# flash("Ten cuidado", "warning")          # Amarillo
# flash("Información general", "info")     # Azul 


#REGISTRO DE USUARIOS
#request.form.get xq flask no acepta tuplas en request.form
@app.route("/registro", methods= ["GET", "POST"])
def registro():
    if request.method =="POST":
        nombre_usuario = request.form["nombre_usuario"]
        contraseña = request.form["contraseña"]
        rol = request.form.get("rol", "empleado")
        clave_registro = request.form["clave_registro"]

        # Verificar clave de registro
        if clave_registro != app.config["EMPLOYEE_REGISTER_KEY"]:
            flash("Clave de registro incorrecta. Solo personal autorizado puede crear usuarios.", "error")
            return redirect(url_for("registro"))
         # Validar campos vacíos
        if not nombre_usuario or not contraseña:
            flash("Todos los campos son obligatorios.", "warning")
            return redirect(url_for("registro"))
        

        #VERIFICAR AL USUARIO
        usuario_existente = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()
        if usuario_existente:
            flash("El nombre de usuario ya existe. Por favor, elige otro.", "warning")
            return redirect(url_for("registro"))
        
        #CIFRADO DE CONTRASEÑA
        hashed_password = generate_password_hash(contraseña)

        #CREAR NUEVO USUARIO
        nuevo_usuario = Usuario(
            nombre_usuario= nombre_usuario,
            contraseña = hashed_password,
            rol = rol
        ) 
        
        #GUARDADO DENTRO DE LA BASE DE DATOS
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash("Registro terminado con exito. Por favor inicia sesion.", "success")
        return redirect(url_for("login"))
    return render_template("registro.html")


#PARA ACCEDER A LA PAGINA DEL LOGIN ES NECESARIO PONER EN EL URL ¨/LOGIN¨
#LOGIN DE USUARIOS 
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre_usuario = request.form["nombre_usuario"]
        password = request.form["contraseña"]

        # BUSCAR AL USUARIO
        usuario = Usuario.query.filter_by(nombre_usuario=nombre_usuario).first()

        # VERIFICAR CONTRASEÑA
        if usuario and check_password_hash(usuario.contraseña, password):
            session["user_id"] = usuario.id
            session["nombre_usuario"] = usuario.nombre_usuario
            session["rol"] = usuario.rol

            flash(f"Bienvenido {usuario.nombre_usuario}!", "success")
            # REDIRIGIR DIRECTAMENTE AL DASHBOARD
            return redirect(url_for("dashboard"))
        else:
            flash("Usuario o contraseña incorrectos.", "error")
            return redirect(url_for("login"))
    
    return render_template("login.html")

#GET	Pedir información (leer datos)	Ver una página, lista de productos, etc.
#POST	Enviar información al servidor (crear o modificar datos) Enviar un formulario, agregar un producto, iniciar sesión
#request.method para POST Y GET
#request.form para capturar datos de formularios

#RUTA PARA LOS PRODUCTOS 
#mostrar todos los productos del inventario
@app.route("/productos")
@rol_requerido("administrador", "empleado", "cajero")
def productos():
    # Obtener parámetro de ordenamiento
    orden = request.args.get('orden', 'categoria')
    
    # Ordenar productos según el parámetro
    if orden == 'nombre':
        productos = Producto.query.order_by(Producto.nombre).all()
    elif orden == 'stock':
        productos = Producto.query.order_by(Producto.stock.desc()).all()
    elif orden == 'precio':
        productos = Producto.query.order_by(Producto.precio.desc()).all()
    else:  # orden == 'categoria' o por defecto
        productos = Producto.query.join(Categoria).order_by(Categoria.nombre, Producto.nombre).all()
    
    return render_template("productos.html", productos=productos)

#agregar nuevos productos al inventario
@app.route("/agregar_producto", methods = ["GET" , "POST"])
@rol_requerido("administrador")
def agregar_producto():
    if request.method == "POST":
        nombre = request.form["nombre"]
        precio = float(request.form["precio"])
        stock = int(request.form ["stock"])
        stock_minimo = int(request.form ["stock_minimo"])
        categoria_id = int(request.form ["categoria_id"])
        imagen_url = request.form.get("imagen_url", "").strip() or None

        nuevo_producto = Producto(
            nombre = nombre,
            precio = precio,
            stock = stock,
            stock_minimo = stock_minimo,
            categoria_id = categoria_id,
            imagen_url = imagen_url
        )

        db.session.add(nuevo_producto)
        db.session.commit()
        flash(f"Producto {nombre} agregado correctamente", "success")
        return redirect(url_for("productos"))
    
    categorias = Categoria.query.all()
    return render_template("agregar_producto.html", categorias=categorias)

#editar productos existentes
#<...> = Indica que es un parámetro variable
#int: = El valor DEBE ser un número entero
#id = Nombre de la variable que recibirás en la función
@app.route("/editar_producto/<int:id>", methods =["GET" , "POST"])
@rol_requerido("administrador")
#BUSCA EL PRODUCTO POR SU ID
def editar_producto(id):
    # El _or_404 maneja el error automáticamente si no encuentra el producto
    producto = Producto.query.get_or_404(id)

    if request.method == "POST":
        producto.nombre = request.form["nombre"]
        producto.precio = float(request.form["precio"])
        producto.stock = int(request.form ["stock"])
        producto.stock_minimo = int(request.form ["stock_minimo"])
        producto.categoria_id = int(request.form ["categoria_id"])
        producto.imagen_url = request.form.get("imagen?url", "").strip() or None

        db.session.commit()
        flash("Producto actualizado correctamente", "success")
        return redirect(url_for("productos"))
    
    categorias = Categoria.query.all()
    return render_template("editar_producto.html", producto=producto, categorias=categorias)

#eliminar productos del inventario
@app.route("/eliminar_producto/<int:id>", methods=["POST"])
@rol_requerido("administrador")
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash("Producto eliminado correctamente", "success")
    return redirect(url_for("productos"))

#entradas y salidas de productos
@app.route("/entrada_producto/<int:id>", methods=["GET", "POST"])
@rol_requerido("administrador", "empleado")
def entrada_producto(id):
    producto = Producto.query.get_or_404(id)

    if request.method == "POST":
        cantidad = int(request.form["cantidad"])
        producto.stock += cantidad

        nueva_entrada = Entradas (
            producto_id = producto.id,
            cantidad = cantidad,
            usuario_id = session["user_id"]
        )
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

        nueva_salida = Salidas (
            producto_id = producto.id,
            cantidad = cantidad,
            usuario_id = session["user_id"]
        )
        db.session.add(nueva_salida)
        db.session.commit()
        flash(f"Salida registrada: -{cantidad} unidades de {producto.nombre}", "success") 
        return redirect(url_for("productos"))
    return render_template("salida_producto.html", producto=producto)


#CATEGORIAS DE LOS PRODUCTOS

@app.route("/categorias")
@rol_requerido("administrador")
def categorias():
    # Obtener parámetro de ordenamiento
    orden = request.args.get('orden', 'nombre')
    
    # Ordenar categorías según el parámetro
    if orden == 'id':
        categorias = Categoria.query.order_by(Categoria.id).all()
    else:  # orden == 'nombre' o por defecto
        categorias = Categoria.query.order_by(Categoria.nombre).all()
    
    return render_template("categorias.html", categorias=categorias)


#agregar categorias nuevas
@app.route ("/agregar_categoria", methods= ["GET", "POST"])
def agregar_categoria():
    if request.method == "POST":
        #.strip sirve para eliminar los espacios en blancos y otros caracteres
        nombre = request.form["nombre"].strip()
        if not nombre:
            flash("El nombre de la categoria no puede estar vacio", "warning")
            return redirect(url_for("agregar_categoria"))
        
        existente = Categoria.query.filter_by(nombre=nombre).first()
        if existente:
            flash("Ya hay una categoria existente con ese nombre" , "info")
            return redirect(url_for("categorias"))
        
        nueva = Categoria (nombre = nombre )
        db.session.add(nueva)
        db.session.commit()
        flash ("Categoria creada correctamente.", "success")
        return redirect(url_for("categorias"))
    return render_template("agregar_categoria.html")

#editar categorias existente
@rol_requerido("administrador")
@app.route ("/editar_categoria/<int:id>", methods=["GET", "POST"]) 
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)

    if request.method == "POST":
        nuevo_nombre = request.form["nombre"].strip()
        
        if not nuevo_nombre:
            flash("El nombre no puede estar vacio" , "warning")
            return redirect(url_for("editar_categoria", id=id))
        
        categoria.nombre = nuevo_nombre
        db.session.commit()
        flash("La categoria se actualizo correctamente.", "success")
        return redirect(url_for("categorias"))
    return render_template("editar_categoria.html", categoria=categoria)

#eliminar categorias
@app.route ("/eliminar_categoria/<int:id>", methods= ["POST"])
@rol_requerido("administrador")
def eliminar_categoria(id):
    categoria= Categoria.query.get_or_404(id)
    db.session.delete(categoria)
    db.session.commit()
    flash("Categoria eliminada correctamente")
    return redirect(url_for("categorias"))


#logout de usuarios
@app.route("/logout")
def logout():
    session.clear()
    flash("Sesion cerrada correctamente.", "info")
    return redirect(url_for("login"))    



#DASHBOARD PARA ADMIN
@app.route("/dashboard")
@rol_requerido("administrador")
def dashboard():

    total_productos = Producto.query.count()
    total_categorias = Categoria.query.count()
    total_usuarios = Usuario.query.count()
    productos_bajos = Producto.query.filter (Producto.stock < 5).all()

    return render_template("dashboard.html",
                           total_productos= total_productos,
                           total_categorias= total_categorias,
                           total_usuarios= total_usuarios,
                           productos_bajos= productos_bajos)
# RUTA PARA GESTION DE USUARIOS

# Ver todos los usuarios
@app.route("/usuarios")
@rol_requerido("administrador")
def usuarios():
    # Obtener parámetro de ordenamiento
    orden = request.args.get('orden', 'jerarquia')
    
    # Definir jerarquía de roles
    jerarquia_roles = {
        'administrador': 1,
        'empleado': 2,
        'cajero': 3
    }
    
    # Obtener usuarios según el ordenamiento
    if orden == 'jerarquia':
        # Ordenar por jerarquía
        usuarios = Usuario.query.all()
        usuarios = sorted(usuarios, key=lambda u: jerarquia_roles.get(u.rol, 999))
    elif orden == 'nombre':
        # Ordenar por nombre alfabéticamente
        usuarios = Usuario.query.order_by(Usuario.nombre_usuario).all()
    else:  # orden == 'id'
        # Ordenar por ID
        usuarios = Usuario.query.order_by(Usuario.id).all()
    
    return render_template("usuarios.html", usuarios=usuarios)


# Eliminar usuario
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


# Cambiar rol
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

#ejecucion de la app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Tablas creadas/verificadas")
    app.run(debug=True)
