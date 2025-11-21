from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Crear la instancia de SQLAlchemy
db = SQLAlchemy()

#USURARIOS DEL SISTEMA
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default="empleado")

#CATEGORIAS DE PRODUCTOS
class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

#PRODUCTOS
class Producto(db.Model):
    __tablename__ = "productos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=5)
    #FOREIGN KEY A CATEGORIAS
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    categoria = db.relationship("Categoria", backref="Productos")
    imagen_url = db.Column(db.String(500), nullable=True)

class Entradas(db.Model):
    __tablename__ = "entradas"
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    #FK A USUARIO
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    producto = db.relationship("Producto", backref="Entradas")
    usuario = db.relationship("Usuario", backref="Entradas")

class Salidas(db.Model):
    __tablename__ = "salidas"
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    #FK A USUARIO
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    producto = db.relationship("Producto", backref="Salidas")
    usuario = db.relationship("Usuario", backref="Salidas")

