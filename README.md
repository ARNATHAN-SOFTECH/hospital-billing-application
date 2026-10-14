# Hospital Billing Application

A starter hospital billing system built with Django and SQLite.

## Features
- Staff login/logout using Django authentication
- Dashboard
- Patient registration with OP number and optional admission/IP details
- Patient listing and search
- Treatment and medicine catalogues
- Separate treatment and medicine bills
- Payment status, paid amount, balance and printable invoice
- Medicine stock deduction when a medicine bill is created
- Django admin for managing staff, treatments, medicines and records

## Setup (Windows PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py makemigrations clinic
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in using the superuser credentials.

## First-time setup
1. Log in to `/admin/`.
2. Add Treatment records and Medicine records.
3. Return to the dashboard and register patients / generate bills.

## Notes
- This is a starter application. Before real clinical/financial use, add backups, HTTPS, role permissions, audit logging, tax rules, and client-approved invoice wording.
- SQLite is suitable for local development. For multiple simultaneous staff users in production, configure PostgreSQL or MySQL.
