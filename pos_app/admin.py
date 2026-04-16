"""
admin.py - Configuración del panel de administración de Django
"""
from django.contrib import admin
from .models import Producto, Categoria, Venta, DetalleVenta


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion', 'fecha_creacion']
    search_fields = ['nombre']


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ['subtotal', 'ganancia']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sku', 'categoria', 'precio_compra', 'precio_venta', 'stock', 'activo']
    list_filter = ['activo', 'categoria']
    search_fields = ['nombre', 'sku']
    list_editable = ['stock', 'activo']


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['pk', 'fecha', 'total_venta', 'total_ganancia', 'metodo_pago']
    list_filter = ['metodo_pago', 'fecha']
    inlines = [DetalleVentaInline]
    readonly_fields = ['total_venta', 'total_ganancia']


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ['venta', 'producto', 'cantidad', 'precio_venta', 'subtotal']
