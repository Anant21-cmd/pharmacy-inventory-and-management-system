# Pharmacy Inventory and Management System

A complete full-stack Pharmacy Inventory and Management System built with Python, Flask, and MongoDB.

## Features
- **Role-based Access Control**: Admin, Pharmacist, and Staff.
- **Dashboard**: Real-time stats on medicines, stock, sales, and purchases.
- **Medicine Management**: Full CRUD with minimum stock and expiry date tracking.
- **Inventory Tracking**: Automated real-time low-stock and expiry alerts.
- **Sales & POS System**: Interactive billing system with automatic inventory updates.
- **Purchases**: Add stock with automatic inventory increment.
- **Customers & Suppliers Management**.
- **Prescriptions**: Manage customer prescriptions securely.
- **Reports**: View Sales, Purchases, Stock, and Profit reports.
- **Invoice Generation**: Printable invoices for sales.

## Technology Stack
- **Backend**: Python 3, Flask
- **Database**: MongoDB (via PyMongo)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Jinja2
- **Authentication**: Flask-Login, Flask-Bcrypt

## Installation

1. **Clone the repository** (or download the source code).
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and update the `MONGO_URI` if necessary.
6. **Ensure MongoDB is running** (locally on port 27017 or use Atlas URI).
7. **Seed the database**:
   ```bash
   python database/seed.py
   ```
8. **Run the application**:
   ```bash
   python app.py
   ```
9. **Access the application**: Open `http://127.0.0.1:5000`

## Demo Credentials
- **Admin**: `admin@pharmacy.com` / `Admin@123`
- **Pharmacist**: `pharmacist@pharmacy.com` / `Pharma@123`
- **Staff**: `staff@pharmacy.com` / `Staff@123`
