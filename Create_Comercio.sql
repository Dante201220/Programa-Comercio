USE [Gestion Comercio];
GO

-- 1. LIMPIEZA PROFUNDA: Borramos las tablas de detalles primero (ambas variantes) para liberar las claves foráneas
DROP TABLE IF EXISTS Detalle_Ventas;
DROP TABLE IF EXISTS DetalleVentas; 

-- Ahora que no hay detalles colgando, podemos borrar el resto de las tablas en orden
DROP TABLE IF EXISTS Ventas;
DROP TABLE IF EXISTS Productos;
DROP TABLE IF EXISTS Categorias;
DROP TABLE IF EXISTS Usuarios;
DROP TABLE IF EXISTS Roles;
GO

-- 2. TABLA DE ROLES
CREATE TABLE Roles (
    id_role INT IDENTITY(1,1) PRIMARY KEY,
    nombre_rol VARCHAR(50) NOT NULL UNIQUE
);
GO

INSERT INTO Roles (nombre_rol) VALUES ('admin'), ('cliente');
GO

-- 3. TABLA DE USUARIOS
CREATE TABLE Usuarios (
    id_usuario INT IDENTITY(1,1) PRIMARY KEY,
    nombre_completo VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL, 
    id_rol INT NOT NULL,
    fecha_creacion DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (id_rol) REFERENCES Roles(id_role)
);
GO

-- Insertamos tu usuario Administrador
INSERT INTO Usuarios (nombre_completo, email, contrasena_hash, id_rol)
VALUES ('Dante Dueño', 'admin@negocio.com', 'scrypt:32768:8:1$kYUOUeqhqaeoKt4Z$81c167615a697cc122eab3dee96fe904a7c0d143f2117d43e1c37b29e58f47b40840bb8f31c7649d35c43f11bb61a45397ad88591bf128391b766821c14b407a', 1);
GO

-- 4. TABLA DE CATEGORÍAS
CREATE TABLE Categorias (
    id_categoria INT IDENTITY(1,1) PRIMARY KEY,
    nombre_categoria VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(200),
    estado BIT DEFAULT 1, 
    fecha_creacion DATETIME DEFAULT GETDATE()
);
GO

-- 5. TABLA DE PRODUCTOS (Limpia, sin la restricción única errónea en la imagen)
CREATE TABLE Productos (
    id_producto INT IDENTITY(1,1) PRIMARY KEY,
    codigo_barra VARCHAR(50) UNIQUE NULL,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(MAX),
    precio_compra DECIMAL(12,2) NOT NULL CHECK (precio_compra >= 0), 
    precio_venta DECIMAL(12,2) NOT NULL CHECK (precio_venta >= 0),   
    stock INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    id_categoria INT NOT NULL,
    imagen_url VARCHAR(255) NULL,
    fecha_creacion DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (id_categoria) REFERENCES Categorias(id_categoria) ON DELETE NO ACTION
);
GO

-- 6. TABLA DE VENTAS (Cabecera adaptada con cliente_nombre para el Carrito)
CREATE TABLE Ventas (
    id_venta INT IDENTITY(1,1) PRIMARY KEY,
    fecha_hora DATETIME NOT NULL DEFAULT GETDATE(),
    total_venta DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (total_venta >= 0),
    id_cliente INT NULL,
    cliente_nombre VARCHAR(100) NULL, -- Esencial para guardar el nombre del input del carrito
    FOREIGN KEY (id_cliente) REFERENCES Usuarios(id_usuario) ON DELETE SET NULL
);
GO

-- 7. DETALLE DE VENTAS (Con subtotal autocalculado)
CREATE TABLE Detalle_Ventas (
    id_detalle_v INT IDENTITY(1,1) PRIMARY KEY,
    id_venta INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    precio_unitario DECIMAL(12,2) NOT NULL CHECK (precio_unitario >= 0),
    subtotal AS (cantidad * precio_unitario) PERSISTED, 
    FOREIGN KEY (id_venta) REFERENCES Ventas(id_venta) ON DELETE CASCADE,
    FOREIGN KEY (id_producto) REFERENCES Productos(id_producto)
);
GO

-- 8. ÍNDICES DE RENDIMIENTO
CREATE INDEX idx_productos_categoria ON Productos(id_categoria);
CREATE INDEX idx_productos_nombre ON Productos(nombre);
CREATE INDEX idx_ventas_fecha ON Ventas(fecha_hora);
CREATE INDEX idx_detalle_producto ON Detalle_Ventas(id_producto);
GO

-- 9. Borramos la restricción molesta usando el nombre exacto de tu error actual
ALTER TABLE Productos DROP CONSTRAINT UQ__Producto__685EAC7A6537AD24;
GO

-- 10. Creamos un índice único que ignora los valores vacíos (NULL)
CREATE UNIQUE NONCLUSTERED INDEX UQ_Productos_CodigoBarra_PermitirNulls
ON Productos(codigo_barra)
WHERE codigo_barra IS NOT NULL;
GO

USE [Gestion Comercio];
GO

-- 11. Buscamos y borramos dinámicamente la restricción UNIQUE vieja sin importar el nombre aleatorio que le dio SQL Server
DECLARE @sql NVARCHAR(MAX);
SELECT @sql = 'ALTER TABLE Categorias DROP CONSTRAINT ' + name
FROM sys.key_constraints
WHERE type = 'UQ' AND parent_object_id = OBJECT_ID('dbo.Categorias');

IF @sql IS NOT NULL
BEGIN
    EXEC sp_executesql @sql;
END
GO

-- 12. Creamos un índice único inteligente: solo exige nombres únicos para categorías ACTIVAS (estado = 1)
CREATE UNIQUE NONCLUSTERED INDEX UQ_Categorias_Nombre_Activo
ON Categorias(nombre_categoria)
WHERE estado = 1;
GO