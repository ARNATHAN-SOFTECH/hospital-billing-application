from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("patients/", views.patient_list, name="patient_list"),
    path("patients/new/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("treatments/", views.treatment_list, name="treatment_list"),
    path("medicines/", views.medicine_list, name="medicine_list"),
    path("billing/treatment/new/", views.create_bill, {"bill_type": "treatment"}, name="treatment_bill_create"),
    path("billing/medicine/new/", views.create_bill, {"bill_type": "medicine"}, name="medicine_bill_create"),
    path("bills/", views.bill_list, name="bill_list"),
    path("bills/<int:pk>/", views.bill_detail, name="bill_detail"),
]
