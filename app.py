"""
UMKM Copilot — AI Business Agent for Small Businesses
Build with Gemini XPRIZE Hackathon
"""

import os
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

# ============================================================
# APP CONFIG
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'umkm-copilot-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Database: use /tmp on Vercel (ephemeral but writable), local file otherwise
_db_path = os.environ.get('DATABASE_URL', '')
if not _db_path:
    if os.path.exists('/tmp') and os.access('/tmp', os.W_OK):
        _db_path = 'sqlite:////tmp/umkm_copilot.db'
    else:
        _db_path = 'sqlite:///umkm_copilot.db'
app.config['SQLALCHEMY_DATABASE_URI'] = _db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# WhatsApp Cloud API config
WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', '')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'umkm-copilot-verify')
WHATSAPP_APP_SECRET = os.environ.get('WHATSAPP_APP_SECRET', '')

# Gemini API config
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')

db = SQLAlchemy(app)

# Import Firestore and Vision helpers
try:
    from db_firestore import is_firestore_available, get_shop as fs_get_shop, create_or_update_shop as fs_save_shop
    from db_firestore import get_products as fs_get_products, create_product as fs_create_product
    from db_firestore import update_product as fs_update_product, delete_product as fs_delete_product
    from db_firestore import save_conversation as fs_save_conversation, get_conversations as fs_get_conversations
    from db_firestore import save_analytics as fs_save_analytics, get_analytics as fs_get_analytics
    from db_firestore import seed_firestore_data, get_firestore
    HAS_FIRESTORE = is_firestore_available()
    # Test actual connection
    if HAS_FIRESTORE and get_firestore() is None:
        HAS_FIRESTORE = False
except ImportError:
    HAS_FIRESTORE = False

try:
    from vision import analyze_product_image, analyze_product_image_local, is_vision_available
    HAS_VISION = is_vision_available()
except ImportError:
    HAS_VISION = False
    def analyze_product_image_local(img): return {'ai_description': 'Vision API not configured'}

# ============================================================
# DATABASE MODELS (SQLite fallback)
# ============================================================
class Shop(db.Model):
    """UMKM shop / business profile"""
    __tablename__ = 'shops'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default='Toko UMKM')
    owner_name = db.Column(db.String(120), default='')
    phone = db.Column(db.String(30), default='')
    address = db.Column(db.Text, default='')
    category = db.Column(db.String(50), default='Retail')
    whatsapp_number = db.Column(db.String(30), default='')
    open_hours = db.Column(db.String(10), default='09:00')
    close_hours = db.Column(db.String(10), default='21:00')
    ai_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    products = db.relationship('Product', backref='shop', lazy=True, cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='shop', lazy=True, cascade='all, delete-orphan')
    analytics = db.relationship('Analytics', backref='shop', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'owner_name': self.owner_name,
            'phone': self.phone, 'address': self.address, 'category': self.category,
            'whatsapp_number': self.whatsapp_number, 'open_hours': self.open_hours,
            'close_hours': self.close_hours, 'ai_enabled': self.ai_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Product(db.Model):
    """Shop products / inventory"""
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    price = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), default='Umum')
    image_url = db.Column(db.String(500), default='')
    ai_description = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'shop_id': self.shop_id, 'name': self.name,
            'description': self.description, 'price': self.price,
            'stock': self.stock, 'category': self.category,
            'image_url': self.image_url, 'ai_description': self.ai_description,
            'is_active': self.is_active
        }


class Conversation(db.Model):
    """WhatsApp conversation logs"""
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=False)
    customer_name = db.Column(db.String(120), default='')
    message_in = db.Column(db.Text, nullable=False)
    message_out = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), default='general')
    response_time_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'shop_id': self.shop_id,
            'customer_phone': self.customer_phone, 'customer_name': self.customer_name,
            'message_in': self.message_in, 'message_out': self.message_out,
            'intent': self.intent, 'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Analytics(db.Model):
    """Daily analytics per shop"""
    __tablename__ = 'analytics'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    total_conversations = db.Column(db.Integer, default=0)
    total_inquiries = db.Column(db.Integer, default=0)
    total_orders = db.Column(db.Integer, default=0)
    products_viewed = db.Column(db.Integer, default=0)
    avg_response_time_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'date': self.date.isoformat(),
            'total_conversations': self.total_conversations,
            'total_inquiries': self.total_inquiries,
            'total_orders': self.total_orders,
            'products_viewed': self.products_viewed,
            'avg_response_time_ms': self.avg_response_time_ms
        }


