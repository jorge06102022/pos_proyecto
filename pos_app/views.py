"""
views.py - Vistas del sistema POS
"""
import json
from decimal import Decimal
from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator

from .models import Producto, Categoria, Venta, DetalleVenta
from .forms import ProductoForm, CategoriaForm


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@login_required
def dashboard(request):
    """Vista principal del dashboard con estadísticas."""
    from datetime import datetime, timedelta
    from decimal import Decimal
    from django.db.models import Sum, F
    from django.utils import timezone
    import json

    from .models import Venta, Producto, DetalleVenta, Egreso

    # 🔥 FECHA ACTUAL CON ZONA HORARIA
    now = timezone.localtime()
    hoy = now.date()

    # 🔥 RANGOS CORRECTOS CON TIMEZONE
    inicio_dia = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
    fin_dia = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))

    inicio_mes = hoy.replace(day=1)
    inicio_mes_dt = timezone.make_aware(datetime.combine(inicio_mes, datetime.min.time()))
    fin_hoy_dt = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))

    # ───────────── VENTAS HOY ─────────────
    ventas_hoy = Venta.objects.filter(
        fecha__gte=inicio_dia,
        fecha__lte=fin_dia
    )

    total_hoy = ventas_hoy.aggregate(t=Sum('total_venta'))['t'] or Decimal('0')
    ganancia_hoy = ventas_hoy.aggregate(g=Sum('total_ganancia'))['g'] or Decimal('0')
    num_ventas_hoy = ventas_hoy.count()

    # ───────────── EGRESOS HOY ─────────────
    egresos_hoy_qs = Egreso.objects.filter(
        fecha__gte=inicio_dia,
        fecha__lte=fin_dia
    )

    egresos_hoy = egresos_hoy_qs.aggregate(t=Sum('monto'))['t'] or Decimal('0')

    # ✅ UTILIDAD REAL HOY
    utilidad_real_hoy = total_hoy - egresos_hoy

    # ───────────── VENTAS MES ─────────────
    ventas_mes = Venta.objects.filter(
        fecha__gte=inicio_mes_dt,
        fecha__lte=fin_hoy_dt
    )

    total_mes = ventas_mes.aggregate(t=Sum('total_venta'))['t'] or Decimal('0')
    ganancia_mes = ventas_mes.aggregate(g=Sum('total_ganancia'))['g'] or Decimal('0')

    # ───────────── EGRESOS MES ─────────────
    egresos_mes_qs = Egreso.objects.filter(
        fecha__gte=inicio_mes_dt,
        fecha__lte=fin_hoy_dt
    )

    egresos_mes = egresos_mes_qs.aggregate(t=Sum('monto'))['t'] or Decimal('0')

    # ✅ UTILIDAD REAL MES
    utilidad_real_mes = total_mes - egresos_mes

    # ───────────── INVENTARIO ─────────────
    total_productos = Producto.objects.filter(activo=True).count()

    productos_stock_bajo = Producto.objects.filter(
        activo=True,
        stock__lte=F('stock_minimo')
    ).count()

    productos_sin_stock = Producto.objects.filter(
        activo=True,
        stock=0
    ).count()

    # ───────────── ÚLTIMAS VENTAS ─────────────
    ultimas_ventas = Venta.objects.prefetch_related('detalles__producto').order_by('-fecha')[:5]

    # ───────────── GRÁFICO 7 DÍAS ─────────────
    labels_7dias = []
    data_ventas_7dias = []
    data_ganancias_7dias = []
    data_egresos_7dias = []

    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)

        inicio_d = timezone.make_aware(datetime.combine(dia, datetime.min.time()))
        fin_d = timezone.make_aware(datetime.combine(dia, datetime.max.time()))

        v = Venta.objects.filter(
            fecha__gte=inicio_d,
            fecha__lte=fin_d
        )

        e = Egreso.objects.filter(
            fecha__gte=inicio_d,
            fecha__lte=fin_d
        )

        labels_7dias.append(dia.strftime('%d/%m'))

        data_ventas_7dias.append(float(v.aggregate(t=Sum('total_venta'))['t'] or 0))
        data_ganancias_7dias.append(float(v.aggregate(g=Sum('total_ganancia'))['g'] or 0))
        data_egresos_7dias.append(float(e.aggregate(t=Sum('monto'))['t'] or 0))

    # ───────────── TOP PRODUCTOS ─────────────
    top_productos = (
        DetalleVenta.objects
        .filter(
            venta__fecha__gte=inicio_mes_dt,
            venta__fecha__lte=fin_hoy_dt
        )
        .values('producto__nombre')
        .annotate(
            total_qty=Sum('cantidad'),
            total_ingresos=Sum('subtotal')
        )
        .order_by('-total_qty')[:5]
    )

    # ───────────── CONTEXT ─────────────
    context = {
        'total_hoy': total_hoy,
        'ganancia_hoy': ganancia_hoy,
        'num_ventas_hoy': num_ventas_hoy,

        'egresos_hoy': egresos_hoy,
        'utilidad_real_hoy': utilidad_real_hoy,

        'total_mes': total_mes,
        'ganancia_mes': ganancia_mes,

        'egresos_mes': egresos_mes,
        'utilidad_real_mes': utilidad_real_mes,

        'total_productos': total_productos,
        'productos_stock_bajo': productos_stock_bajo,
        'productos_sin_stock': productos_sin_stock,

        'ultimas_ventas': ultimas_ventas,

        'labels_7dias': json.dumps(labels_7dias),
        'data_ventas_7dias': json.dumps(data_ventas_7dias),
        'data_ganancias_7dias': json.dumps(data_ganancias_7dias),
        'data_egresos_7dias': json.dumps(data_egresos_7dias),

        'top_productos': list(top_productos),
    }

    return render(request, 'dashboard/dashboard.html', context)
