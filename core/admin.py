from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, Price, Stock, StockRecord, Transaction, AuditLog

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'nickname', 'phone_number', 'date_created']
    search_fields = ['full_name', 'nickname', 'phone_number']
    list_filter = ['date_created']

@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ['category', 'price', 'date_updated', 'updated_by']
    list_editable = ['price']

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['category', 'quantity', 'low_stock_threshold', 'last_updated', 'stock_status']
    list_editable = ['low_stock_threshold']

    def stock_status(self, obj):
        if obj.is_low_stock():
            return format_html('<span style="color: red;">⚠️ Low Stock</span>')
        return format_html('<span style="color: green;">✓ Good</span>')
    stock_status.short_description = 'Status'

@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ['category', 'quantity_added', 'date_recorded', 'recorded_by']
    list_filter = ['category', 'date_recorded']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'egg_category', 'quantity', 'total_amount', 'transaction_date']
    list_filter = ['egg_category', 'transaction_date']
    search_fields = ['invoice_number', 'customer__full_name']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name']
    list_filter = ['action', 'timestamp']
    readonly_fields = ['details']