# ============================================================
# AI AGENT (GEMINI)
# ============================================================
class UMKGeminiAgent:
    """AI Agent powered by Google Gemini for UMKM customer service"""
    
    SYSTEM_PROMPT = """Anda adalah asisten AI untuk toko UMKM (Usaha Mikro, Kecil, dan Menengah) di Indonesia.

TUGAS ANDA:
1. Menjawab pertanyaan customer tentang produk (harga, stok, deskripsi)
2. Membantu customer memilih produk yang sesuai
3. Memberikan informasi toko (jam buka, alamat, cara pesan)
4. Membantu proses pemesanan sederhana
5. Memberikan rekomendasi produk berdasarkan kebutuhan customer

GAYA BICARA:
- Ramah, profesional, tapi tidak kaku
- Gunakan bahasa Indonesia yang mudah dipahami
- Gunakan emoji secukupnya untuk membuat percakapan lebih hangat
- Singkat dan langsung ke inti

INFORMASI TOKO:
- Toko akan memberikan data produk dan informasi toko
- Gunakan data tersebut untuk menjawab pertanyaan
- Jika tidak tahu jawabannya, katakan dengan jujur

CONTOH RESPONS:
- "Halo Kak! 😊 Ada yang bisa kami bantu?"
- "Untuk [produk], harganya Rp [harga]. Stok masih ada [jumlah] unit ya!"
- "Produk yang cocok untuk Kak [nama] adalah [rekomendasi]. Mau dilihat detailnya?"
- "Untuk pemesanan, Kakak bisa langsung chat kami dengan format: PESAN [nama produk]"

BENTUK RESPONS:
- Selalu dalam format teks biasa (bukan HTML atau Markdown)
- Gunakan bullet point jika perlu
- Sertakan harga dalam format Rupiah: Rp X.XXX.XXX
- Maksimal 3-4 baris per respons untuk WhatsApp
"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = GEMINI_MODEL
        # Rate limiter
        self._call_times = []
        self._quota_exhausted = False
        self._quota_exhausted_at = 0
        self._cooldown_seconds = 62
    
    def _check_rate_limit(self):
        """Check if we should skip Gemini API call"""
        import time
        now = time.time()
        
        if self._quota_exhausted:
            if now - self._quota_exhausted_at < self._cooldown_seconds:
                return False
            else:
                self._quota_exhausted = False
                self._call_times = []
        
        self._call_times = [t for t in self._call_times if now - t < 60]
        
        if len(self._call_times) >= 12:
            return False
        
        self._call_times.append(now)
        return True
    
    def _mark_quota_exhausted(self):
        """Mark quota as exhausted"""
        import time
        self._quota_exhausted = True
        self._quota_exhausted_at = time.time()
    
    def _build_context(self, shop, products):
        """Build context from shop data for the AI"""
        product_list = "\n".join([
            f"- {p['name']}: Rp {p['price']:,.0f} (Stok: {p['stock']}) - {p['category']}"
            for p in products[:20]
        ])
        
        return f"""
DATA TOKO:
- Nama: {shop['name']}
- Pemilik: {shop.get('owner_name', '')}
- Kategori: {shop.get('category', '')}
- Alamat: {shop.get('address', '')}
- Telepon: {shop.get('phone', '')}
- Jam Buka: {shop.get('open_hours', '09:00')} - {shop.get('close_hours', '21:00')}
- WhatsApp: {shop.get('whatsapp_number', '')}

PRODUK TERSEDIA:
{product_list if product_list else "Belum ada produk terdaftar"}

