
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Patient, Treatment, Medicine, Bill, BillItem


# --------------------------------------------------
# HELPER: PATIENT FORM CONTEXT
# --------------------------------------------------

def patient_form_context(form_data=None):
    return {
        "form_data": form_data or {},
        "gender_choices": Patient.GENDER_CHOICES,
    }


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@login_required
def dashboard(request):
    today = timezone.localdate()

    context = {
        "patient_count": Patient.objects.count(),
        "admitted_count": Patient.objects.filter(is_admitted=True).count(),
        "today_bills": Bill.objects.filter(bill_date__date=today).count(),
        "today_total": (
            Bill.objects.filter(bill_date__date=today)
            .aggregate(v=Sum("total"))["v"]
            or Decimal("0.00")
        ),
        "pending_total": (
            Bill.objects.aggregate(v=Sum("balance"))["v"]
            or Decimal("0.00")
        ),
        "recent_bills": Bill.objects.select_related("patient")[:6],
        "recent_patients": Patient.objects.all()[:6],
    }

    return render(request, "clinic/dashboard.html", context)


# --------------------------------------------------
# PATIENT LIST
# --------------------------------------------------

@login_required
def patient_list(request):
    q = request.GET.get("q", "").strip()

    patients = Patient.objects.all()

    if q:
        patients = patients.filter(
            Q(name__icontains=q)
            | Q(op_number__icontains=q)
            | Q(ip_number__icontains=q)
            | Q(phone__icontains=q)
        )

    return render(
        request,
        "clinic/patient_list.html",
        {
            "patients": patients,
            "q": q,
        }
    )


# --------------------------------------------------
# CREATE PATIENT
# --------------------------------------------------

@login_required
def patient_create(request):

    if request.method == "POST":

        op_number = request.POST.get("op_number", "").strip()
        name = request.POST.get("name", "").strip()

        # Validate OP number
        if not op_number:
            messages.error(request, "OP number is required.")
            return render(
                request,
                "clinic/patient_form.html",
                patient_form_context(request.POST)
            )

        # Check duplicate OP number
        if Patient.objects.filter(op_number=op_number).exists():
            messages.error(
                request,
                f"OP number '{op_number}' is already registered. "
                "Please enter a different OP number."
            )

            return render(
                request,
                "clinic/patient_form.html",
                patient_form_context(request.POST)
            )

        # Validate patient name
        if not name:
            messages.error(request, "Patient name is required.")

            return render(
                request,
                "clinic/patient_form.html",
                patient_form_context(request.POST)
            )

        # Validate age
        try:
            age_raw = request.POST.get("age", "").strip()
            age = int(age_raw) if age_raw else None

            if age is not None and not (0 <= age <= 125):
                raise ValueError

        except ValueError:
            messages.error(
                request,
                "Enter a valid age between 0 and 125."
            )

            return render(
                request,
                "clinic/patient_form.html",
                patient_form_context(request.POST)
            )

        # Admission details
        is_admitted = request.POST.get("is_admitted") == "on"

        ip_number = request.POST.get("ip_number", "").strip() or None

        if not is_admitted:
            ip_number = None

        # Check duplicate IP number
        if ip_number and Patient.objects.filter(ip_number=ip_number).exists():
            messages.error(
                request,
                f"IP number '{ip_number}' is already in use."
            )

            return render(
                request,
                "clinic/patient_form.html",
                patient_form_context(request.POST)
            )

        # Validate admission dates
        admission_date_raw = request.POST.get("admission_date", "").strip()
        discharge_date_raw = request.POST.get("discharge_date", "").strip()

        admission_date = None
        discharge_date = None

        if is_admitted:
            if admission_date_raw:
                admission_date = parse_date(admission_date_raw)

                if admission_date is None:
                    messages.error(request, "Enter a valid admission date.")
                    return render(
                        request,
                        "clinic/patient_form.html",
                        patient_form_context(request.POST)
                    )

            if discharge_date_raw:
                discharge_date = parse_date(discharge_date_raw)

                if discharge_date is None:
                    messages.error(request, "Enter a valid discharge date.")
                    return render(
                        request,
                        "clinic/patient_form.html",
                        patient_form_context(request.POST)
                    )

        # Save patient
        try:
            with transaction.atomic():

                patient = Patient.objects.create(
                    op_number=op_number,
                    name=name,
                    age=age,
                    gender=request.POST.get("gender", ""),
                    phone=request.POST.get("phone", "").strip(),
                    email=request.POST.get("email", "").strip(),
                    address=request.POST.get("address", "").strip(),

                    is_admitted=is_admitted,
                    ip_number=ip_number,

                    room_number=(
                        request.POST.get("room_number", "").strip()
                        if is_admitted else ""
                    ),

                    admission_date=admission_date,
                    discharge_date=discharge_date,

                    consulting_doctor=(
                        request.POST.get("consulting_doctor", "").strip()
                        if is_admitted else ""
                    ),
                )

        except IntegrityError:
            messages.error(
                request,
                "The OP number or IP number is already registered. "
                "Please check and try again."
            )

            return render(
                request,
                "clinic/patient_form.html",
                patient_form_context(request.POST)
            )

        messages.success(
            request,
            f"Patient registered successfully. OP Number: {patient.op_number}"
        )

        return redirect("patient_detail", pk=patient.pk)

    return render(
        request,
        "clinic/patient_form.html",
        patient_form_context()
    )