# ─────────────────────────────────────────────
# INVENTARIO / PRODUCTOS
# ─────────────────────────────────────────────

@login_required
def inventario(request):
    """Lista de productos con filtros y búsqueda."""
    productos = Producto.objects.select_related('categoria').filter(activo=True)

    # Búsqueda
    q = request.GET.get('q', '')
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(sku__icontains=q))

    # Filtro categoría
    cat_id = request.GET.get('categoria', '')
    if cat_id:
        productos = productos.filter(categoria_id=cat_id)

    # Filtro stock
    filtro_stock = request.GET.get('stock', '')
    if filtro_stock == 'bajo':
        productos = productos.filter(stock__lte=F('stock_minimo'), stock__gt=0)
    elif filtro_stock == 'sin':
        productos = productos.filter(stock=0)

    paginator = Paginator(productos, 20)
    page = request.GET.get('page', 1)
    productos_paginados = paginator.get_page(page)

    categorias = Categoria.objects.all()

    context = {
        'productos': productos_paginados,
        'categorias': categorias,
        'q': q,
        'cat_id': cat_id,
        'filtro_stock': filtro_stock,
        'total_stock_bajo': Producto.objects.filter(activo=True, stock__lte=F('stock_minimo')).count(),
    }
    return render(request, 'inventory/inventario.html', context)


@login_required
def producto_crear(request):
    """Crear un nuevo producto."""
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            producto = form.save()
            messages.success(request, f'Producto "{producto.nombre}" creado exitosamente.')
            return redirect('inventario')
    else:
        form = ProductoForm()
    return render(request, 'inventory/producto_form.html', {'form': form, 'titulo': 'Nuevo Producto'})


@login_required
def producto_editar(request, pk):
    """Editar un producto existente."""
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{producto.nombre}" actualizado.')
            return redirect('inventario')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'inventory/producto_form.html', {
        'form': form, 'producto': producto, 'titulo': 'Editar Producto'
    })


@login_required
def producto_eliminar(request, pk):
    """Desactivar (soft delete) un producto."""
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.activo = False
        producto.save()
        messages.success(request, f'Producto "{producto.nombre}" eliminado.')
        return redirect('inventario')
    return render(request, 'inventory/producto_confirmar_eliminar.html', {'producto': producto})


