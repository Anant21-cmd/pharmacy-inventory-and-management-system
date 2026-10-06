import os
import sys
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

bcrypt = Bcrypt()

def seed_db():
    client = MongoClient(Config.MONGO_URI)
    db = client[Config.MONGO_DB_NAME]
    
    # Drop existing collections to start fresh
    collections = ['users', 'categories', 'medicines', 'suppliers', 'customers', 'purchases', 'sales', 'prescriptions']
    for coll in collections:
        db[coll].drop()

    print("Seeding Users...")
    users = [
        {
            "name": "Admin User",
            "email": "admin@pharmacy.com",
            "password": bcrypt.generate_password_hash("Admin@123").decode('utf-8'),
            "role": "admin",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Pharmacist User",
            "email": "pharmacist@pharmacy.com",
            "password": bcrypt.generate_password_hash("Pharma@123").decode('utf-8'),
            "role": "pharmacist",
            "created_at": datetime.utcnow()
        },
        {
            "name": "Staff User",
            "email": "staff@pharmacy.com",
            "password": bcrypt.generate_password_hash("Staff@123").decode('utf-8'),
            "role": "staff",
            "created_at": datetime.utcnow()
        }
    ]
    db.users.insert_many(users)

    print("Seeding Categories...")
    categories_data = [
        {"name": "Tablet", "description": "Tablet medicines"},
        {"name": "Capsule", "description": "Capsule medicines"},
        {"name": "Syrup", "description": "Liquid syrups"},
        {"name": "Cream", "description": "Topical creams"},
        {"name": "Injection", "description": "Injectables"},
    ]
    db.categories.insert_many(categories_data)

    print("Seeding Suppliers...")
    suppliers_data = [
        {"supplier_name": "ABC Medical Suppliers", "company_name": "ABC Pharma Distributors", "phone": "9876543210", "email": "abc@example.com", "address": "Chennai", "gst_number": "GST123", "created_at": datetime.utcnow()},
        {"supplier_name": "XYZ Meds", "company_name": "XYZ Corp", "phone": "9876543211", "email": "xyz@example.com", "address": "Mumbai", "gst_number": "GST124", "created_at": datetime.utcnow()},
        {"supplier_name": "Global Pharma", "company_name": "Global Ltd", "phone": "9876543212", "email": "global@example.com", "address": "Delhi", "gst_number": "GST125", "created_at": datetime.utcnow()},
        {"supplier_name": "MedLife Dist", "company_name": "MedLife", "phone": "9876543213", "email": "medlife@example.com", "address": "Bangalore", "gst_number": "GST126", "created_at": datetime.utcnow()},
        {"supplier_name": "HealthCare Sup", "company_name": "HealthCare", "phone": "9876543214", "email": "health@example.com", "address": "Hyderabad", "gst_number": "GST127", "created_at": datetime.utcnow()},
    ]
    suppliers_res = db.suppliers.insert_many(suppliers_data)
    supplier_ids = suppliers_res.inserted_ids

    print("Seeding Customers...")
    customers_data = [
        {"customer_name": "Rahul Kumar", "phone": "9876543215", "email": "rahul@example.com", "age": 25, "gender": "Male", "address": "Chennai", "created_at": datetime.utcnow()},
        {"customer_name": "Priya Sharma", "phone": "9876543216", "email": "priya@example.com", "age": 30, "gender": "Female", "address": "Mumbai", "created_at": datetime.utcnow()},
        {"customer_name": "Amit Singh", "phone": "9876543217", "email": "amit@example.com", "age": 45, "gender": "Male", "address": "Delhi", "created_at": datetime.utcnow()},
        {"customer_name": "Sneha Reddy", "phone": "9876543218", "email": "sneha@example.com", "age": 28, "gender": "Female", "address": "Bangalore", "created_at": datetime.utcnow()},
        {"customer_name": "Vikram Das", "phone": "9876543219", "email": "vikram@example.com", "age": 50, "gender": "Male", "address": "Kolkata", "created_at": datetime.utcnow()},
        {"customer_name": "Anjali Patel", "phone": "9876543220", "email": "anjali@example.com", "age": 35, "gender": "Female", "address": "Ahmedabad", "created_at": datetime.utcnow()},
        {"customer_name": "Rohan Gupta", "phone": "9876543221", "email": "rohan@example.com", "age": 40, "gender": "Male", "address": "Pune", "created_at": datetime.utcnow()},
        {"customer_name": "Neha Verma", "phone": "9876543222", "email": "neha@example.com", "age": 32, "gender": "Female", "address": "Jaipur", "created_at": datetime.utcnow()},
        {"customer_name": "Karan Malhotra", "phone": "9876543223", "email": "karan@example.com", "age": 27, "gender": "Male", "address": "Lucknow", "created_at": datetime.utcnow()},
        {"customer_name": "Pooja Joshi", "phone": "9876543224", "email": "pooja@example.com", "age": 29, "gender": "Female", "address": "Bhopal", "created_at": datetime.utcnow()},
    ]
    customers_res = db.customers.insert_many(customers_data)
    customer_ids = customers_res.inserted_ids

    print("Seeding Medicines...")
    today = datetime.utcnow()
    medicines_data = [
        {"medicine_name": "Paracetamol 500mg", "generic_name": "Paracetamol", "brand_name": "Calpol", "category": "Tablet", "dosage": "500mg", "form": "Tablet", "strength": "500mg", "manufacturer": "ABC Pharma", "supplier_id": supplier_ids[0], "batch_number": "PAR001", "purchase_price": 2.50, "selling_price": 5.00, "quantity": 150, "minimum_stock": 20, "manufacturing_date": (today - timedelta(days=100)), "expiry_date": (today + timedelta(days=700)), "prescription_required": False, "description": "Fever and pain", "created_at": today},
        {"medicine_name": "Amoxicillin 500mg", "generic_name": "Amoxicillin", "brand_name": "Amox", "category": "Capsule", "dosage": "500mg", "form": "Capsule", "strength": "500mg", "manufacturer": "XYZ Corp", "supplier_id": supplier_ids[1], "batch_number": "AMX001", "purchase_price": 8.00, "selling_price": 12.00, "quantity": 50, "minimum_stock": 30, "manufacturing_date": (today - timedelta(days=50)), "expiry_date": (today + timedelta(days=365)), "prescription_required": True, "description": "Antibiotic", "created_at": today},
        {"medicine_name": "Cetirizine 10mg", "generic_name": "Cetirizine", "brand_name": "Cetzine", "category": "Tablet", "dosage": "10mg", "form": "Tablet", "strength": "10mg", "manufacturer": "Global Ltd", "supplier_id": supplier_ids[2], "batch_number": "CET001", "purchase_price": 4.00, "selling_price": 8.00, "quantity": 100, "minimum_stock": 20, "manufacturing_date": (today - timedelta(days=200)), "expiry_date": (today + timedelta(days=10)), "prescription_required": False, "description": "Allergy", "created_at": today}, # Expiring soon
        {"medicine_name": "Azithromycin 500mg", "generic_name": "Azithromycin", "brand_name": "Azee", "category": "Tablet", "dosage": "500mg", "form": "Tablet", "strength": "500mg", "manufacturer": "MedLife", "supplier_id": supplier_ids[3], "batch_number": "AZI001", "purchase_price": 15.00, "selling_price": 25.00, "quantity": 10, "minimum_stock": 20, "manufacturing_date": (today - timedelta(days=300)), "expiry_date": (today + timedelta(days=500)), "prescription_required": True, "description": "Antibiotic", "created_at": today}, # Low stock
        {"medicine_name": "Ibuprofen 400mg", "generic_name": "Ibuprofen", "brand_name": "Brufen", "category": "Tablet", "dosage": "400mg", "form": "Tablet", "strength": "400mg", "manufacturer": "HealthCare", "supplier_id": supplier_ids[4], "batch_number": "IBU001", "purchase_price": 3.00, "selling_price": 6.00, "quantity": 200, "minimum_stock": 50, "manufacturing_date": (today - timedelta(days=150)), "expiry_date": (today + timedelta(days=600)), "prescription_required": False, "description": "Pain relief", "created_at": today},
        {"medicine_name": "Pantoprazole 40mg", "generic_name": "Pantoprazole", "brand_name": "Pan40", "category": "Tablet", "dosage": "40mg", "form": "Tablet", "strength": "40mg", "manufacturer": "ABC Pharma", "supplier_id": supplier_ids[0], "batch_number": "PAN001", "purchase_price": 5.00, "selling_price": 10.00, "quantity": 80, "minimum_stock": 30, "manufacturing_date": (today - timedelta(days=400)), "expiry_date": (today - timedelta(days=5)), "prescription_required": True, "description": "Acidity", "created_at": today}, # Expired
        {"medicine_name": "ORS", "generic_name": "Oral Rehydration Salts", "brand_name": "Electral", "category": "Powder", "dosage": "1 Sachet", "form": "Powder", "strength": "21g", "manufacturer": "XYZ Corp", "supplier_id": supplier_ids[1], "batch_number": "ORS001", "purchase_price": 15.00, "selling_price": 20.00, "quantity": 300, "minimum_stock": 50, "manufacturing_date": (today - timedelta(days=50)), "expiry_date": (today + timedelta(days=700)), "prescription_required": False, "description": "Dehydration", "created_at": today},
        {"medicine_name": "Vitamin C", "generic_name": "Ascorbic Acid", "brand_name": "Limcee", "category": "Tablet", "dosage": "500mg", "form": "Tablet", "strength": "500mg", "manufacturer": "Global Ltd", "supplier_id": supplier_ids[2], "batch_number": "VIT001", "purchase_price": 2.00, "selling_price": 4.00, "quantity": 500, "minimum_stock": 100, "manufacturing_date": (today - timedelta(days=100)), "expiry_date": (today + timedelta(days=800)), "prescription_required": False, "description": "Supplement", "created_at": today},
        {"medicine_name": "Cough Syrup", "generic_name": "Dextromethorphan", "brand_name": "Benadryl", "category": "Syrup", "dosage": "100ml", "form": "Syrup", "strength": "100ml", "manufacturer": "MedLife", "supplier_id": supplier_ids[3], "batch_number": "SYR001", "purchase_price": 40.00, "selling_price": 60.00, "quantity": 60, "minimum_stock": 20, "manufacturing_date": (today - timedelta(days=120)), "expiry_date": (today + timedelta(days=400)), "prescription_required": False, "description": "Cough relief", "created_at": today},
        {"medicine_name": "Antiseptic Cream", "generic_name": "Chlorhexidine", "brand_name": "Savlon", "category": "Cream", "dosage": "30g", "form": "Cream", "strength": "30g", "manufacturer": "HealthCare", "supplier_id": supplier_ids[4], "batch_number": "CRE001", "purchase_price": 25.00, "selling_price": 35.00, "quantity": 40, "minimum_stock": 15, "manufacturing_date": (today - timedelta(days=80)), "expiry_date": (today + timedelta(days=500)), "prescription_required": False, "description": "Wound care", "created_at": today},
    ]
    meds_res = db.medicines.insert_many(medicines_data)
    med_ids = meds_res.inserted_ids

    print("Seeding Purchases...")
    purchases_data = []
    for i in range(5):
        purchases_data.append({
            "supplier_id": supplier_ids[i],
            "invoice_number": f"PUR-{1000+i}",
            "purchase_date": today - timedelta(days=i*5),
            "payment_method": "UPI",
            "items": [
                {
                    "medicine_id": med_ids[i],
                    "medicine_name": medicines_data[i]["medicine_name"],
                    "batch_number": medicines_data[i]["batch_number"],
                    "quantity": 50,
                    "purchase_price": medicines_data[i]["purchase_price"],
                    "expiry_date": medicines_data[i]["expiry_date"],
                    "total": 50 * medicines_data[i]["purchase_price"]
                }
            ],
            "total_amount": 50 * medicines_data[i]["purchase_price"],
            "created_at": today - timedelta(days=i*5)
        })
    db.purchases.insert_many(purchases_data)

    print("Seeding Sales...")
    sales_data = []
    admin_user = db.users.find_one({"role": "admin"})
    for i in range(10):
        med = medicines_data[i]
        qty = 2
        total = qty * med["selling_price"]
        sales_data.append({
            "customer_id": customer_ids[i],
            "user_id": admin_user["_id"],
            "invoice_number": f"INV-{1000+i}",
            "sale_date": today - timedelta(days=i),
            "items": [
                {
                    "medicine_id": med_ids[i],
                    "medicine_name": med["medicine_name"],
                    "batch_number": med["batch_number"],
                    "quantity": qty,
                    "selling_price": med["selling_price"],
                    "total": total
                }
            ],
            "subtotal": total,
            "discount": 0,
            "tax": 0,
            "grand_total": total,
            "payment_method": "Cash",
            "created_at": today - timedelta(days=i)
        })
    db.sales.insert_many(sales_data)

    print("Seeding Prescriptions...")
    prescriptions_data = []
    for i in range(5):
        prescriptions_data.append({
            "customer_id": customer_ids[i],
            "doctor_name": f"Dr. Smith {i}",
            "prescription_date": today - timedelta(days=i*2),
            "items": [
                {
                    "medicine_id": med_ids[i],
                    "medicine_name": medicines_data[i]["medicine_name"],
                    "dosage": "1 tablet",
                    "frequency": "Twice daily",
                    "duration": "5 days"
                }
            ],
            "instructions": "Take after food",
            "created_at": today - timedelta(days=i*2)
        })
    db.prescriptions.insert_many(prescriptions_data)

    print("Database seeding completed successfully!")
    
    # Create Indexes
    print("Creating Indexes...")
    db.medicines.create_index([("medicine_name", 1)])
    db.medicines.create_index([("generic_name", 1)])
    db.medicines.create_index([("batch_number", 1)])
    db.purchases.create_index([("supplier_id", 1)])
    db.sales.create_index([("customer_id", 1)])
    db.sales.create_index([("invoice_number", 1)])
    db.sales.create_index([("sale_date", -1)])
    db.purchases.create_index([("purchase_date", -1)])
    print("Indexes created!")

if __name__ == "__main__":
    seed_db()
