"""
models.py - Modelos de base de datos del sistema POS
"""
from django.db import models
from django.utils import timezone


class Categoria(models.Model):
    """Categorías de productos."""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Modelo de producto para el inventario."""
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    sku = models.CharField(
        max_length=50, unique=True, verbose_name="Código / SKU",
        help_text="Código único del producto"
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Categoría"
    )
    precio_compra = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Precio de Compra"
    )
    precio_venta = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Precio de Venta"
    )
    stock = models.IntegerField(default=0, verbose_name="Stock Disponible")
    stock_minimo = models.IntegerField(
        default=5, verbose_name="Stock Mínimo",
        help_text="Alerta cuando el stock baje de este nivel"
    )
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.sku})"

    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia en porcentaje."""
        if self.precio_compra > 0:
            return round(
                ((self.precio_venta - self.precio_compra) / self.precio_compra) * 100, 2
            )
        return 0

    @property
    def ganancia_unitaria(self):
        """Ganancia por unidad vendida."""
        return self.precio_venta - self.precio_compra

    @property
    def stock_bajo(self):
        """Retorna True si el stock está por debajo del mínimo."""
        return self.stock <= self.stock_minimo

    @property
    def sin_stock(self):
        """Retorna True si no hay stock."""
        return self.stock <= 0


class Venta(models.Model):
    """Encabezado de la venta."""
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('otro', 'Otro'),
    ]

    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Venta")
    total_venta = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="Total Venta"
    )
    total_ganancia = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="Ganancia Total"
    )
    metodo_pago = models.CharField(
        max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo',
        verbose_name="Método de Pago"
    )
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']

    def __str__(self):
        return f"Venta #{self.pk} - {self.fecha.strftime('%d/%m/%Y %H:%M')} - ${self.total_venta}"

    def calcular_totales(self):
        """Recalcula total y ganancia a partir de los detalles."""
        detalles = self.detalles.all()
        self.total_venta = sum(d.subtotal for d in detalles)
        self.total_ganancia = sum(d.ganancia for d in detalles)
        self.save()


class DetalleVenta(models.Model):
    """Línea de detalle de una venta."""
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='detalles',
        verbose_name="Venta"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, verbose_name="Producto"
    )
    cantidad = models.IntegerField(verbose_name="Cantidad")
    precio_venta = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Precio de Venta"
    )
    precio_compra = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Precio de Compra"
    )
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Subtotal"
    )

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} @ ${self.precio_venta}"

    @property
    def ganancia(self):
        """Ganancia de esta línea."""
        return (self.precio_venta - self.precio_compra) * self.cantidad

    def save(self, *args, **kwargs):
        """Calcula el subtotal automáticamente antes de guardar."""
        self.subtotal = self.precio_venta * self.cantidad
        super().save(*args, **kwargs)