TOTAL PRODUK: {len(products)}
"""
    
    def _fallback_response(self, message, shop, products):
        """Smart fallback when Gemini API is unavailable"""
        import random
        msg_lower = message.lower()
        
        # Store info
        if any(k in msg_lower for k in ['alamat', 'lokasi', 'kontak', 'jam buka', 'buka jam', 'toko buka', 'tutup', 'jam berapa']):
            return f"📍 {shop['name']}\n🏠 {shop.get('address', '')}\n🕐 Jam: {shop.get('open_hours', '09:00')} - {shop.get('close_hours', '21:00')}\n📞 {shop.get('phone', '')}\n📱 WA: {shop.get('whatsapp_number', '')}"
        
        # Order
        if any(k in msg_lower for k in ['pesan', 'order', 'beli', 'checkout']):
            for p in products:
                if any(word in msg_lower for word in p['name'].lower().split()):
                    if p['stock'] > 0:
                        return f"✅ Pesanan {p['name']} sudah kami catat!\n💰 Harga: Rp {p['price']:,.0f}\n📦 Stok: {p['stock']} unit\n\nUntuk konfirmasi, chat langsung:\n📱 WA: {shop.get('whatsapp_number', '')}\n\nTerima kasih Kak! 😊"
                    else:
                        return f"Maaf Kak, {p['name']} lagi kosong 😔\nKami bisa kabarin kalau sudah restok ya?"
            return "Produk apa yang mau dipesan Kak? 😊\nContoh: PESAN [nama produk]"
        
        # Product list
        if any(k in msg_lower for k in ['produk', 'apa saja', 'daftar', 'catalog', 'katalog', 'list']):
            plist = "\n".join([f"• {p['name']} - Rp {p['price']:,.0f} (Stok: {p['stock']})" for p in products[:6]])
            return f"Produk {shop['name']} Kak:\n{plist}\n\nMau tanya yang mana? 😊"
        
        # Greeting
        if any(k in msg_lower for k in ['halo', 'hai', 'hello', 'hi', 'pagi', 'siang', 'sore', 'malam']):
            if any(k in msg_lower for k in ['produk', 'apa', 'ada']):
                plist = "\n".join([f"• {p['name']} - Rp {p['price']:,.0f} (Stok: {p['stock']})" for p in products[:6]])
                return f"Produk {shop['name']} Kak:\n{plist}\n\nMau tanya yang mana? 😊"
            return f"Halo Kak! 👋 Selamat datang di {shop['name']}. Ada yang bisa kami bantu hari ini? 😊"
        
        # Recommendation
        if any(k in msg_lower for k in ['rekomendasi', 'saran', 'recommend', 'cocok', 'murah', 'bagus']):
            category_map = {
                'aksesoris': ['Aksesoris', 'Jam', 'Topi', 'Tas'],
                'pakaian': ['Pakaian', 'Pria', 'Wanita', 'Kemeja', 'Dress', 'Hoodie'],
                'sepatu': ['Sepatu', 'Sneakers', 'Footwear'],
                'celana': ['Celana', 'Jeans'],
            }
            filtered = products
            for cat_key, cat_vals in category_map.items():
                if cat_key in msg_lower:
                    filtered = [p for p in products if any(cv.lower() in p.get('category', '').lower() for cv in cat_vals)]
                    break
            
            if any(k in msg_lower for k in ['murah', 'terjangkau', 'hemat']):
                filtered.sort(key=lambda p: p['price'])
            
            if filtered:
                p = filtered[0]
                return f"Rekomendasi: {p['name']} Rp {p['price']:,.0f} 🔥\n{p.get('description', '')}\nStok: {p['stock']} unit\nMau lihat detail? 😊"
            return "Tanya produk spesifik ya Kak, nanti kami bantu carikan yang cocok! 😊"
        
        # Price inquiry
        for p in products:
            if any(word in msg_lower for word in p['name'].lower().split()):
                if any(k in msg_lower for k in ['harga', 'berapa', 'price', 'murah', 'mahal']):
                    return f"Untuk {p['name']}, harganya Rp {p['price']:,.0f} ya Kak. Stok masih ada {p['stock']} unit! 😊"
                if any(k in msg_lower for k in ['stok', 'stock', 'ada', 'habis']):
                    if p['stock'] > 0:
                        return f"{p['name']} masih ada {p['stock']} unit Kak. Harga Rp {p['price']:,.0f}. Mau diorder? 😉"
                    else:
                        return f"Maaf Kak, {p['name']} lagi kosong 😔 Kami bisa kabarin kalau sudah restok ya?"
                return f"{p['name']} - Rp {p['price']:,.0f} (Stok: {p['stock']}). Mau yang mana Kak? 😊"
        
        if any(k in msg_lower for k in ['harga', 'berapa', 'price']):
            p = random.choice(products) if products else None
            if p:
                return f"Contoh: {p['name']} Rp {p['price']:,.0f}. Tanya produk spesifik ya Kak! 😊"
            return "Bisa tanya harga produk tertentu ya Kak. Contoh: 'Berapa harga [nama produk]?' 😊"
        
        if any(k in msg_lower for k in ['stok', 'stock', 'ada', 'habis', 'kosong']):
            return "Produk apa yang ingin dicek stoknya Kak? 😊"
        
        return f"Makasih Kak! 😊 Ada yang bisa kami bantu soal produk atau info {shop['name']}?"
    
    def _call_gemini(self, user_message, context, history=None):
        """Call Gemini API with rate limiter and fallback"""
        if not self._check_rate_limit():
            return None
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{context}\n\nPESAN CUSTOMER: {user_message}"
            
            if history:
                chat = model.start_chat(history=history)
                response = chat.send_message(full_prompt)
            else:
                response = model.generate_content(full_prompt)
            
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'quota' in err_str.lower() or 'ResourceExhausted' in type(e).__name__:
                self._mark_quota_exhausted()
            return None
    
    def handle_message(self, message, shop_data, products_data):
        """Process incoming message"""
        import time
        start_time = time.time()
        
        intent = self._detect_intent(message, products_data)
        
        context = self._build_context(shop_data, products_data)
        response = self._call_gemini(message, context)
        
        if not response:
            response = self._fallback_response(message, shop_data, products_data)
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            'response': response,
            'intent': intent,
            'response_time_ms': response_time
        }
    
    def _detect_intent(self, message, products):
        """Simple intent detection based on keywords"""
        msg_lower = message.lower()
        
        if any(k in msg_lower for k in ['alamat', 'jam buka', 'lokasi', 'toko', 'kontak', 'buka jam', 'jam berapa']):
            return 'store_info'
        
        if any(k in msg_lower for k in ['pesan', 'order', 'beli', 'checkout', 'bayar']):
            return 'order'
        
        for p in products:
            if p['name'].lower() in msg_lower:
                return 'product_inquiry'
        
        if any(k in msg_lower for k in ['harga', 'berapa', 'price', 'murah', 'mahal']):
            return 'price_inquiry'
        
        if any(k in msg_lower for k in ['stok', 'stock', 'ada', 'habis', 'kosong']):
            return 'stock_inquiry'
        
        if any(k in msg_lower for k in ['halo', 'hai', 'hello', 'hi', 'pagi', 'siang', 'sore', 'malam']):
            return 'greeting'
        
        return 'general'


# Initialize AI Agent
ai_agent = UMKGeminiAgent()


# ============================================================
# DATABASE LAYER (Firestore + SQLite fallback)
# ============================================================

def get_or_create_shop():
    """Get existing shop or create default one"""
    shop = Shop.query.first()
    if not shop:
        shop = Shop(
            name='Toko MJF Endin', owner_name='MJF Endin', phone='081283839494',
            address='JL. Cempaka No.45, Kota Tangerang', category='Retail',
            whatsapp_number='6281283839494', open_hours='09:00', close_hours='21:00',
            ai_enabled=True
        )
        db.session.add(shop)
        db.session.commit()
    return shop


def db_get_shop_dict():
    """Get shop as dict (Firestore or SQLite)"""
    if HAS_FIRESTORE:
        shop = fs_get_shop('default')
        if shop:
            return shop
    shop = get_or_create_shop()
    return shop.to_dict()


def db_get_products_list(shop_id='default'):
    """Get products as list of dicts"""
    if HAS_FIRESTORE:
        products = fs_get_products(shop_id)
        if products:
            return products
    shop = get_or_create_shop()
    products = Product.query.filter_by(shop_id=shop.id, is_active=True).all()
    return [p.to_dict() for p in products]


def db_save_conversation(shop_id, data):
    """Save conversation"""
    if HAS_FIRESTORE:
        fs_save_conversation(shop_id, data)
    shop = get_or_create_shop()
    conv = Conversation(
        shop_id=shop.id,
        customer_phone=data.get('customer_phone', ''),
        customer_name=data.get('customer_name', ''),
        message_in=data.get('message_in', ''),
        message_out=data.get('message_out', ''),
        intent=data.get('intent', 'general'),
        response_time_ms=data.get('response_time_ms', 0)
    )
    db.session.add(conv)
    db.session.commit()


def db_get_conversations(limit=50):
    """Get conversations"""
    if HAS_FIRESTORE:
        convs = fs_get_conversations('default', limit)
        if convs:
            return convs
    shop = get_or_create_shop()
    convs = Conversation.query.filter_by(shop_id=shop.id).order_by(Conversation.created_at.desc()).limit(limit).all()
    return [c.to_dict() for c in convs]


# ============================================================
# WHATSAPP WEBHOOK HANDLER
# ============================================================
@app.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """WhatsApp Cloud API webhook endpoint"""
    
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
            return challenge, 200
        else:
            return 'Verification failed', 403
    
    elif request.method == 'POST':
        data = request.get_json()
        
        try:
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                return 'OK', 200
            
            msg = messages[0]
            phone = msg.get('from', '')
            text = msg.get('text', {}).get('body', '')
            msg_type = msg.get('type', '')
            
            if msg_type != 'text' or not text:
                return 'OK', 200
            
            shop_data = db_get_shop_dict()
            products_data = db_get_products_list()
            
            contacts = value.get('contacts', [])
            customer_name = contacts[0].get('profile', {}).get('name', '') if contacts else ''
            
            result = ai_agent.handle_message(text, shop_data, products_data)
            
            db_save_conversation(shop_data.get('id', 'default'), {
                'customer_phone': phone,
                'customer_name': customer_name,
                'message_in': text,
                'message_out': result['response'],
                'intent': result['intent'],
                'response_time_ms': result['response_time_ms']
            })
            
            _send_whatsapp_message(phone, result['response'])
            
            return 'OK', 200
            
        except Exception as e:
            print(f"Webhook error: {e}")
            return 'Error', 500


def _send_whatsapp_message(phone, message):
    """Send message via WhatsApp Cloud API"""
    import requests
    
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        return
    
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone,
        'type': 'text',
        'text': {'body': message}
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"WhatsApp send exception: {e}")


# ============================================================
# DASHBOARD ROUTES
# ============================================================
@app.route('/')
def index():
    """Main dashboard"""
    try:
        shop_data = db_get_shop_dict()
        products_data = db_get_products_list()
        
        from datetime import date as date_type
        today = date_type.today()
        week_ago = today - timedelta(days=7)
        
        total_products = len([p for p in products_data if p.get('is_active', True)])
        low_stock = len([p for p in products_data if p.get('is_active', True) and p.get('stock', 0) <= 5])
        
        convs = db_get_conversations(30)
        week_conversations = sum(1 for c in convs if str(c.get('created_at', '')) >= week_ago.isoformat())
        today_conversations = sum(1 for c in convs if str(c.get('created_at', '')).startswith(today.isoformat()))
        
        return render_template('dashboard.html', 
            shop=shop_data, 
            total_products=total_products,
            low_stock=low_stock,
            week_conversations=week_conversations,
            today_conversations=today_conversations,
            recent_conversations=convs[:5],
            week_orders=0,
            ai_status='Aktif' if shop_data.get('ai_enabled') else 'Nonaktif',
            db_status='Firestore' if HAS_FIRESTORE else 'SQLite',
            vision_status='Active' if HAS_VISION else 'Local Fallback'
        )
    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return f"Dashboard Error: {e}", 500


# ============================================================
# PRODUCTS ROUTES
# ============================================================
@app.route('/products')
def products_page():
    """Products management"""
    shop = get_or_create_shop()
    products = Product.query.filter_by(shop_id=shop.id).order_by(Product.created_at.desc()).all()
    return render_template('products.html', shop=shop, products=products)


@app.route('/products/create', methods=['GET', 'POST'])
def product_create():
    """Create new product"""
    shop = get_or_create_shop()
    
    if request.method == 'POST':
        try:
            # Handle image upload
            image_url = ''
            ai_desc = ''
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # Save to /tmp for now (would be Cloud Storage in production)
                    import uuid
                    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                    filename = f"{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join('/tmp', filename)
                    file.save(filepath)
                    image_url = f"/tmp/{filename}"
                    
                    # Analyze with Cloud Vision if available
                    if HAS_VISION:
                        with open(filepath, 'rb') as f:
                            img_bytes = f.read()
                        analysis = analyze_product_image(image_bytes=img_bytes)
                        ai_desc = analysis.get('ai_description', '')
                    else:
                        with open(filepath, 'rb') as f:
                            img_bytes = f.read()
                        analysis = analyze_product_image_local(img_bytes)
                        ai_desc = analysis.get('ai_description', '')
            
            product = Product(
                shop_id=shop.id,
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                price=float(request.form.get('price', 0)),
                stock=int(request.form.get('stock', 0)),
                category=request.form.get('category', 'Umum'),
                image_url=image_url,
                ai_description=ai_desc,
                is_active=True
            )
            db.session.add(product)
            db.session.commit()
            flash('Produk berhasil ditambahkan!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('products_page'))
    
    return render_template('product_form.html', shop=shop, product=None)


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def product_edit(product_id):
    """Edit product"""
    shop = get_or_create_shop()
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name', product.name)
            product.description = request.form.get('description', product.description)
            product.price = float(request.form.get('price', product.price))
            product.stock = int(request.form.get('stock', product.stock))
            product.category = request.form.get('category', product.category)
            
            # Handle new image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    import uuid
                    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
                    filename = f"{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join('/tmp', filename)
                    file.save(filepath)
                    product.image_url = f"/tmp/{filename}"
                    
                    if HAS_VISION:
                        with open(filepath, 'rb') as f:
                            img_bytes = f.read()
                        analysis = analyze_product_image(image_bytes=img_bytes)
                        product.ai_description = analysis.get('ai_description', '')
            
            db.session.commit()
            flash('Produk berhasil diupdate!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('products_page'))
    
    return render_template('product_form.html', shop=shop, product=product)


@app.route('/products/<int:product_id>/delete', methods=['POST'])
def product_delete(product_id):
    """Delete product"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash('Produk berhasil dihapus!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('products_page'))


