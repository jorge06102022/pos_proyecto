"""
urls.py - Rutas de la aplicación POS
"""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Inventario
    path('inventario/', views.inventario, name='inventario'),
    path('inventario/nuevo/', views.producto_crear, name='producto_crear'),
    path('inventario/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('inventario/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('inventario/<int:pk>/', views.producto_detalle, name='producto_detalle'),

    # POS
    path('pos/', views.pos, name='pos'),
    path('pos/procesar/', views.procesar_venta, name='procesar_venta'),
    path('api/productos/', views.api_buscar_producto, name='api_productos'),

    # Ventas
    path('ventas/', views.historial_ventas, name='historial_ventas'),
    path('ventas/<int:pk>/', views.venta_detalle, name='venta_detalle'),

    # Reportes
    path('reportes/', views.reportes, name='reportes'),

    # APIs
    path('api/stock-bajo/', views.api_stock_bajo, name='api_stock_bajo'),
    path('reporte-diario/', views.reporte_diario_pdf, name='reporte_diario'),
    path("crear-admin/", views.crear_admin),
    path('logout/', views.auth_views.LogoutView.as_view(), name='logout'),
]
