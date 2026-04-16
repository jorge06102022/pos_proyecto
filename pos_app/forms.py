"""
forms.py - Formularios del sistema POS
"""
from django import forms
from .models import Producto, Categoria


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de categoría'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'sku', 'categoria', 'precio_compra',
            'precio_venta', 'stock', 'stock_minimo', 'descripcion'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Nombre del producto'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Código único (ej: PROD-001)'
            }),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'precio_compra': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'
            }),
            'precio_venta': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'placeholder': '0'
            }),
            'stock_minimo': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'placeholder': '5'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'
            }),
        }
        labels = {
            'nombre': 'Nombre del Producto',
            'sku': 'Código / SKU',
            'categoria': 'Categoría',
            'precio_compra': 'Precio de Compra ($)',
            'precio_venta': 'Precio de Venta ($)',
            'stock': 'Stock Inicial',
            'stock_minimo': 'Stock Mínimo (alerta)',
            'descripcion': 'Descripción',
        }

    def clean(self):
        cleaned_data = super().clean()
        precio_compra = cleaned_data.get('precio_compra')
        precio_venta = cleaned_data.get('precio_venta')
        if precio_compra and precio_venta:
            if precio_venta < precio_compra:
                self.add_error(
                    'precio_venta',
                    'El precio de venta no puede ser menor al precio de compra.'
                )
        return cleaned_data
