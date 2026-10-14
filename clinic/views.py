from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Patient, Treatment, Medicine, Bill, BillItem


@login_required
def dashboard(request):
    today = timezone.localdate()
    context = {
        "patient_count": Patient.objects.count(),
        "admitted_count": Patient.objects.filter(is_admitted=True).count(),
        "today_bills": Bill.objects.filter(bill_date__date=today).count(),
        "today_total": Bill.objects.filter(bill_date__date=today).aggregate(v=Sum("total"))["v"] or Decimal("0.00"),
        "pending_total": Bill.objects.aggregate(v=Sum("balance"))["v"] or Decimal("0.00"),
        "recent_bills": Bill.objects.select_related("patient")[:6],
        "recent_patients": Patient.objects.all()[:6],
    }
    return render(request, "clinic/dashboard.html", context)


@login_required
def patient_list(request):
    q = request.GET.get("q", "").strip()
    patients = Patient.objects.all()
    if q:
        patients = patients.filter(
            Q(name__icontains=q) | Q(op_number__icontains=q) |
            Q(ip_number__icontains=q) | Q(phone__icontains=q)
        )
    return render(request, "clinic/patient_list.html", {"patients": patients, "q": q})


@login_required
def patient_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Patient name is required.")
            return render(request, "clinic/patient_form.html", {"form_data": request.POST})
        try:
            age_raw = request.POST.get("age", "").strip()
            age = int(age_raw) if age_raw else None
            if age is not None and not (0 <= age <= 125):
                raise ValueError
        except ValueError:
            messages.error(request, "Enter a valid age between 0 and 125.")
            return render(request, "clinic/patient_form.html", {"form_data": request.POST})
        is_admitted = request.POST.get("is_admitted") == "on"
        ip_number = request.POST.get("ip_number", "").strip() or None
        if not is_admitted:
            ip_number = None
        try:
            patient = Patient.objects.create(
                name=name,
                age=age,
                gender=request.POST.get("gender", ""),
                phone=request.POST.get("phone", "").strip(),
                email=request.POST.get("email", "").strip(),
                address=request.POST.get("address", "").strip(),
                is_admitted=is_admitted,
                ip_number=ip_number,
                room_number=request.POST.get("room_number", "").strip() if is_admitted else "",
                admission_date=request.POST.get("admission_date") or None if is_admitted else None,
                discharge_date=request.POST.get("discharge_date") or None if is_admitted else None,
                consulting_doctor=request.POST.get("consulting_doctor", "").strip() if is_admitted else "",
            )
        except Exception as exc:
            if "ip_number" in str(exc).lower() or "unique" in str(exc).lower():
                messages.error(request, "That IP number is already in use. Please enter a different one.")
            else:
                messages.error(request, "Unable to save patient. Please check the entered details.")
            return render(request, "clinic/patient_form.html", {"form_data": request.POST})
        messages.success(request, f"Patient registered successfully. OP Number: {patient.op_number}")
        return redirect("patient_detail", pk=patient.pk)
    return render(request, "clinic/patient_form.html", {"form_data": {}})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    bills = patient.bills.all()
    return render(request, "clinic/patient_detail.html", {"patient": patient, "bills": bills})


@login_required
def treatment_list(request):
    return render(request, "clinic/treatment_list.html", {"items": Treatment.objects.all()})


@login_required
def medicine_list(request):
    return render(request, "clinic/medicine_list.html", {"items": Medicine.objects.all()})