@login_required
def producto_detalle(request, pk):
    """Detalle de un producto."""
    producto = get_object_or_404(Producto, pk=pk)
    # Historial de ventas del producto (últimas 10)
    historial = DetalleVenta.objects.filter(
        producto=producto
    ).select_related('venta').order_by('-venta__fecha')[:10]
    return render(request, 'inventory/producto_detalle.html', {
        'producto': producto, 'historial': historial
    })


# ─────────────────────────────────────────────
# POS - PUNTO DE VENTA
# ─────────────────────────────────────────────

@login_required
def pos(request):
    """Vista del punto de venta (carrito)."""
    categorias = Categoria.objects.all()
    productos = Producto.objects.filter(activo=True, stock__gt=0).select_related('categoria')
    return render(request, 'sales/pos.html', {
        'categorias': categorias,
        'productos': productos,
    })


@login_required
def api_buscar_producto(request):
    """API: busca productos para el POS."""
    q = request.GET.get('q', '')
    cat = request.GET.get('cat', '')
    productos = Producto.objects.filter(activo=True, stock__gt=0)
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(sku__icontains=q))
    if cat:
        productos = productos.filter(categoria_id=cat)
    data = [
        {
            'id': p.pk,
            'nombre': p.nombre,
            'sku': p.sku,
            'precio_venta': float(p.precio_venta),
            'precio_compra': float(p.precio_compra),
            'stock': p.stock,
            'categoria': p.categoria.nombre if p.categoria else 'Sin categoría',
        }
        for p in productos[:50]
    ]
    return JsonResponse({'productos': data})


