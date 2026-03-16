# Cerámicas Artesanales — App Flask

## Instalación rápida

```bash
# 1. Instalar dependencias
pip install flask

# 2. Ejecutar la app
python app.py
```

Luego abre: **http://localhost:5000**

## Estructura de archivos

```
ceramicas/
├── app.py                  ← Servidor Flask + API + BD SQLite
├── ceramicas.db            ← Base de datos (se crea automáticamente)
├── README.md
└── templates/
    ├── base.html           ← Layout principal con navbar
    ├── dashboard.html      ← Resumen y estadísticas
    ├── inventario.html     ← CRUD de productos
    ├── facturacion.html    ← Generador de facturas
    └── reportes.html       ← Historial de facturas
```

## Funcionalidades

### Dashboard
- Total de ingresos (suma de facturas)
- Número de productos en inventario
- Facturas generadas
- Alerta de productos con stock ≤ 5
- Top 3 productos más vendidos

### Inventario
- Agregar, editar y eliminar productos
- Búsqueda en tiempo real
- Indicador de stock (rojo/amarillo/verde)
- Categorías: Alcancías, Materas, Decoración

### Facturación
- Selección de productos por categoría
- Descuento automático 5% para empresas
- Actualización de stock al generar factura
- Número de factura único por timestamp

### Reportes
- Historial completo de facturas
- Total general acumulado
- Diferenciación cliente/empresa

## Base de datos (SQLite)

Tablas:
- `productos` — inventario con stock y ventas
- `facturas` — cabecera de cada factura
- `factura_items` — detalle de productos por factura

Los datos de ejemplo se cargan automáticamente la primera vez.