# ============================================================
# ANALYZE IMAGE API (for AJAX)
# ============================================================
@app.route('/api/analyze-image', methods=['POST'])
def api_analyze_image():
    """Analyze uploaded image with Cloud Vision"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    
    file = request.files['image']
    if not file or not file.filename:
        return jsonify({'error': 'No image selected'}), 400
    
    try:
        img_bytes = file.read()
        
        if HAS_VISION:
            result = analyze_product_image(image_bytes=img_bytes)
        else:
            result = analyze_product_image_local(img_bytes)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# CONVERSATIONS ROUTE
# ============================================================
@app.route('/conversations')
def conversations_page():
    """View conversations"""
    shop = get_or_create_shop()
    convs = db_get_conversations(50)
    return render_template('conversations.html', shop=shop, conversations=convs)


# ============================================================
# ANALYTICS ROUTE
# ============================================================
@app.route('/analytics')
def analytics_page():
    """View analytics"""
    shop = get_or_create_shop()
    convs = db_get_conversations(100)
    
    from datetime import date as date_type
    today = date_type.today()
    
    # Calculate stats from conversations
    total_convs = len(convs)
    intents = {}
    for c in convs:
        intent = c.get('intent', 'general')
        intents[intent] = intents.get(intent, 0) + 1
    
    return render_template('analytics.html', 
        shop=shop, 
        conversations=convs,
        total_conversations=total_convs,
        intents=intents
    )


# ============================================================
# SETTINGS ROUTE
# ============================================================
@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """Shop settings"""
    shop = get_or_create_shop()
    
    if request.method == 'POST':
        try:
            shop.name = request.form.get('name', shop.name)
            shop.owner_name = request.form.get('owner_name', shop.owner_name)
            shop.phone = request.form.get('phone', shop.phone)
            shop.address = request.form.get('address', shop.address)
            shop.category = request.form.get('category', shop.category)
            shop.whatsapp_number = request.form.get('whatsapp_number', shop.whatsapp_number)
            shop.open_hours = request.form.get('open_hours', shop.open_hours)
            shop.close_hours = request.form.get('close_hours', shop.close_hours)
            shop.ai_enabled = request.form.get('ai_enabled') == 'on'
            db.session.commit()
            flash('Pengaturan berhasil disimpan!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('settings_page'))
    
    return render_template('settings.html', shop=shop)


# ============================================================
# DEMO ROUTE
# ============================================================
@app.route('/demo')
def demo_page():
    """Demo chat page"""
    return render_template('demo.html')


@app.route('/demo/test', methods=['POST'])
def demo_test():
    """Test the AI agent from demo page"""
    data = request.get_json()
    message = data.get('message', 'Halo')
    
    shop_data = db_get_shop_dict()
    products_data = db_get_products_list()
    
    result = ai_agent.handle_message(message, shop_data, products_data)
    return jsonify(result)


# ============================================================
# API ENDPOINTS
# ============================================================
@app.route('/api/products', methods=['GET'])
def api_products():
    """API: List products"""
    products = db_get_products_list()
    return jsonify(products)


@app.route('/api/products', methods=['POST'])
def api_product_create():
    """API: Create product"""
    data = request.get_json()
    shop = get_or_create_shop()
    
    try:
        product = Product(
            shop_id=shop.id,
            name=data.get('name', ''),
            description=data.get('description', ''),
            price=float(data.get('price', 0)),
            stock=int(data.get('stock', 0)),
            category=data.get('category', 'Umum'),
            image_url=data.get('image_url', ''),
            ai_description=data.get('ai_description', ''),
            is_active=True
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'success': True, 'product': product.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_product_delete(product_id):
    """API: Delete product"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/stats')