@login_required
def create_bill(request, bill_type):
    if bill_type not in ("treatment", "medicine"):
        return redirect("dashboard")
    patients = Patient.objects.all().order_by("name")
    catalogue = Treatment.objects.filter(active=True) if bill_type == "treatment" else Medicine.objects.filter(active=True)
    if request.method == "POST":
        patient_mode = request.POST.get("patient_mode", "existing")
        patient = None
        try:
            with transaction.atomic():
                if patient_mode == "new":
                    name = request.POST.get("new_name", "").strip()
                    if not name:
                        raise ValueError("Enter the new patient's name.")
                    age_text = request.POST.get("new_age", "").strip()
                    age = int(age_text) if age_text else None
                    if age is not None and not 0 <= age <= 125:
                        raise ValueError("Enter a valid patient age.")
                    admitted = request.POST.get("new_is_admitted") == "on"
                    patient = Patient.objects.create(
                        name=name, age=age,
                        gender=request.POST.get("new_gender", ""),
                        phone=request.POST.get("new_phone", "").strip(),
                        address=request.POST.get("new_address", "").strip(),
                        is_admitted=admitted,
                        ip_number=(request.POST.get("new_ip_number", "").strip() or None) if admitted else None,
                        room_number=request.POST.get("new_room_number", "").strip() if admitted else "",
                        admission_date=(request.POST.get("new_admission_date") or None) if admitted else None,
                        discharge_date=(request.POST.get("new_discharge_date") or None) if admitted else None,
                        consulting_doctor=request.POST.get("new_consulting_doctor", "").strip() if admitted else "",
                    )
                else:
                    patient_id = request.POST.get("patient_id")
                    if not patient_id:
                        raise ValueError("Select a patient.")
                    patient = Patient.objects.get(pk=patient_id)

                selected_ids = request.POST.getlist("item_id")
                quantities = request.POST.getlist("quantity")
                if not selected_ids:
                    raise ValueError("Add at least one item to the bill.")
                if len(selected_ids) != len(quantities):
                    raise ValueError("The bill items are invalid. Please try again.")

                bill = Bill.objects.create(
                    bill_type=bill_type,
                    patient=patient,
                    discount=Decimal("0.00"),
                    amount_paid=Decimal("0.00"),
                    payment_method=request.POST.get("payment_method", "Cash"),
                    notes=request.POST.get("notes", "").strip(),
                    created_by=request.user,
                )
                subtotal = Decimal("0.00")
                for item_id, quantity_text in zip(selected_ids, quantities):
                    try:
                        quantity = int(quantity_text)
                    except (ValueError, TypeError):
                        raise ValueError("Quantity must be a positive whole number.")
                    if quantity < 1:
                        raise ValueError("Quantity must be at least 1.")
                    if bill_type == "treatment":
                        item = Treatment.objects.select_for_update().get(pk=item_id, active=True)
                    else:
                        item = Medicine.objects.select_for_update().get(pk=item_id, active=True)
                        if item.stock_quantity < quantity:
                            raise ValueError(f"Not enough stock for {item.name}. Available: {item.stock_quantity}.")
                        item.stock_quantity -= quantity
                        item.save(update_fields=["stock_quantity"])
                    line_total = item.price * quantity
                    BillItem.objects.create(
                        bill=bill, item_name=item.name, quantity=quantity,
                        unit_price=item.price, line_total=line_total
                    )
                    subtotal += line_total

                try:
                    discount = Decimal(request.POST.get("discount", "0") or "0")
                    amount_paid = Decimal(request.POST.get("amount_paid", "0") or "0")
                except InvalidOperation:
                    raise ValueError("Enter valid discount and payment amounts.")
                if discount < 0 or amount_paid < 0:
                    raise ValueError("Discount and payment cannot be negative.")
                if discount > subtotal:
                    raise ValueError("Discount cannot be greater than the subtotal.")
                total = subtotal - discount
                if amount_paid > total:
                    raise ValueError("Amount paid cannot exceed the bill total.")
                bill.subtotal = subtotal
                bill.discount = discount
                bill.total = total
                bill.amount_paid = amount_paid
                bill.save()
        except Patient.DoesNotExist:
            messages.error(request, "The selected patient could not be found.")
            return render(request, "clinic/bill_form.html", {"bill_type": bill_type, "patients": patients, "catalogue": catalogue})
        except (ValueError, Treatment.DoesNotExist, Medicine.DoesNotExist) as exc:
            messages.error(request, str(exc))
            return render(request, "clinic/bill_form.html", {
                "bill_type": bill_type, "patients": patients, "catalogue": catalogue,
                "form_data": request.POST,
            })
        messages.success(request, f"{bill.get_bill_type_display()} bill {bill.bill_number} generated.")
        return redirect("bill_detail", pk=bill.pk)

    return render(request, "clinic/bill_form.html", {
        "bill_type": bill_type, "patients": patients, "catalogue": catalogue, "form_data": {}
    })


@login_required
def bill_list(request):
    q = request.GET.get("q", "").strip()
    bill_type = request.GET.get("type", "").strip()
    bills = Bill.objects.select_related("patient").all()
    if q:
        bills = bills.filter(
            Q(bill_number__icontains=q) | Q(patient__name__icontains=q) |
            Q(patient__op_number__icontains=q) | Q(patient__phone__icontains=q)
        )
    if bill_type in ("treatment", "medicine"):
        bills = bills.filter(bill_type=bill_type)
    return render(request, "clinic/bill_list.html", {"bills": bills, "q": q, "bill_type": bill_type})


@login_required
def bill_detail(request, pk):
    bill = get_object_or_404(Bill.objects.select_related("patient", "created_by").prefetch_related("items"), pk=pk)
    return render(request, "clinic/bill_detail.html", {"bill": bill})
