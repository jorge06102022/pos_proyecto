"""
Management command: python manage.py cargar_datos_prueba
Carga datos iniciales de prueba en la base de datos.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import random
from datetime import timedelta

from pos_app.models import Categoria, Producto, Venta, DetalleVenta


class Command(BaseCommand):
    help = 'Carga datos de prueba iniciales para el sistema POS'

    def handle(self, *args, **options):
        self.stdout.write('Cargando datos de prueba...')

        # Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@pos.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('✓ Superusuario creado: admin / admin123'))

        # Categorías
        categorias_data = [
            ('Bebidas', 'Refrescos, jugos y agua'),
            ('Snacks', 'Papas, galletas y dulces'),
            ('Lácteos', 'Leche, queso y yogurt'),
            ('Panadería', 'Pan y productos de panadería'),
            ('Limpieza', 'Productos de limpieza del hogar'),
            ('Electrónica', 'Accesorios electrónicos'),
        ]
        categorias = {}
        for nombre, desc in categorias_data:
            cat, _ = Categoria.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc})
            categorias[nombre] = cat
        self.stdout.write(self.style.SUCCESS(f'✓ {len(categorias)} categorías creadas'))

        # Productos
        productos_data = [
            ('Coca-Cola 350ml', 'BEB-001', 'Bebidas', 1200, 2000, 50),
            ('Pepsi 350ml', 'BEB-002', 'Bebidas', 1100, 1800, 40),
            ('Agua Cristal 600ml', 'BEB-003', 'Bebidas', 500, 1000, 80),
            ('Jugo Hit Mango', 'BEB-004', 'Bebidas', 900, 1500, 35),
            ('Papas Margarita', 'SNK-001', 'Snacks', 1500, 2500, 60),
            ('Chitos', 'SNK-002', 'Snacks', 800, 1500, 45),
            ('Galletas Oreo', 'SNK-003', 'Snacks', 2000, 3200, 30),
            ('Chocolatina Jet', 'SNK-004', 'Snacks', 600, 1000, 100),
            ('Leche Alquería 1L', 'LAC-001', 'Lácteos', 2800, 3800, 25),
            ('Yogurt Alpina 200g', 'LAC-002', 'Lácteos', 1800, 2800, 20),
            ('Pan Tajado Bimbo', 'PAN-001', 'Panadería', 4500, 6500, 15),
            ('Mogolla', 'PAN-002', 'Panadería', 200, 500, 50),
            ('Jabón Protex', 'LIM-001', 'Limpieza', 2500, 4000, 30),
            ('Detergente Ariel 500g', 'LIM-002', 'Limpieza', 5500, 8000, 20),
            ('Audífonos Genéricos', 'ELE-001', 'Electrónica', 8000, 15000, 10),
            ('Cable USB-C', 'ELE-002', 'Electrónica', 3000, 8000, 15),
            ('Pilas AA x2', 'ELE-003', 'Electrónica', 2000, 4500, 40),
            ('Fósforos', 'LIM-003', 'Limpieza', 300, 700, 3),  # stock bajo para demo
            ('Mentas Halls', 'SNK-005', 'Snacks', 400, 800, 80),
            ('Red Bull 250ml', 'BEB-005', 'Bebidas', 3500, 6000, 25),
        ]

        for nombre, sku, cat_nombre, p_compra, p_venta, stock in productos_data:
            Producto.objects.get_or_create(
                sku=sku,
                defaults={
                    'nombre': nombre,
                    'categoria': categorias[cat_nombre],
                    'precio_compra': Decimal(str(p_compra)),
                    'precio_venta': Decimal(str(p_venta)),
                    'stock': stock,
                    'stock_minimo': 5,
                }
            )
        self.stdout.write(self.style.SUCCESS(f'✓ {len(productos_data)} productos creados'))

        # Ventas de prueba (últimos 30 días)
        productos_list = list(Producto.objects.filter(activo=True))
        ventas_creadas = 0

        for days_ago in range(30, 0, -1):
            num_ventas_dia = random.randint(3, 12)
            for _ in range(num_ventas_dia):
                fecha = timezone.now() - timedelta(days=days_ago) + timedelta(
                    hours=random.randint(8, 21),
                    minutes=random.randint(0, 59)
                )
                metodo = random.choice(['efectivo', 'efectivo', 'efectivo', 'tarjeta', 'transferencia'])

                venta = Venta.objects.create(
                    fecha=fecha,
                    metodo_pago=metodo,
                    total_venta=Decimal('0'),
                    total_ganancia=Decimal('0'),
                )

                productos_venta = random.sample(productos_list, random.randint(1, 4))
                total = Decimal('0')
                ganancia = Decimal('0')

                for prod in productos_venta:
                    cantidad = random.randint(1, 3)
                    detalle = DetalleVenta(
                        venta=venta,
                        producto=prod,
                        cantidad=cantidad,
                        precio_venta=prod.precio_venta,
                        precio_compra=prod.precio_compra,
                    )
                    detalle.save()
                    total += detalle.subtotal
                    ganancia += (prod.precio_venta - prod.precio_compra) * cantidad

                venta.total_venta = total
                venta.total_ganancia = ganancia
                venta.save()
                ventas_creadas += 1

        self.stdout.write(self.style.SUCCESS(f'✓ {ventas_creadas} ventas de prueba generadas'))
        self.stdout.write(self.style.SUCCESS('\n✅ Datos de prueba cargados exitosamente.'))
        self.stdout.write('   Usuario: admin | Contraseña: admin123')