# --------------------------------------------------
# PATIENT DETAIL
# --------------------------------------------------

@login_required
def patient_detail(request, pk):

    patient = get_object_or_404(Patient, pk=pk)

    bills = patient.bills.all()

    return render(
        request,
        "clinic/patient_detail.html",
        {
            "patient": patient,
            "bills": bills,
        }
    )


# --------------------------------------------------
# TREATMENT LIST
# --------------------------------------------------

@login_required
def treatment_list(request):

    return render(
        request,
        "clinic/treatment_list.html",
        {
            "items": Treatment.objects.all()
        }
    )


# --------------------------------------------------
# MEDICINE LIST
# --------------------------------------------------

@login_required
def medicine_list(request):

    return render(
        request,
        "clinic/medicine_list.html",
        {
            "items": Medicine.objects.all()
        }
    )


# --------------------------------------------------
# CREATE BILL
# --------------------------------------------------

@login_required
def create_bill(request, bill_type):

    if bill_type not in ("treatment", "medicine"):
        return redirect("dashboard")

    patients = Patient.objects.all().order_by("name")

    catalogue = (
        Treatment.objects.filter(active=True)
        if bill_type == "treatment"
        else Medicine.objects.filter(active=True)
    )

    if request.method == "POST":

        patient_mode = request.POST.get("patient_mode", "existing")

        patient = None

        try:
            with transaction.atomic():

                # ----------------------------------
                # NEW PATIENT
                # ----------------------------------

                if patient_mode == "new":

                    new_op_number = request.POST.get(
                        "new_op_number", ""
                    ).strip()

                    name = request.POST.get(
                        "new_name", ""
                    ).strip()

                    if not new_op_number:
                        raise ValueError(
                            "Enter the new patient's OP number."
                        )

                    if Patient.objects.filter(
                        op_number=new_op_number
                    ).exists():
                        raise ValueError(
                            f"OP number '{new_op_number}' is already registered."
                        )

                    if not name:
                        raise ValueError(
                            "Enter the new patient's name."
                        )

                    age_text = request.POST.get(
                        "new_age", ""
                    ).strip()

                    age = int(age_text) if age_text else None

                    if age is not None and not 0 <= age <= 125:
                        raise ValueError(
                            "Enter a valid patient age."
                        )

                    admitted = (
                        request.POST.get("new_is_admitted") == "on"
                    )

                    new_ip_number = (
                        request.POST.get("new_ip_number", "").strip()
                        or None
                    ) if admitted else None

                    if new_ip_number and Patient.objects.filter(
                        ip_number=new_ip_number
                    ).exists():
                        raise ValueError(
                            f"IP number '{new_ip_number}' is already in use."
                        )

                    admission_date_raw = request.POST.get(
                        "new_admission_date", ""
                    ).strip()

                    discharge_date_raw = request.POST.get(
                        "new_discharge_date", ""
                    ).strip()

                    admission_date = (
                        parse_date(admission_date_raw)
                        if admitted and admission_date_raw
                        else None
                    )

                    discharge_date = (
                        parse_date(discharge_date_raw)
                        if admitted and discharge_date_raw
                        else None
                    )

                    if admitted and admission_date_raw and not admission_date:
                        raise ValueError("Enter a valid admission date.")

                    if admitted and discharge_date_raw and not discharge_date:
                        raise ValueError("Enter a valid discharge date.")

                    patient = Patient.objects.create(
                        op_number=new_op_number,
                        name=name,
                        age=age,

                        gender=request.POST.get(
                            "new_gender", ""
                        ),

                        phone=request.POST.get(
                            "new_phone", ""
                        ).strip(),

                        address=request.POST.get(
                            "new_address", ""
                        ).strip(),

                        is_admitted=admitted,
                        ip_number=new_ip_number,

                        room_number=(
                            request.POST.get(
                                "new_room_number", ""
                            ).strip()
                            if admitted else ""
                        ),

                        admission_date=admission_date,
                        discharge_date=discharge_date,

                        consulting_doctor=(
                            request.POST.get(
                                "new_consulting_doctor", ""
                            ).strip()
                            if admitted else ""
                        ),
                    )

                # ----------------------------------
                # EXISTING PATIENT
                # ----------------------------------

                else:

                    patient_id = request.POST.get("patient_id")

                    if not patient_id:
                        raise ValueError("Select a patient.")

                    patient = Patient.objects.get(pk=patient_id)

                # ----------------------------------
                # BILL ITEMS
                # ----------------------------------

                selected_ids = request.POST.getlist("item_id")
                quantities = request.POST.getlist("quantity")

                if not selected_ids:
                    raise ValueError(
                        "Add at least one item to the bill."
                    )

                if len(selected_ids) != len(quantities):
                    raise ValueError(
                        "The bill items are invalid. Please try again."
                    )

                bill = Bill.objects.create(
                    bill_type=bill_type,
                    patient=patient,
                    discount=Decimal("0.00"),
                    amount_paid=Decimal("0.00"),
                    payment_method=request.POST.get(
                        "payment_method", "Cash"
                    ),
                    notes=request.POST.get("notes", "").strip(),
                    created_by=request.user,
                )

                subtotal = Decimal("0.00")

                for item_id, quantity_text in zip(
                    selected_ids, quantities
                ):

                    try:
                        quantity = int(quantity_text)

                    except (ValueError, TypeError):
                        raise ValueError(
                            "Quantity must be a positive whole number."
                        )

                    if quantity < 1:
                        raise ValueError(
                            "Quantity must be at least 1."
                        )

                    if bill_type == "treatment":

                        item = Treatment.objects.select_for_update().get(
                            pk=item_id,
                            active=True
                        )

                    else:

                        item = Medicine.objects.select_for_update().get(
                            pk=item_id,
                            active=True
                        )

                        if item.stock_quantity < quantity:
                            raise ValueError(
                                f"Not enough stock for {item.name}. "
                                f"Available: {item.stock_quantity}."
                            )

                        item.stock_quantity -= quantity

                        item.save(
                            update_fields=["stock_quantity"]
                        )

                    line_total = item.price * quantity

                    BillItem.objects.create(
                        bill=bill,
                        item_name=item.name,
                        quantity=quantity,
                        unit_price=item.price,
                        line_total=line_total,
                    )

                    subtotal += line_total

                # ----------------------------------
                # DISCOUNT AND PAYMENT
                # ----------------------------------

                try:
                    discount = Decimal(
                        request.POST.get("discount", "0") or "0"
                    )

                    amount_paid = Decimal(
                        request.POST.get("amount_paid", "0") or "0"
                    )

                except (InvalidOperation, ValueError):
                    raise ValueError(
                        "Enter valid discount and payment amounts."
                    )

                if not discount.is_finite() or not amount_paid.is_finite():
                    raise ValueError(
                        "Enter valid discount and payment amounts."
                    )

                if discount < 0 or amount_paid < 0:
                    raise ValueError(
                        "Discount and payment cannot be negative."
                    )

                if discount > subtotal:
                    raise ValueError(
                        "Discount cannot be greater than the subtotal."
                    )

                total = subtotal - discount

                if amount_paid > total:
                    raise ValueError(
                        "Amount paid cannot exceed the bill total."
                    )

                bill.subtotal = subtotal
                bill.discount = discount
                bill.total = total
                bill.amount_paid = amount_paid

                bill.save()

        # ----------------------------------
        # ERROR HANDLING
        # ----------------------------------

        except Patient.DoesNotExist:

            messages.error(
                request,
                "The selected patient could not be found."
            )

            return render(
                request,
                "clinic/bill_form.html",
                {
                    "bill_type": bill_type,
                    "patients": patients,
                    "catalogue": catalogue,
                    "form_data": request.POST,
                }
            )

        except (ValueError, Treatment.DoesNotExist, Medicine.DoesNotExist) as exc:

            messages.error(request, str(exc))

            return render(
                request,
                "clinic/bill_form.html",
                {
                    "bill_type": bill_type,
                    "patients": patients,
                    "catalogue": catalogue,
                    "form_data": request.POST,
                }
            )

        except IntegrityError:

            messages.error(
                request,
                "A duplicate OP number, IP number, or other database "
                "conflict occurred. Please check the entered details."
            )

            return render(
                request,
                "clinic/bill_form.html",
                {
                    "bill_type": bill_type,
                    "patients": patients,
                    "catalogue": catalogue,
                    "form_data": request.POST,
                }
            )

        messages.success(
            request,
            f"{bill.get_bill_type_display()} bill "
            f"{bill.bill_number} generated."
        )

        return redirect("bill_detail", pk=bill.pk)

    return render(
        request,
        "clinic/bill_form.html",
        {
            "bill_type": bill_type,
            "patients": patients,
            "catalogue": catalogue,
            "form_data": {},
        }
    )


# --------------------------------------------------
# BILL LIST
# --------------------------------------------------

@login_required
def bill_list(request):

    q = request.GET.get("q", "").strip()
    bill_type = request.GET.get("type", "").strip()

    bills = Bill.objects.select_related("patient").all()

    if q:
        bills = bills.filter(
            Q(bill_number__icontains=q)
            | Q(patient__name__icontains=q)
            | Q(patient__op_number__icontains=q)
            | Q(patient__phone__icontains=q)
        )

    if bill_type in ("treatment", "medicine"):
        bills = bills.filter(bill_type=bill_type)

    return render(
        request,
        "clinic/bill_list.html",
        {
            "bills": bills,
            "q": q,
            "bill_type": bill_type,
        }
    )


# --------------------------------------------------
# BILL DETAIL
# --------------------------------------------------

@login_required
def bill_detail(request, pk):

    bill = get_object_or_404(
        Bill.objects.select_related(
            "patient",
            "created_by"
        ).prefetch_related("items"),
        pk=pk
    )

    return render(
        request,
        "clinic/bill_detail.html",
        {
            "bill": bill
        }
    )
