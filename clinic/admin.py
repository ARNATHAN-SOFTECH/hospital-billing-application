from django.contrib import admin
from .models import Patient, Treatment, Medicine, Bill, BillItem

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("op_number", "name", "phone", "is_admitted", "ip_number", "created_at")
    search_fields = ("op_number", "name", "phone", "ip_number")
    list_filter = ("is_admitted", "gender")

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "active")
    list_filter = ("active",)
    search_fields = ("name",)

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("name", "medicine_code", "price", "stock_quantity", "active")
    list_filter = ("active",)
    search_fields = ("name", "medicine_code")

class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = ("line_total",)

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "bill_type", "patient", "bill_date", "total", "amount_paid", "balance", "payment_status")
    list_filter = ("bill_type", "payment_status", "payment_method", "bill_date")
    search_fields = ("bill_number", "patient__name", "patient__op_number", "patient__phone")
    inlines = [BillItemInline]
    readonly_fields = ("bill_number", "bill_date", "subtotal", "total", "balance", "payment_status")