def api_stats():
    """API: Dashboard stats"""
    shop = get_or_create_shop()
    products = Product.query.filter_by(shop_id=shop.id, is_active=True).all()
    convs = Conversation.query.filter_by(shop_id=shop.id).order_by(Conversation.created_at.desc()).limit(100).all()
    
    from datetime import date as date_type
    today = date_type.today()
    week_ago = today - timedelta(days=7)
    
    return jsonify({
        'total_products': len(products),
        'low_stock': len([p for p in products if p.stock <= 5]),
        'week_conversations': len([c for c in convs if c.created_at and c.created_at.date() >= week_ago]),
        'today_conversations': len([c for c in convs if c.created_at and c.created_at.date() == today])
    })


# ============================================================
# SYSTEM INFO
# ============================================================
@app.route('/api/system')
def api_system():
    """API: System status"""
    return jsonify({
        'firestore': HAS_FIRESTORE,
        'vision': HAS_VISION,
        'gemini_key_set': bool(GEMINI_API_KEY),
        'whatsapp_configured': bool(WHATSAPP_TOKEN),
        'db_path': _db_path
    })


# ============================================================
# SEED DATA
# ============================================================
def seed_data():
    """Create sample data for demo"""
    if Shop.query.first():
        return
    
    shop = Shop(
        name='Toko MJF Endin',
        owner_name='MJF Endin',
        phone='081283839494',
        address='JL. Cempaka No.45, Kota Tangerang',
        category='Retail Fashion',
        whatsapp_number='6281283839494',
        open_hours='09:00',
        close_hours='21:00',
        ai_enabled=True
    )
    db.session.add(shop)
    db.session.flush()
    
    products = [
        Product(shop_id=shop.id, name='Kemeja Batik Pria', description='Kemeja batik motif parang, ukuran M-XL', price=285000, stock=25, category='Pakaian Pria'),
        Product(shop_id=shop.id, name='Dress Wanita Floral', description='Dress bermotif bunga, warna pastel', price=350000, stock=15, category='Pakaian Wanita'),
        Product(shop_id=shop.id, name='Jeans Slim Fit', description='Celana jeans pria, warna dark blue', price=225000, stock=30, category='Celana'),
        Product(shop_id=shop.id, name='Tas Selempang Kulit', description='Tas selempang kulit sintetis, warna coklat', price=175000, stock=8, category='Aksesoris'),
        Product(shop_id=shop.id, name='Sepatu Sneakers', description='Sneakers casual, warna putih-hitam', price=450000, stock=3, category='Sepatu'),
        Product(shop_id=shop.id, name='Jam Tangan Digital', description='Jam tangan digital, tahan air', price=325000, stock=12, category='Aksesoris'),
        Product(shop_id=shop.id, name='Topi Baseball', description='Topi baseball, bisa custom bordir', price=85000, stock=50, category='Aksesoris'),
        Product(shop_id=shop.id, name='Hoodie Oversize', description='Hoodie oversized, bahan fleece', price=299000, stock=0, category='Pakaian Pria'),
    ]
    for p in products:
        db.session.add(p)
    
    # Sample conversations
    sample_convs = [
        Conversation(shop_id=shop.id, customer_phone='628111111111', customer_name='Andi',
            message_in='Halo, ada kemeja batik?', message_out='Halo Kak Andi! 😊 Ada Kak, Kemeja Batik Pria motif parang Rp 285.000. Stok masih 25 unit. Mau lihat detailnya?',
            intent='product_inquiry', response_time_ms=1200),
        Conversation(shop_id=shop.id, customer_phone='628222222222', customer_name='Siti',
            message_in='Berapa harga tas selempang?', message_out='Halo Kak! 😊 Tas Selempang Kulit harganya Rp 175.000. Ada warna coklat, bahannya kulit sintetis yang bagus. Mau pesan?',
            intent='price_inquiry', response_time_ms=950),
        Conversation(shop_id=shop.id, customer_phone='628333333333', customer_name='Rina',
            message_in='Sepatu sneakers masih ada?', message_out='Halo Kak Rina! 👟 Sepatu Sneakers masih ada 3 unit Kak. Harga Rp 450.000. Warna putih-hitam, cocok buat casual. Mau diambil hari ini?',
            intent='stock_inquiry', response_time_ms=880),
        Conversation(shop_id=shop.id, customer_phone='628555555555', customer_name='Maya',
            message_in='Toko buka jam berapa?', message_out='Halo Kak Maya! 🏪 Toko MJF Endin buka setiap hari jam 09:00 - 21:00 WIB. Alamat di JL. Cempaka No.45, Kota Tangerang. Datang ya Kak!',
            intent='store_info', response_time_ms=750),
    ]
    for c in sample_convs:
        db.session.add(c)
    
    db.session.commit()
    print("SQLite seed data created!")


# ============================================================
# INITIALIZE
# ============================================================
try:
    with app.app_context():
        db.create_all()
        seed_data()
        
        # Seed Firestore if available
        if HAS_FIRESTORE:
            try:
                seed_firestore_data('default')
            except Exception as e:
                print(f"Firestore seed error: {e}")
except Exception as e:
    print(f"Init error: {e}")


# ============================================================
# STATIC FILE SERVING (for Vercel)
# ============================================================
@app.route('/static/<path:filename>')
def serve_static(filename):
    return app.send_static_file(filename)


# For Vercel
if __name__ == '__main__':
    app.run(debug=True)
