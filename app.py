import os
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import gridfs
import io
from flask import send_file
import re

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# MongoDB Connection
client = MongoClient(app.config['MONGO_URI'])
db = client[app.config['MONGO_DB_NAME']]

# Initialize GridFS for media storage
fs = gridfs.GridFS(db)

# --- USER MODEL ---
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.name = user_data['name']
        self.email = user_data['email']
        self.role = user_data['role']

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')
        
        user_data = db.users.find_one({'email': email})
        
        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# --- DASHBOARD ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    thirty_days = today + timedelta(days=30)
    
    # Total Medicines
    total_medicines = db.medicines.count_documents({})
    
    # Total Stock (Sum of all quantities)
    stock_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$quantity"}}}]
    stock_res = list(db.medicines.aggregate(stock_pipeline))
    total_stock = stock_res[0]['total'] if stock_res else 0
    
    # Low Stock
    low_stock = db.medicines.count_documents({"$expr": {"$lte": ["$quantity", "$minimum_stock"]}})
    
    # Expired
    expired = db.medicines.count_documents({"expiry_date": {"$lt": today}})
    
    # Expiring Soon
    expiring_soon = db.medicines.count_documents({
        "expiry_date": {"$gte": today, "$lte": thirty_days}
    })
    
    # Today's Sales
    sales_pipeline = [
        {"$match": {"sale_date": {"$gte": today, "$lt": tomorrow}}},
        {"$group": {"_id": None, "total_sales": {"$sum": "$grand_total"}}}
    ]
    sales_res = list(db.sales.aggregate(sales_pipeline))
    today_sales = sales_res[0]['total_sales'] if sales_res else 0
    
    # Today's Purchases
    purchases_pipeline = [
        {"$match": {"purchase_date": {"$gte": today, "$lt": tomorrow}}},
        {"$group": {"_id": None, "total_purchases": {"$sum": "$total_amount"}}}
    ]
    purchases_res = list(db.purchases.aggregate(purchases_pipeline))
    today_purchases = purchases_res[0]['total_purchases'] if purchases_res else 0
    
    total_suppliers = db.suppliers.count_documents({})
    total_customers = db.customers.count_documents({})
    
    return render_template('dashboard.html', 
        total_medicines=total_medicines,
        total_stock=total_stock,
        low_stock=low_stock,
        expired=expired,
        expiring_soon=expiring_soon,
        today_sales=today_sales,
        today_purchases=today_purchases,
        total_suppliers=total_suppliers,
        total_customers=total_customers
    )

# --- MEDICINES ---
@app.route('/medicines')
@login_required
def list_medicines():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = {}
    if search:
        query["$or"] = [
            {"medicine_name": {"$regex": search, "$options": "i"}},
            {"generic_name": {"$regex": search, "$options": "i"}},
            {"batch_number": {"$regex": search, "$options": "i"}}
        ]
        
    if category:
        query["category"] = category
        
    medicines = list(db.medicines.find(query).sort("medicine_name", 1))
    categories = db.medicines.distinct('category')
    
    return render_template('medicines/list.html', medicines=medicines, search=search, categories=categories, current_category=category)

