from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    GENDER_CHOICES = [("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
    op_number = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=150)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_admitted = models.BooleanField(default=False)
    ip_number = models.CharField(max_length=30, blank=True, unique=True, null=True)
    room_number = models.CharField(max_length=30, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    discharge_date = models.DateField(null=True, blank=True)
    consulting_doctor = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.op_number:
            last = Patient.objects.order_by("-id").first()
            next_number = (last.id + 1) if last else 1
            self.op_number = f"OP{next_number:05d}"
        if not self.ip_number:
            self.ip_number = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.op_number} - {self.name}"


class Treatment(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Medicine(models.Model):
    name = models.CharField(max_length=150, unique=True)
    medicine_code = models.CharField(max_length=40, blank=True)
    unit = models.CharField(max_length=30, default="unit")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    stock_quantity = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Bill(models.Model):
    BILL_TYPES = [("treatment", "Treatment"), ("medicine", "Medicine")]
    PAYMENT_METHODS = [
        ("Cash", "Cash"), ("UPI", "UPI"), ("Card", "Card"), ("Bank Transfer", "Bank Transfer")
    ]
    PAYMENT_STATUSES = [("Pending", "Pending"), ("Partial", "Partial"), ("Paid", "Paid")]

    bill_number = models.CharField(max_length=32, unique=True, blank=True)
    bill_type = models.CharField(max_length=20, choices=BILL_TYPES)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="bills")
    bill_date = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="Cash")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default="Pending")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-bill_date"]

    def save(self, *args, **kwargs):
        if not self.bill_number:
            prefix = "TB" if self.bill_type == "treatment" else "MB"
            today = timezone.localdate().strftime("%Y%m%d")
            count = Bill.objects.filter(bill_number__startswith=f"{prefix}-{today}-").count() + 1
            self.bill_number = f"{prefix}-{today}-{count:04d}"
        self.balance = max(Decimal("0.00"), self.total - self.amount_paid)
        if self.amount_paid <= 0:
            self.payment_status = "Pending"
        elif self.amount_paid < self.total:
            self.payment_status = "Partial"
        else:
            self.payment_status = "Paid"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.bill_number


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"