@login_required
@require_POST
def procesar_venta(request):
    """Procesa y guarda una venta desde el POS."""
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
        metodo_pago = data.get('metodo_pago', 'efectivo')

        if not items:
            return JsonResponse({'success': False, 'error': 'El carrito está vacío.'})

        # Validar stock antes de procesar
        for item in items:
            producto = get_object_or_404(Producto, pk=item['producto_id'])
            if producto.stock < item['cantidad']:
                return JsonResponse({
                    'success': False,
                    'error': f'Stock insuficiente para "{producto.nombre}". Disponible: {producto.stock}'
                })

        # Crear la venta
        venta = Venta.objects.create(
            metodo_pago=metodo_pago,
            total_venta=Decimal('0'),
            total_ganancia=Decimal('0'),
        )

        total_venta = Decimal('0')
        total_ganancia = Decimal('0')

        for item in items:
            producto = Producto.objects.get(pk=item['producto_id'])
            cantidad = int(item['cantidad'])
            precio_venta = Decimal(str(item['precio_venta']))
            precio_compra = producto.precio_compra

            detalle = DetalleVenta(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_venta=precio_venta,
                precio_compra=precio_compra,
            )
            detalle.save()  # subtotal se calcula en save()

            ganancia_linea = (precio_venta - precio_compra) * cantidad
            total_venta += detalle.subtotal
            total_ganancia += ganancia_linea

            # Descontar stock
            producto.stock -= cantidad
            producto.save()

        venta.total_venta = total_venta
        venta.total_ganancia = total_ganancia
        venta.save()

        return JsonResponse({
            'success': True,
            'venta_id': venta.pk,
            'total': float(total_venta),
            'ganancia': float(total_ganancia),
            'mensaje': f'Venta #{venta.pk} procesada exitosamente.'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ─────────────────────────────────────────────
# HISTORIAL DE VENTAS
# ─────────────────────────────────────────────

@login_required
def historial_ventas(request):
    """Historial de todas las ventas."""
    ventas = Venta.objects.prefetch_related('detalles__producto')

    # Filtros de fecha
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')

    if fecha_desde:
        ventas = ventas.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        ventas = ventas.filter(fecha__date__lte=fecha_hasta)

    # Totales del filtro
    totales = ventas.aggregate(
        total=Sum('total_venta'),
        ganancia=Sum('total_ganancia'),
        num=Count('id')
    )

    paginator = Paginator(ventas, 20)
    page = request.GET.get('page', 1)
    ventas_paginadas = paginator.get_page(page)

    return render(request, 'sales/historial.html', {
        'ventas': ventas_paginadas,
        'totales': totales,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@login_required
def venta_detalle(request, pk):
    """Detalle de una venta específica."""
    venta = get_object_or_404(Venta, pk=pk)
    detalles = venta.detalles.select_related('producto').all()
    return render(request, 'sales/venta_detalle.html', {
        'venta': venta,
        'detalles': detalles,
    })


# ─────────────────────────────────────────────
# REPORTES Y ESTADÍSTICAS
# ─────────────────────────────────────────────

@login_required
def reportes(request):
    """Panel de reportes y estadísticas avanzadas."""
    hoy = timezone.now().date()

    # Parámetros de período
    periodo = request.GET.get('periodo', 'mes')

    if periodo == 'hoy':
        fecha_inicio = hoy
        fecha_fin = hoy
    elif periodo == 'semana':
        fecha_inicio = hoy - timedelta(days=6)
        fecha_fin = hoy
    elif periodo == 'mes':
        fecha_inicio = hoy.replace(day=1)
        fecha_fin = hoy
    elif periodo == 'año':
        fecha_inicio = hoy.replace(month=1, day=1)
        fecha_fin = hoy
    else:
        # Fechas personalizadas
        fecha_inicio_str = request.GET.get('fecha_inicio', '')
        fecha_fin_str = request.GET.get('fecha_fin', '')
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy

    # 🔥 CORRECCIÓN CLAVE (datetime en vez de date)
    inicio_datetime = datetime.combine(fecha_inicio, datetime.min.time())
    fin_datetime = datetime.combine(fecha_fin, datetime.max.time())

    ventas_periodo = Venta.objects.filter(
        fecha__gte=inicio_datetime,
        fecha__lte=fin_datetime
    )

    # Resumen del período
    resumen = ventas_periodo.aggregate(
        total_ventas=Sum('total_venta'),
        total_ganancias=Sum('total_ganancia'),
        num_ventas=Count('id'),
    )
    resumen['total_ventas'] = resumen['total_ventas'] or Decimal('0')
    resumen['total_ganancias'] = resumen['total_ganancias'] or Decimal('0')
    resumen['num_ventas'] = resumen['num_ventas'] or 0

    ticket_promedio = (
        resumen['total_ventas'] / resumen['num_ventas']
        if resumen['num_ventas'] > 0 else Decimal('0')
    )

    # Ventas por día
    ventas_por_dia = (
        ventas_periodo
        .annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(
            total=Sum('total_venta'),
            ganancia=Sum('total_ganancia')
        )
        .order_by('dia')
    )

    labels_dias = [
        v['dia'].strftime('%d/%m') if v['dia'] else ''
        for v in ventas_por_dia
    ]
    data_ventas_dia = [float(v['total']) for v in ventas_por_dia]
    data_ganancias_dia = [float(v['ganancia']) for v in ventas_por_dia]

    # Ventas por método de pago
    por_metodo = (
        ventas_periodo
        .values('metodo_pago')
        .annotate(
            total=Sum('total_venta'),
            num=Count('id')
        )
        .order_by('-total')
    )

    # Top productos
    top_productos = (
        DetalleVenta.objects
        .filter(
            venta__fecha__gte=inicio_datetime,
            venta__fecha__lte=fin_datetime
        )
        .values('producto__nombre', 'producto__sku')
        .annotate(
            qty=Sum('cantidad'),
            ingresos=Sum('subtotal'),
            ganancia=Sum(F('subtotal') - F('precio_compra') * F('cantidad'))
        )
        .order_by('-qty')[:10]
    )

    # Stock bajo
    stock_bajo = Producto.objects.filter(
        activo=True,
        stock__lte=F('stock_minimo')
    ).order_by('stock')

    # Ventas mensuales
    hace_12_meses = hoy - timedelta(days=365)

    ventas_mensuales = (
        Venta.objects
        .filter(fecha__date__gte=hace_12_meses)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(
            total=Sum('total_venta'),
            ganancia=Sum('total_ganancia')
        )
        .order_by('mes')
    )

    labels_meses = [v['mes'].strftime('%b %Y') for v in ventas_mensuales]
    data_ventas_mes = [float(v['total']) for v in ventas_mensuales]
    data_ganancias_mes = [float(v['ganancia']) for v in ventas_mensuales]

    context = {
        'periodo': periodo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'resumen': resumen,
        'ticket_promedio': ticket_promedio,
        'labels_dias': json.dumps(labels_dias),
        'data_ventas_dia': json.dumps(data_ventas_dia),
        'data_ganancias_dia': json.dumps(data_ganancias_dia),
        'por_metodo': list(por_metodo),
        'top_productos': list(top_productos),
        'stock_bajo': stock_bajo,
        'labels_meses': json.dumps(labels_meses),
        'data_ventas_mes': json.dumps(data_ventas_mes),
        'data_ganancias_mes': json.dumps(data_ganancias_mes),
    }

    return render(request, 'reports/reportes.html', context)

# ─────────────────────────────────────────────
# API STOCK (para alertas en tiempo real)
# ─────────────────────────────────────────────

@login_required
def api_stock_bajo(request):
    """API: devuelve productos con stock bajo."""
    productos = Producto.objects.filter(
        activo=True, stock__lte=F('stock_minimo')
    ).values('id', 'nombre', 'sku', 'stock', 'stock_minimo')
    return JsonResponse({'productos': list(productos)})

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
import io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate


# ─────────────────────────────────────────────
#  PALETA DE COLORES
# ─────────────────────────────────────────────
PURPLE       = colors.HexColor("#6c63ff")
PURPLE_DARK  = colors.HexColor("#4b44cc")
PURPLE_LIGHT = colors.HexColor("#ede9ff")
GREEN        = colors.HexColor("#22c55e")
GREEN_LIGHT  = colors.HexColor("#dcfce7")
GRAY_DARK    = colors.HexColor("#1e1e2e")
GRAY_MID     = colors.HexColor("#6b7280")
GRAY_LIGHT   = colors.HexColor("#f3f4f6")
WHITE        = colors.white
ROW_ALT      = colors.HexColor("#f8f7ff")


# ─────────────────────────────────────────────
#  CANVAS CON ENCABEZADO Y FOOTER PERSONALIZADOS
# ─────────────────────────────────────────────
def draw_header_footer(canvas_obj, doc, hoy, page_num, total_pages):
    canvas_obj.saveState()
    page_w, page_h = A4

    # ── Banda superior ──────────────────────────────────────────
    canvas_obj.setFillColor(PURPLE)
    canvas_obj.rect(0, page_h - 60, page_w, 60, fill=1, stroke=0)

    # Línea decorativa bajo la banda
    canvas_obj.setFillColor(PURPLE_DARK)
    canvas_obj.rect(0, page_h - 64, page_w, 4, fill=1, stroke=0)

    # Nombre del negocio
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont("Helvetica-Bold", 20)
    canvas_obj.drawString(30, page_h - 38, "POS PRO")

    # Subtítulo a la derecha
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.setFillColor(colors.HexColor("#d0cdff"))
    canvas_obj.drawRightString(page_w - 30, page_h - 28, "Sistema de Punto de Venta")
    canvas_obj.drawRightString(page_w - 30, page_h - 42, f"Generado: {hoy.strftime('%d/%m/%Y')}")

    # ── Banda inferior ──────────────────────────────────────────
    canvas_obj.setFillColor(GRAY_LIGHT)
    canvas_obj.rect(0, 0, page_w, 40, fill=1, stroke=0)

    canvas_obj.setFillColor(PURPLE)
    canvas_obj.rect(0, 40, page_w, 2, fill=1, stroke=0)

    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(GRAY_MID)
    canvas_obj.drawString(30, 15, "Reporte generado automáticamente por POS PRO  •  Documento confidencial")
    canvas_obj.drawRightString(
        page_w - 30, 15,
        f"Página {page_num} de {total_pages}"
    )

    canvas_obj.restoreState()


# ─────────────────────────────────────────────
#  VISTA PRINCIPAL
# ─────────────────────────────────────────────
@login_required
def reporte_diario_pdf(request):
    hoy = timezone.now().date()
    inicio = datetime.combine(hoy, datetime.min.time())
    fin    = datetime.combine(hoy, datetime.max.time())

    ventas = Venta.objects.filter(fecha__gte=inicio, fecha__lte=fin).order_by("-fecha")

    # ✅ NUEVO: EGRESOS
    egresos = Egreso.objects.filter(fecha__gte=inicio, fecha__lte=fin).order_by("-fecha")

    total     = ventas.aggregate(t=Sum("total_venta"))["t"] or 0
    ganancia  = ventas.aggregate(g=Sum("total_ganancia"))["g"] or 0
    cantidad  = ventas.count()
    promedio  = (total / cantidad) if cantidad else 0

    # ✅ NUEVO
    total_egresos = egresos.aggregate(t=Sum("monto"))["t"] or 0

    # ✅ UTILIDAD REAL
    utilidad_real = total - total_egresos

    # ── Response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="reporte_{hoy}.pdf"'

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    # ── Estilos (NO TOCADOS)
    style_section_title = ParagraphStyle(
        "SectionTitle", fontName="Helvetica-Bold", fontSize=11,
        textColor=PURPLE_DARK, spaceAfter=8, spaceBefore=4,
    )

    style_label = ParagraphStyle(
        "Label", fontName="Helvetica", fontSize=8,
        textColor=GRAY_MID, spaceAfter=2,
    )

    style_value_big = ParagraphStyle(
        "ValueBig", fontName="Helvetica-Bold", fontSize=20,
        textColor=GRAY_DARK,
    )

    style_value_green = ParagraphStyle(
        "ValueGreen", fontName="Helvetica-Bold", fontSize=20,
        textColor=GREEN,
    )

    style_value_red = ParagraphStyle(  # 👈 NUEVO
        "ValueRed", fontName="Helvetica-Bold", fontSize=20,
        textColor=colors.red,
    )

    style_footer_note = ParagraphStyle(
        "FooterNote", fontName="Helvetica", fontSize=8,
        textColor=GRAY_MID, alignment=TA_CENTER,
    )

    elements = []
    page_w, _ = A4
    content_w = page_w - 60

    # ── Título
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Reporte Diario de Ventas", styles["Title"]))
    elements.append(Paragraph(
        f"{hoy.strftime('%d/%m/%Y')}", styles["Normal"]
    ))

    elements.append(Spacer(1, 10))

    # ── CARDS (MODIFICADAS)
    def card(label, value_text, value_style):
        return Table(
            [[Paragraph(label, style_label)],
             [Paragraph(value_text, value_style)]],
            colWidths=[(content_w / 2) - 10],
        )

    cards = Table([
        [
            card("Total Ventas", f"${total:,.0f}", style_value_big),
            card("Ganancia", f"${ganancia:,.0f}", style_value_green),
        ],
        [
            card("Egresos", f"${total_egresos:,.0f}", style_value_red),  # 👈 NUEVO
            card("Utilidad Real", f"${utilidad_real:,.0f}", style_value_green),  # 👈 NUEVO
        ]
    ])

    elements.append(cards)
    elements.append(Spacer(1, 20))

    # ── TABLA VENTAS (NO TOCADA)
    elements.append(Paragraph("Detalle de Ventas", style_section_title))

    if ventas.exists():
        rows = [["ID", "Hora", "Método", "Total"]]
        for v in ventas:
            rows.append([
                f"#{v.id}",
                v.fecha.strftime("%H:%M"),
                v.get_metodo_pago_display(),
                f"${v.total_venta:,.0f}"
            ])
        elements.append(Table(rows))
    else:
        elements.append(Paragraph("Sin ventas"))

    elements.append(Spacer(1, 20))

    # ── 🆕 TABLA EGRESOS
    elements.append(Paragraph("Detalle de Egresos", style_section_title))

    if egresos.exists():
        rows = [["Nombre", "Descripción", "Monto"]]

        for e in egresos:
            rows.append([
                e.nombre,
                e.descripcion or "-",
                f"${e.monto:,.0f}"
            ])

        elements.append(Table(rows))
    else:
        elements.append(Paragraph("No hay egresos registrados"))

    elements.append(Spacer(1, 20))

    # ── RESUMEN FINAL 🧠
    elements.append(Paragraph("Resumen Final", style_section_title))

    resumen = Table([
        ["Total Ventas", f"${total:,.0f}"],
        ["Total Egresos", f"${total_egresos:,.0f}"],
        ["Utilidad Real", f"${utilidad_real:,.0f}"],
    ])

    elements.append(resumen)

    # ── Build
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response

from django.contrib.auth import get_user_model
from django.http import HttpResponse

def crear_admin(request):
    User = get_user_model()

    key = request.GET.get("key")

    if key != "crear123":
        return HttpResponse("No autorizado", status=403)

    try:
        user, created = User.objects.get_or_create(
            username="wiliam",
            defaults={
                "email": "jordav8a@gmail.com",
            }
        )

        if created:
            user.set_password("12345678")
            user.is_superuser = True
            user.is_staff = True
            user.save()
            return HttpResponse("✅ Superusuario creado correctamente")

        return HttpResponse("⚠️ El usuario ya existe")

    except Exception as e:
        return HttpResponse(f"❌ Error: {str(e)}", status=500)
    
    from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Egreso
import json


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
import json
from .models import Egreso

@csrf_exempt
def egresos_list_create(request):

    # 🔥 GET → LISTA
    if request.method == 'GET':
        egresos = Egreso.objects.all().order_by('-fecha')

        # ✅ SIEMPRE HTML si viene desde navegador (más confiable)
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return render(request, 'egresos/lista.html', {
                'egresos': egresos
            })

        # 🔹 JSON solo para fetch/API
        data = [
            {
                "id": e.id,
                "nombre": e.nombre,
                "descripcion": e.descripcion,
                "monto": float(e.monto),
                "metodo_pago": e.metodo_pago,
                "fecha": e.fecha.strftime('%Y-%m-%d %H:%M')
            }
            for e in egresos
        ]

        return JsonResponse(data, safe=False)

    # 🔥 POST → CREAR
    elif request.method == 'POST':
        try:
            body = json.loads(request.body)

            egreso = Egreso.objects.create(
                nombre=body.get('nombre'),
                descripcion=body.get('descripcion'),
                monto=body.get('monto'),
                metodo_pago=body.get('metodo_pago', 'efectivo')
            )

            return JsonResponse({
                "message": "Egreso creado correctamente",
                "id": egreso.id
            }, status=201)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def egreso_detail(request, pk):
    try:
        egreso = Egreso.objects.get(pk=pk)
    except Egreso.DoesNotExist:
        return JsonResponse({"error": "Egreso no encontrado"}, status=404)

    if request.method == 'GET':
        data = {
            "id": egreso.id,
            "nombre": egreso.nombre,
            "descripcion": egreso.descripcion,
            "monto": float(egreso.monto),
            "metodo_pago": egreso.metodo_pago,
            "fecha": egreso.fecha.strftime('%Y-%m-%d %H:%M')
        }
        return JsonResponse(data)

    elif request.method == 'PUT':
        try:
            body = json.loads(request.body)

            egreso.nombre = body.get('nombre', egreso.nombre)
            egreso.descripcion = body.get('descripcion', egreso.descripcion)
            egreso.monto = body.get('monto', egreso.monto)
            egreso.metodo_pago = body.get('metodo_pago', egreso.metodo_pago)

            egreso.save()

            return JsonResponse({"message": "Egreso actualizado"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    elif request.method == 'DELETE':
        egreso.delete()
        return JsonResponse({"message": "Egreso eliminado"})
    
from django.shortcuts import render, redirect
from .models import Egreso
from django.utils import timezone


def egresos_page(request):
    return render(request, 'egresos/egresos_form.html')


def egresos_guardar(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        monto = request.POST.get('monto')
        metodo_pago = request.POST.get('metodo_pago')

        Egreso.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            monto=monto,
            metodo_pago=metodo_pago,
            fecha=timezone.now()
        )

        return redirect('egresos_page')
    

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Egreso

@login_required
def eliminar_egresos(request):
    Egreso.objects.all().delete()
    return redirect('dashboard')