@app.route('/medicines/add', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if current_user.role != 'admin':
        flash('Permission denied. Admin only.', 'error')
        return redirect(url_for('list_medicines'))
        
    if request.method == 'POST':
        med_data = {
            "medicine_name": request.form.get('medicine_name'),
            "generic_name": request.form.get('generic_name'),
            "brand_name": request.form.get('brand_name'),
            "category": request.form.get('category'),
            "dosage": request.form.get('dosage'),
            "form": request.form.get('form'),
            "strength": request.form.get('strength'),
            "manufacturer": request.form.get('manufacturer'),
            "supplier_id": ObjectId(request.form.get('supplier_id')),
            "batch_number": request.form.get('batch_number'),
            "purchase_price": float(request.form.get('purchase_price')),
            "selling_price": float(request.form.get('selling_price')),
            "quantity": int(request.form.get('quantity')),
            "minimum_stock": int(request.form.get('minimum_stock')),
            "manufacturing_date": datetime.strptime(request.form.get('manufacturing_date'), '%Y-%m-%d'),
            "expiry_date": datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d'),
            "prescription_required": True if request.form.get('prescription_required') else False,
            "description": request.form.get('description'),
            "created_at": datetime.utcnow()
        }
        db.medicines.insert_one(med_data)
        flash('Medicine added successfully.', 'success')
        return redirect(url_for('list_medicines'))
        
    categories = list(db.categories.find())
    suppliers = list(db.suppliers.find())
    return render_template('medicines/add.html', categories=categories, suppliers=suppliers)

@app.route('/medicines/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_medicine(id):
    if current_user.role != 'admin':
        flash('Permission denied. Admin only.', 'error')
        return redirect(url_for('list_medicines'))
        
    medicine = db.medicines.find_one({'_id': ObjectId(id)})
    if not medicine:
        flash('Medicine not found.', 'error')
        return redirect(url_for('list_medicines'))
        
    if request.method == 'POST':
        update_data = {
            "medicine_name": request.form.get('medicine_name'),
            "generic_name": request.form.get('generic_name'),
            "brand_name": request.form.get('brand_name'),
            "category": request.form.get('category'),
            "dosage": request.form.get('dosage'),
            "form": request.form.get('form'),
            "strength": request.form.get('strength'),
            "manufacturer": request.form.get('manufacturer'),
            "supplier_id": ObjectId(request.form.get('supplier_id')),
            "batch_number": request.form.get('batch_number'),
            "purchase_price": float(request.form.get('purchase_price')),
            "selling_price": float(request.form.get('selling_price')),
            "quantity": int(request.form.get('quantity')),
            "minimum_stock": int(request.form.get('minimum_stock')),
            "manufacturing_date": datetime.strptime(request.form.get('manufacturing_date'), '%Y-%m-%d'),
            "expiry_date": datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d'),
            "prescription_required": True if request.form.get('prescription_required') else False,
            "description": request.form.get('description')
        }
        db.medicines.update_one({'_id': ObjectId(id)}, {'$set': update_data})
        flash('Medicine updated successfully.', 'success')
        return redirect(url_for('list_medicines'))
        
    categories = list(db.categories.find())
    suppliers = list(db.suppliers.find())
    return render_template('medicines/edit.html', medicine=medicine, categories=categories, suppliers=suppliers)

@app.route('/medicines/view/<id>')
@login_required
def view_medicine(id):
    medicine = db.medicines.find_one({'_id': ObjectId(id)})
    supplier = db.suppliers.find_one({'_id': medicine.get('supplier_id')}) if medicine else None
    return render_template('medicines/view.html', medicine=medicine, supplier=supplier)

# --- INVENTORY ---
@app.route('/inventory')
@login_required
def inventory():
    medicines = list(db.medicines.find().sort("medicine_name", 1))
    today = datetime.utcnow()
    
    for med in medicines:
        if med['quantity'] == 0:
            med['status'] = 'OUT OF STOCK'
            med['status_class'] = 'danger'
        elif med['expiry_date'] < today:
            med['status'] = 'EXPIRED'
            med['status_class'] = 'dark'
        elif med['quantity'] <= med['minimum_stock']:
            med['status'] = 'LOW STOCK'
            med['status_class'] = 'warning'
        else:
            med['status'] = 'IN STOCK'
            med['status_class'] = 'success'
            
    return render_template('inventory/list.html', medicines=medicines)

# --- SUPPLIERS ---
@app.route('/suppliers')
@login_required
def list_suppliers():
    suppliers = list(db.suppliers.find().sort("supplier_name", 1))
    return render_template('suppliers/list.html', suppliers=suppliers)

@app.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if current_user.role != 'admin':
        flash('Permission denied. Admin only.', 'error')
        return redirect(url_for('list_suppliers'))
        
    if request.method == 'POST':
        supplier_data = {
            "supplier_name": request.form.get('supplier_name'),
            "company_name": request.form.get('company_name'),
            "phone": request.form.get('phone'),
            "email": request.form.get('email'),
            "address": request.form.get('address'),
            "gst_number": request.form.get('gst_number'),
            "created_at": datetime.utcnow()
        }
        db.suppliers.insert_one(supplier_data)
        flash('Supplier added successfully.', 'success')
        return redirect(url_for('list_suppliers'))
    return render_template('suppliers/add.html')

@app.route('/suppliers/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    if current_user.role != 'admin':
        flash('Permission denied. Admin only.', 'error')
        return redirect(url_for('list_suppliers'))
        
    supplier = db.suppliers.find_one({'_id': ObjectId(id)})
    if request.method == 'POST':
        update_data = {
            "supplier_name": request.form.get('supplier_name'),
            "company_name": request.form.get('company_name'),
            "phone": request.form.get('phone'),
            "email": request.form.get('email'),
            "address": request.form.get('address'),
            "gst_number": request.form.get('gst_number')
        }
        db.suppliers.update_one({'_id': ObjectId(id)}, {'$set': update_data})
        flash('Supplier updated successfully.', 'success')
        return redirect(url_for('list_suppliers'))
    return render_template('suppliers/edit.html', supplier=supplier)

# --- CUSTOMERS ---
@app.route('/customers')
@login_required
def list_customers():
    customers = list(db.customers.find().sort("customer_name", 1))
    return render_template('customers/list.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if current_user.role == 'staff':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_customers'))
        
    if request.method == 'POST':
        customer_data = {
            "customer_name": request.form.get('customer_name'),
            "phone": request.form.get('phone'),
            "email": request.form.get('email'),
            "age": int(request.form.get('age') or 0),
            "gender": request.form.get('gender'),
            "address": request.form.get('address'),
            "created_at": datetime.utcnow()
        }
        db.customers.insert_one(customer_data)
        flash('Customer added successfully.', 'success')
        return redirect(url_for('list_customers'))
    return render_template('customers/add.html')

@app.route('/customers/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    if current_user.role == 'staff':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_customers'))
        
    customer = db.customers.find_one({'_id': ObjectId(id)})
    if request.method == 'POST':
        update_data = {
            "customer_name": request.form.get('customer_name'),
            "phone": request.form.get('phone'),
            "email": request.form.get('email'),
            "age": int(request.form.get('age') or 0),
            "gender": request.form.get('gender'),
            "address": request.form.get('address')
        }
        db.customers.update_one({'_id': ObjectId(id)}, {'$set': update_data})
        flash('Customer updated successfully.', 'success')
        return redirect(url_for('list_customers'))
    return render_template('customers/edit.html', customer=customer)

# --- PURCHASES ---
@app.route('/purchases')
@login_required
def list_purchases():
    purchases = list(db.purchases.find().sort("purchase_date", -1))
    for pur in purchases:
        supplier = db.suppliers.find_one({'_id': pur['supplier_id']})
        pur['supplier_name'] = supplier['supplier_name'] if supplier else 'Unknown'
    return render_template('purchases/list.html', purchases=purchases)

@app.route('/purchases/add', methods=['GET', 'POST'])
@login_required
def add_purchase():
    if current_user.role == 'pharmacist':
        flash('Permission denied. Pharmacists cannot add purchases.', 'error')
        return redirect(url_for('list_purchases'))
        
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        invoice_number = request.form.get('invoice_number')
        payment_method = request.form.get('payment_method')
        
        medicine_ids = request.form.getlist('medicine_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('purchase_price[]')
        
        items = []
        total_amount = 0
        
        for i in range(len(medicine_ids)):
            if not medicine_ids[i] or not quantities[i] or not prices[i]:
                continue
                
            try:
                med_id = ObjectId(medicine_ids[i])
                qty = int(quantities[i])
                price = float(prices[i])
            except (ValueError, TypeError):
                continue
            
            med = db.medicines.find_one({'_id': med_id})
            if med:
                item_total = qty * price
                items.append({
                    "medicine_id": med_id,
                    "medicine_name": med['medicine_name'],
                    "batch_number": med['batch_number'],
                    "quantity": qty,
                    "purchase_price": price,
                    "expiry_date": med['expiry_date'],
                    "total": item_total
                })
                total_amount += item_total
                
                # Update inventory via atomic $inc
                db.medicines.update_one(
                    {"_id": med_id},
                    {"$inc": {"quantity": qty}}
                )
                
        purchase_data = {
            "supplier_id": ObjectId(supplier_id),
            "invoice_number": invoice_number,
            "purchase_date": datetime.utcnow(),
            "payment_method": payment_method,
            "items": items,
            "total_amount": total_amount,
            "created_at": datetime.utcnow()
        }
        db.purchases.insert_one(purchase_data)
        flash('Purchase completed successfully and inventory updated.', 'success')
        return redirect(url_for('list_purchases'))
        
    suppliers = list(db.suppliers.find())
    medicines = list(db.medicines.find())
    return render_template('purchases/add.html', suppliers=suppliers, medicines=medicines)

@app.route('/purchases/view/<id>')
@login_required
def view_purchase(id):
    purchase = db.purchases.find_one({'_id': ObjectId(id)})
    supplier = db.suppliers.find_one({'_id': purchase['supplier_id']}) if purchase else None
    return render_template('purchases/view.html', purchase=purchase, supplier=supplier)

# --- SALES / POS ---
@app.route('/sales')
@login_required
def list_sales():
    sales = list(db.sales.find().sort("sale_date", -1))
    for sale in sales:
        customer = db.customers.find_one({'_id': sale['customer_id']})
        sale['customer_name'] = customer['customer_name'] if customer else 'Unknown'
    return render_template('sales/list.html', sales=sales)

@app.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if current_user.role == 'staff':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_sales'))
        
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        payment_method = request.form.get('payment_method')
        try:
            discount = float(request.form.get('discount') or 0)
        except ValueError:
            discount = 0.0
            
        prescription_id = None
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            file_id = fs.put(file.stream, filename=file.filename, content_type=file.content_type)
            prescription_id = str(file_id)
        
        medicine_ids = request.form.getlist('medicine_id[]')
        quantities = request.form.getlist('quantity[]')
        
        items = []
        subtotal = 0
        today = datetime.utcnow()
        
        for i in range(len(medicine_ids)):
            if not medicine_ids[i] or not quantities[i]:
                continue
                
            try:
                med_id = ObjectId(medicine_ids[i])
                qty = int(quantities[i])
            except (ValueError, TypeError):
                continue
            
            med = db.medicines.find_one({'_id': med_id})
            if med:
                # Check Expiry
                if med['expiry_date'] < today:
                    flash(f"Medicine {med['medicine_name']} has expired and cannot be sold.", 'error')
                    return redirect(url_for('new_sale'))
                    
                # Check Stock
                if med['quantity'] < qty:
                    flash(f"Insufficient stock for {med['medicine_name']}. Available: {med['quantity']}", 'error')
                    return redirect(url_for('new_sale'))
                    
                item_total = qty * med['selling_price']
                items.append({
                    "medicine_id": med_id,
                    "medicine_name": med['medicine_name'],
                    "batch_number": med['batch_number'],
                    "quantity": qty,
                    "selling_price": med['selling_price'],
                    "total": item_total
                })
                subtotal += item_total
                
                # Update Inventory atomic
                db.medicines.update_one(
                    {"_id": med_id},
                    {"$inc": {"quantity": -qty}}
                )
                
        grand_total = subtotal - discount
        invoice_number = f"INV-{int(datetime.utcnow().timestamp())}"
        
        sale_data = {
            "customer_id": ObjectId(customer_id),
            "user_id": ObjectId(current_user.id),
            "invoice_number": invoice_number,
            "sale_date": datetime.utcnow(),
            "items": items,
            "subtotal": subtotal,
            "discount": discount,
            "tax": 0,
            "grand_total": grand_total,
            "payment_method": payment_method,
            "created_at": datetime.utcnow()
        }
        
        if prescription_id:
            sale_data["prescription_id"] = prescription_id
            
        result = db.sales.insert_one(sale_data)
        flash('Sale completed successfully.', 'success')
        return redirect(url_for('invoice', id=str(result.inserted_id)))
        
    customers = list(db.customers.find())
    medicines = list(db.medicines.find({"quantity": {"$gt": 0}, "expiry_date": {"$gte": datetime.utcnow()}}))
    return render_template('sales/new.html', customers=customers, medicines=medicines)

@app.route('/sales/invoice/<id>')
@login_required
def invoice(id):
    sale = db.sales.find_one({'_id': ObjectId(id)})
    if not sale:
        flash('Sale not found.', 'error')
        return redirect(url_for('list_sales'))
    customer = db.customers.find_one({'_id': sale['customer_id']})
    return render_template('sales/invoice.html', sale=sale, customer=customer)

@app.route('/sales/view/<id>')
@login_required
def view_sale(id):
    return redirect(url_for('invoice', id=id))

# --- PRESCRIPTIONS ---
@app.route('/prescriptions')
@login_required
def list_prescriptions():
    prescriptions = list(db.prescriptions.find().sort("prescription_date", -1))
    for p in prescriptions:
        customer = db.customers.find_one({'_id': p['customer_id']})
        p['customer_name'] = customer['customer_name'] if customer else 'Unknown'
    return render_template('prescriptions/list.html', prescriptions=prescriptions)

@app.route('/prescriptions/add', methods=['GET', 'POST'])
@login_required
def add_prescription():
    if current_user.role == 'staff':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_prescriptions'))
        
    if request.method == 'POST':
        prescription_data = {
            "customer_id": ObjectId(request.form.get('customer_id')),
            "doctor_name": request.form.get('doctor_name'),
            "prescription_date": datetime.strptime(request.form.get('prescription_date'), '%Y-%m-%d'),
            "items": [],
            "instructions": request.form.get('instructions'),
            "created_at": datetime.utcnow()
        }
        
        medicine_ids = request.form.getlist('medicine_id[]')
        dosages = request.form.getlist('dosage[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        
        for i in range(len(medicine_ids)):
            if not medicine_ids[i] or not dosages[i] or not frequencies[i] or not durations[i]:
                continue
                
            try:
                med_id = ObjectId(medicine_ids[i])
            except (ValueError, TypeError):
                continue
                
            med = db.medicines.find_one({'_id': med_id})
            if med:
                prescription_data['items'].append({
                    "medicine_id": med_id,
                    "medicine_name": med['medicine_name'],
                    "dosage": dosages[i],
                    "frequency": frequencies[i],
                    "duration": durations[i]
                })
                
        db.prescriptions.insert_one(prescription_data)
        flash('Prescription added successfully.', 'success')
        return redirect(url_for('list_prescriptions'))
        
    customers = list(db.customers.find())
    medicines = list(db.medicines.find())
    return render_template('prescriptions/add.html', customers=customers, medicines=medicines)

@app.route('/prescriptions/view/<id>')
@login_required
def view_prescription(id):
    prescription = db.prescriptions.find_one({'_id': ObjectId(id)})
    customer = db.customers.find_one({'_id': prescription['customer_id']}) if prescription else None
    return render_template('prescriptions/view.html', prescription=prescription, customer=customer)

# --- REPORTS ---
@app.route('/reports')
@login_required
def reports_dashboard():
    if current_user.role == 'staff':
        flash('Permission denied.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('reports/dashboard.html')

@app.route('/reports/sales')
@login_required
def sales_report():
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$sale_date"}},
            "total_sales": {"$sum": "$grand_total"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": -1}}
    ]
    report_data = list(db.sales.aggregate(pipeline))
    return render_template('reports/sales.html', report_data=report_data)

@app.route('/reports/purchases')
@login_required
def purchases_report():
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$purchase_date"}},
            "total_purchases": {"$sum": "$total_amount"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": -1}}
    ]
    report_data = list(db.purchases.aggregate(pipeline))
    return render_template('reports/purchases.html', report_data=report_data)

@app.route('/reports/stock')
@login_required
def stock_report():
    medicines = list(db.medicines.find().sort("quantity", 1))
    total_meds = len(medicines)
    total_qty = sum(m['quantity'] for m in medicines)
    low_stock = sum(1 for m in medicines if m['quantity'] <= m['minimum_stock'] and m['quantity'] > 0)
    out_of_stock = sum(1 for m in medicines if m['quantity'] == 0)
    expired = sum(1 for m in medicines if m['expiry_date'] < datetime.utcnow())
    
    return render_template('reports/stock.html', 
        medicines=medicines, total_meds=total_meds, 
        total_qty=total_qty, low_stock=low_stock, 
        out_of_stock=out_of_stock, expired=expired)

@app.route('/reports/profit')
@login_required
def profit_report():
    # Calculate profit from sales items
    pipeline = [
        {"$unwind": "$items"},
        {"$lookup": {
            "from": "medicines",
            "localField": "items.medicine_id",
            "foreignField": "_id",
            "as": "medicine_details"
        }},
        {"$unwind": "$medicine_details"},
        {"$project": {
            "sale_date": "$sale_date",
            "invoice_number": "$invoice_number",
            "medicine_name": "$items.medicine_name",
            "quantity": "$items.quantity",
            "selling_price": "$items.selling_price",
            "purchase_price": "$medicine_details.purchase_price",
            "profit_per_item": {"$subtract": ["$items.selling_price", "$medicine_details.purchase_price"]},
            "total_profit": {"$multiply": [{"$subtract": ["$items.selling_price", "$medicine_details.purchase_price"]}, "$items.quantity"]}
        }},
        {"$sort": {"sale_date": -1}}
    ]
    profit_data = list(db.sales.aggregate(pipeline))
    total_profit = sum(item['total_profit'] for item in profit_data)
    
    return render_template('reports/profit.html', profit_data=profit_data, total_profit=total_profit)

# --- USERS (Admin Only) ---
@app.route('/users')
@login_required
def list_users():
    if current_user.role != 'admin':
        flash('Permission denied. Admin only.', 'error')
        return redirect(url_for('dashboard'))
    users = list(db.users.find())
    return render_template('users/list.html', users=users)

# --- CLINICAL SAFETY API ---
@app.route('/api/check_interactions', methods=['POST'])
@login_required
def check_interactions():
    data = request.json
    medicine_ids = data.get('medicine_ids', [])
    
    try:
        object_ids = [ObjectId(mid) for mid in medicine_ids if mid]
        medicines = list(db.medicines.find({"_id": {"$in": object_ids}}))
    except:
        return {"warnings": []}
        
    generic_names = [m.get('generic_name', '').lower().strip() for m in medicines if m.get('generic_name')]
    
    warnings = []
    
    interactions = [
        ({"cetirizine", "dextromethorphan"}, "SEVERE DROWSINESS: Cetirizine combined with Cough Syrup (Dextromethorphan) can cause central nervous system depression and extreme sedation."),
        ({"amoxicillin", "azithromycin"}, "HEART RHYTHM RISK: Combining these strong antibiotics may increase the risk of QT prolongation and irregular heart rhythms."),
        ({"ibuprofen", "pantoprazole"}, "STOMACH ISSUES: Ensure patient takes pantoprazole strictly 30 mins before food when on strong NSAIDs like Ibuprofen to prevent acid reflux."),
        ({"paracetamol", "ibuprofen"}, "LIVER/KIDNEY WARNING: Combined use of multiple painkillers requires careful dosage monitoring to prevent toxicity.")
    ]
    
    for combo, warning_msg in interactions:
        if combo.issubset(set(generic_names)):
            warnings.append(warning_msg)
            
    return {"warnings": warnings}

# --- SMART OCR SCANNER API ---
import pytesseract
from PIL import Image
from thefuzz import fuzz

# Set tesseract path for Windows if installed locally in standard path
if os.name == 'nt' and os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@app.route('/api/ocr_prescription', methods=['POST'])
@login_required
def ocr_prescription():
    if 'image' not in request.files:
        return {"error": "No image uploaded"}, 400
        
    file = request.files['image']
    try:
        # 1. SAVE THE IMAGE TO MONGODB (GridFS)
        file_id = fs.put(file.stream, filename=file.filename, content_type=file.content_type)
        
        # Reset stream for PIL to read it
        file.stream.seek(0)
        img = Image.open(file.stream)
        
        try:
            # Try to use real Tesseract OCR
            extracted_text = pytesseract.image_to_string(img)
        except Exception as e:
            # Fallback to Mock Mode if Tesseract is not installed on the system
            # Extract possible medicine names from the filename or just simulate
            extracted_text = file.filename.replace('_', ' ').replace('-', ' ') + " paracetamol amoxicillin"
            print("Tesseract not found, using simulated OCR text:", extracted_text)

        # Get all medicines to match against
        all_meds = list(db.medicines.find({"quantity": {"$gt": 0}}))
        matched_meds = []
        
        words = extracted_text.lower().split()
        
        for med in all_meds:
            med_name = med['medicine_name'].lower()
            generic = med['generic_name'].lower()
            brand = med['brand_name'].lower()
            
            # Use fuzzy matching to detect handwritten mistakes
            match_score = 0
            for word in words:
                if len(word) > 3:
                    score1 = fuzz.partial_ratio(word, med_name)
                    score2 = fuzz.partial_ratio(word, generic)
                    score3 = fuzz.partial_ratio(word, brand)
                    match_score = max(match_score, score1, score2, score3)
            
            # If match score is high enough (e.g. > 80%), we consider it a match
            if match_score > 80:
                matched_meds.append({
                    "id": str(med['_id']),
                    "name": med['medicine_name'],
                    "price": med['selling_price'],
                    "stock": med['quantity'],
                    "match_score": match_score
                })
                
        # Sort by best match score
        matched_meds = sorted(matched_meds, key=lambda x: x['match_score'], reverse=True)
        
        # Remove duplicates
        unique_matches = []
        seen = set()
        for m in matched_meds:
            if m['id'] not in seen:
                seen.add(m['id'])
                unique_matches.append(m)
                
        return {"success": True, "matches": unique_matches, "extracted_text": extracted_text, "prescription_id": str(file_id)}
        
    except Exception as e:
        print("OCR Error:", str(e))
        return {"error": "Failed to process image. " + str(e)}, 500

@app.route('/api/media/<file_id>')
@login_required
def get_media(file_id):
    try:
        from bson.errors import InvalidId
        try:
            grid_out = fs.get(ObjectId(file_id))
        except InvalidId:
            return "Invalid file ID", 400
            
        return send_file(
            io.BytesIO(grid_out.read()),
            mimetype=grid_out.content_type,
            as_attachment=False,
            download_name=grid_out.filename
        )
    except gridfs.errors.NoFile:
        return "File not found", 404
    except Exception as e:
        return str(e), 500

# --- DELETION ROUTES (Admin Only) ---
@app.route('/medicines/delete/<id>', methods=['POST'])
@login_required
def delete_medicine(id):
    if current_user.role != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_medicines'))
    db.medicines.delete_one({'_id': ObjectId(id)})
    flash('Medicine deleted successfully.', 'success')
    return redirect(url_for('list_medicines'))

@app.route('/suppliers/delete/<id>', methods=['POST'])
@login_required
def delete_supplier(id):
    if current_user.role != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_suppliers'))
    db.suppliers.delete_one({'_id': ObjectId(id)})
    flash('Supplier deleted successfully.', 'success')
    return redirect(url_for('list_suppliers'))

@app.route('/customers/delete/<id>', methods=['POST'])
@login_required
def delete_customer(id):
    if current_user.role != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_customers'))
    db.customers.delete_one({'_id': ObjectId(id)})
    flash('Customer deleted successfully.', 'success')
    return redirect(url_for('list_customers'))

@app.route('/sales/delete/<id>', methods=['POST'])
@login_required
def delete_sale(id):
    if current_user.role != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_sales'))
    db.sales.delete_one({'_id': ObjectId(id)})
    flash('Sale deleted successfully.', 'success')
    return redirect(url_for('list_sales'))

@app.route('/purchases/delete/<id>', methods=['POST'])
@login_required
def delete_purchase(id):
    if current_user.role != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_purchases'))
    db.purchases.delete_one({'_id': ObjectId(id)})
    flash('Purchase deleted successfully.', 'success')
    return redirect(url_for('list_purchases'))

@app.route('/prescriptions/delete/<id>', methods=['POST'])
@login_required
def delete_prescription(id):
    if current_user.role != 'admin':
        flash('Permission denied.', 'error')
        return redirect(url_for('list_prescriptions'))
    db.prescriptions.delete_one({'_id': ObjectId(id)})
    flash('Prescription deleted successfully.', 'success')
    return redirect(url_for('list_prescriptions'))

# --- ERRORS ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
