"""
Firestore Database Layer for UMKM Copilot
Persistent storage for Vercel deployment
"""

import os
from datetime import datetime, timezone, date

# Firestore client (lazy init)
_firestore_client = None

def get_firestore():
    """Get Firestore client"""
    global _firestore_client
    if _firestore_client is None:
        try:
            from google.cloud import firestore
            # Try service account from env
            project_id = os.environ.get('FIRESTORE_PROJECT_ID', '')
            if project_id:
                _firestore_client = firestore.Client(project=project_id)
            else:
                # Try default credentials (Vercel with Firebase integration)
                _firestore_client = firestore.Client()
        except Exception as e:
            print(f"Firestore init error: {e}")
            _firestore_client = None
    return _firestore_client


def is_firestore_available():
    """Check if Firestore is configured"""
    return get_firestore() is not None


# ============================================================
# SHOP OPERATIONS
# ============================================================

def get_shop(shop_id='default'):
    """Get shop from Firestore"""
    fs = get_firestore()
    if not fs:
        return None
    doc = fs.collection('shops').document(str(shop_id)).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None


def create_or_update_shop(shop_id, data):
    """Create or update shop in Firestore"""
    fs = get_firestore()
    if not fs:
        return False
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    if 'created_at' not in data:
        data['created_at'] = datetime.now(timezone.utc).isoformat()
    fs.collection('shops').document(str(shop_id)).set(data, merge=True)
    return True


# ============================================================
# PRODUCT OPERATIONS
# ============================================================

def get_products(shop_id='default', active_only=True):
    """Get all products from Firestore"""
    fs = get_firestore()
    if not fs:
        return []
    query = fs.collection('shops').document(str(shop_id)).collection('products')
    if active_only:
        query = query.where('is_active', '==', True)
    docs = query.stream()
    products = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        products.append(data)
    return products


def get_product(shop_id, product_id):
    """Get single product"""
    fs = get_firestore()
    if not fs:
        return None
    doc = fs.collection('shops').document(str(shop_id)).collection('products').document(str(product_id)).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None


def create_product(shop_id, data):
    """Create product in Firestore"""
    fs = get_firestore()
    if not fs:
        return None
    data['created_at'] = datetime.now(timezone.utc).isoformat()
    data['is_active'] = data.get('is_active', True)
    ref = fs.collection('shops').document(str(shop_id)).collection('products').add(data)
    return ref[1].id


def update_product(shop_id, product_id, data):
    """Update product"""
    fs = get_firestore()
    if not fs:
        return False
    fs.collection('shops').document(str(shop_id)).collection('products').document(str(product_id)).set(data, merge=True)
    return True


def delete_product(shop_id, product_id):
    """Delete product"""
    fs = get_firestore()
    if not fs:
        return False
    fs.collection('shops').document(str(shop_id)).collection('products').document(str(product_id)).delete()
    return True


# ============================================================
# CONVERSATION OPERATIONS
# ============================================================

def save_conversation(shop_id, data):
    """Save conversation to Firestore"""
    fs = get_firestore()
    if not fs:
        return None
    data['created_at'] = datetime.now(timezone.utc).isoformat()
    ref = fs.collection('shops').document(str(shop_id)).collection('conversations').add(data)
    return ref[1].id


def get_conversations(shop_id, limit=50):
    """Get recent conversations"""
    fs = get_firestore()
    if not fs:
        return []
    docs = fs.collection('shops').document(str(shop_id)).collection('conversations')\
        .order_by('created_at', direction='DESCENDING').limit(limit).stream()
    convs = []
    for doc in docs:
        data = doc.to_dict()
        data['id'] = doc.id
        convs.append(data)
    return convs


# ============================================================
# ANALYTICS OPERATIONS
# ============================================================

def save_analytics(shop_id, date_str, data):
    """Save daily analytics"""
    fs = get_firestore()
    if not fs:
        return False
    fs.collection('shops').document(str(shop_id)).collection('analytics').document(date_str).set(data, merge=True)
    return True


def get_analytics(shop_id, days=7):
    """Get analytics for last N days"""
    fs = get_firestore()
    if not fs:
        return []
    from datetime import timedelta
    today = date.today()
    analytics = []
    for i in range(days):
        d = today - timedelta(days=i)
        doc = fs.collection('shops').document(str(shop_id)).collection('analytics').document(d.isoformat()).get()
        if doc.exists:
            data = doc.to_dict()
            data['date'] = d.isoformat()
            analytics.append(data)
    return analytics


# ============================================================
# SEED DATA
# ============================================================

def seed_firestore_data(shop_id='default'):
    """Seed Firestore with sample data"""
    fs = get_firestore()
    if not fs:
        return False
    
    # Check if already seeded
    existing = get_shop(shop_id)
    if existing:
        return True
    
    # Create shop
    shop_data = {
        'name': 'Toko MJF Endin',
        'owner_name': 'MJF Endin',
        'phone': '081283839494',
        'address': 'JL. Cempaka No.45, Kota Tangerang',
        'category': 'Retail Fashion',
        'whatsapp_number': '6281283839494',
        'open_hours': '09:00',
        'close_hours': '21:00',
        'ai_enabled': True
    }
    create_or_update_shop(shop_id, shop_data)
    
    # Create products
    products = [
        {'name': 'Kemeja Batik Pria', 'description': 'Kemeja batik motif parang, ukuran M-XL', 'price': 285000, 'stock': 25, 'category': 'Pakaian Pria', 'is_active': True},
        {'name': 'Dress Wanita Floral', 'description': 'Dress bermotif bunga, warna pastel', 'price': 350000, 'stock': 15, 'category': 'Pakaian Wanita', 'is_active': True},
        {'name': 'Jeans Slim Fit', 'description': 'Celana jeans pria, warna dark blue', 'price': 225000, 'stock': 30, 'category': 'Celana', 'is_active': True},
        {'name': 'Tas Selempang Kulit', 'description': 'Tas selempang kulit sintetis, warna coklat', 'price': 175000, 'stock': 8, 'category': 'Aksesoris', 'is_active': True},
        {'name': 'Sepatu Sneakers', 'description': 'Sneakers casual, warna putih-hitam', 'price': 450000, 'stock': 3, 'category': 'Sepatu', 'is_active': True},
        {'name': 'Jam Tangan Digital', 'description': 'Jam tangan digital, tahan air', 'price': 325000, 'stock': 12, 'category': 'Aksesoris', 'is_active': True},
        {'name': 'Topi Baseball', 'description': 'Topi baseball, bisa custom bordir', 'price': 85000, 'stock': 50, 'category': 'Aksesoris', 'is_active': True},
        {'name': 'Hoodie Oversize', 'description': 'Hoodie oversized, bahan fleece', 'price': 299000, 'stock': 0, 'category': 'Pakaian Pria', 'is_active': True},
    ]
    for p in products:
        create_product(shop_id, p)
    
    print("Firestore seeded successfully!")
    return True
