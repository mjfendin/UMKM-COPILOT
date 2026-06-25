"""
UMKM Copilot — AI Business Agent for Small Businesses
Build with Gemini XPRIZE Hackathon
"""

import os
import json
import hashlib
import hmac
import base64
import re
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from translations import t as _t

# ============================================================
# APP CONFIG
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'umkm-copilot-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

@app.template_global()
def t(key):
    """Template global for translations"""
    return _t(key, session.get('lang', 'id'))



# ============================================================
# AUTH SYSTEM — Admin Login
# ============================================================
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'umkm2026')

def login_required(f):
    """Protect admin routes — redirect to /login if not authenticated"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(request.args.get('next', url_for('index')))
        flash('Password salah!', 'error')
    return render_template('login.html', lang=session.get('lang', 'id'))

@app.route('/logout')
def logout():
    """Logout admin"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('login_page'))

@app.route('/lang/<lang_code>')
def set_language(lang_code):
    """Switch language (id/en) — redirects back to previous page"""
    if lang_code in ('id', 'en'):
        session['lang'] = lang_code
    # Use 'next' param if provided, else referrer, else home
    next_url = request.args.get('next', request.referrer or url_for('index'))
    return redirect(next_url)

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
    
    SYSTEM_PROMPT = """You are an AI assistant for a UMKM (small business) store in Indonesia.

LANGUAGE RULES (CRITICAL):
- ALWAYS respond in the SAME LANGUAGE as the customer's message.
- If the customer writes in Bahasa Indonesia → respond in Bahasa Indonesia.
- If the customer writes in English → respond in English.
- NEVER mix languages in a single response.
- The system language setting may be ID or EN — always match the CUSTOMER's message language.

TASKS:
1. Answer customer questions about products (price, stock, description)
2. Help customers choose suitable products
3. Provide store information (opening hours, address, how to order)
4. Help with simple ordering process
5. Provide product recommendations based on customer needs

TONE:
- Friendly, professional, not stiff
- Use emojis to make conversation warmer
- Keep responses short and to the point (max 3-4 lines for WhatsApp)

STORE INFORMATION:
- Store will provide product data and store info
- Use that data to answer questions
- If you don't know the answer, say so honestly

EXAMPLE RESPONSES (Indonesian):
- "Halo Kak! 😊 Ada yang bisa kami bantu?"
- "Untuk [produk], harganya Rp [harga]. Stok masih ada [jumlah] unit ya!"
- "Produk yang cocok adalah [rekomendasi]. Mau dilihat detailnya?"

EXAMPLE RESPONSES (English):
- "Hello! 😊 How can we help you today?"
- "For [product], the price is Rp [price]. We have [qty] units in stock!"
- "I recommend [product]. Would you like to see the details?"
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
    
    def _is_english(self, message):
        """Detect if message is primarily English — uses word boundaries"""
        msg_lower = message.lower()
        words = re.findall(r'[a-z]+', msg_lower)
        id_words = {'halo', 'hai', 'pagi', 'siang', 'sore', 'malam', 'berapa', 'harga', 'stok',
                    'produk', 'pesan', 'beli', 'toko', 'buka', 'tutup', 'alamat', 'lokasi',
                    'rekomendasi', 'saran', 'murah', 'bagus', 'yang', 'ini', 'itu', 'ada', 'apa',
                    'siapa', 'dimana', 'kapan', 'kenapa', 'bagaimana', 'mau', 'dong',
                    'ya', 'nih', 'kah', 'kak', 'mbak', 'mas', 'pak', 'tolong', 'terima',
                    'kasih', 'makasih', 'permisi', 'maaf', 'sedang', 'lagi', 'saya', 'kami',
                    'belum', 'masih', 'sudah', 'akan', 'bisa', 'tidak', 'bukan',
                    'juga', 'hanya', 'untuk', 'dengan', 'dari', 'ke', 'dan', 'atau',
                    'saja', 'aja', 'lho', 'kok', 'deh'}
        id_count = sum(1 for w in words if w in id_words)
        if id_count > 0:
            return False
        eng_words = {'hello', 'hey', 'price', 'stock', 'products', 'product', 'recommend', 'cheap', 'good',
                     'how', 'what', 'where', 'when', 'have', 'available', 'order', 'buy', 'cost',
                     'show', 'tell', 'store', 'shop', 'open', 'close', 'recommendation',
                     'anyone', 'something', 'else', 'about', 'help', 'thanks', 'please',
                     'check', 'want', 'need', 'look', 'see', 'list', 'all', 'each'}
        eng_count = sum(1 for w in words if w in eng_words)
        return eng_count >= 1


    def _fallback_response(self, message, shop, products):
        """Smart fallback when Gemini API is unavailable — bilingual"""
        import random
        msg_lower = message.lower()
        is_en = self._is_english(message)

        # Store info
        store_info_id = f"📍 {shop['name']}\n🏠 {shop.get('address', '')}\n🕐 Jam: {shop.get('open_hours', '09:00')} - {shop.get('close_hours', '21:00')}\n📞 {shop.get('phone', '')}\n📱 WA: {shop.get('whatsapp_number', '')}"
        store_info_en = f"📍 {shop['name']}\n🏠 {shop.get('address', '')}\n🕐 Hours: {shop.get('open_hours', '09:00')} - {shop.get('close_hours', '21:00')}\n📞 {shop.get('phone', '')}\n📱 WA: {shop.get('whatsapp_number', '')}"
        if any(k in msg_lower for k in ['alamat', 'lokasi', 'kontak', 'jam buka', 'buka jam', 'toko buka', 'tutup', 'jam berapa', 'address', 'location', 'hours', 'open', 'close', 'where']):
            return store_info_en if is_en else store_info_id

        # Order
        if any(k in msg_lower for k in ['pesan', 'order', 'beli', 'checkout', 'buy']):
            for p in products:
                if any(word in msg_lower for word in p['name'].lower().split()):
                    if p['stock'] > 0:
                        if is_en:
                            return f"✅ Order for {p['name']} recorded!\n💰 Price: Rp {p['price']:,.0f}\n📦 Stock: {p['stock']} units\n\nFor confirmation, chat directly:\n📱 WA: {shop.get('whatsapp_number', '')}\n\nThank you! 😊"
                        else:
                            return f"✅ Pesanan {p['name']} sudah kami catat!\n💰 Harga: Rp {p['price']:,.0f}\n📦 Stok: {p['stock']} unit\n\nUntuk konfirmasi, chat langsung:\n📱 WA: {shop.get('whatsapp_number', '')}\n\nTerima kasih Kak! 😊"
                    else:
                        if is_en:
                            return f"Sorry, {p['name']} is out of stock 😔\nWe'll let you know when it's restocked!"
                        else:
                            return f"Maaf Kak, {p['name']} lagi kosong 😔\nKami bisa kabarin kalau sudah restok ya?"
            return "What product would you like to order? 😊\nExample: ORDER [product name]" if is_en else "Produk apa yang mau dipesan Kak? 😊\nContoh: PESAN [nama produk]"

        # Product list
        if any(k in msg_lower for k in ['produk', 'apa saja', 'daftar', 'catalog', 'katalog', 'list', 'products', 'all']):
            plist = "\n".join([f"• {p['name']} - Rp {p['price']:,.0f} (Stock: {p['stock']})" if is_en else f"• {p['name']} - Rp {p['price']:,.0f} (Stok: {p['stock']})" for p in products[:6]])
            if is_en:
                return f"Products at {shop['name']}:\n{plist}\n\nWhich one interests you? 😊"
            else:
                return f"Produk {shop['name']} Kak:\n{plist}\n\nMau tanya yang mana? 😊"

        # Greeting — use word-boundary matching (avoid 'hi' matching 'shirt')
        greeting_words = {'halo', 'hai', 'hello', 'hi', 'hey', 'pagi', 'siang', 'sore', 'malam'}
        msg_words = set(re.findall(r'[a-z]+', msg_lower))
        has_greeting = bool(greeting_words & msg_words) or any(phrase in msg_lower for phrase in ['good morning', 'good afternoon', 'good evening'])
        if has_greeting:
            if msg_words & {'produk', 'apa', 'ada', 'product', 'show', 'what'}:
                plist = "\n".join([f"• {p['name']} - Rp {p['price']:,.0f} (Stock: {p['stock']})" if is_en else f"• {p['name']} - Rp {p['price']:,.0f} (Stok: {p['stock']})" for p in products[:6]])
                if is_en:
                    return f"Products at {shop['name']}:\n{plist}\n\nWhich one interests you? 😊"
                else:
                    return f"Produk {shop['name']} Kak:\n{plist}\n\nMau tanya yang mana? 😊"
            if is_en:
                return f"Hello! 👋 Welcome to {shop['name']}. How can we help you today? 😊"
            else:
                return f"Halo Kak! 👋 Selamat datang di {shop['name']}. Ada yang bisa kami bantu hari ini? 😊"

        # Recommendation
        if any(k in msg_lower for k in ['rekomendasi', 'saran', 'recommend', 'cocok', 'murah', 'bagus', 'suggest', 'best', 'cheap', 'good']):
            category_map = {
                'aksesoris': ['Aksesoris', 'Jam', 'Topi', 'Tas', 'accessories', 'watch', 'hat', 'bag'],
                'pakaian': ['Pakaian', 'Pria', 'Wanita', 'Kemeja', 'Dress', 'Hoodie', 'clothing', 'shirt'],
                'sepatu': ['Sepatu', 'Sneakers', 'Footwear', 'shoes'],
                'celana': ['Celana', 'Jeans', 'pants'],
            }
            filtered = products
            for cat_key, cat_vals in category_map.items():
                if cat_key in msg_lower:
                    filtered = [p for p in products if any(cv.lower() in p.get('category', '').lower() for cv in cat_vals)]
                    break

            if any(k in msg_lower for k in ['murah', 'terjangkau', 'hemat', 'cheap', 'budget', 'affordable']):
                filtered.sort(key=lambda p: p['price'])

            if filtered:
                p = filtered[0]
                if is_en:
                    return f"Recommendation: {p['name']} Rp {p['price']:,.0f} 🔥\n{p.get('description', '')}\nStock: {p['stock']} units\nWant to see details? 😊"
                else:
                    return f"Rekomendasi: {p['name']} Rp {p['price']:,.0f} 🔥\n{p.get('description', '')}\nStok: {p['stock']} unit\nMau lihat detail? 😊"
            return "Ask about a specific product, and we'll help you find the right one! 😊" if is_en else "Tanya produk spesifik ya Kak, nanti kami bantu carikan yang cocok! 😊"

        # Price inquiry
        for p in products:
            if any(word in msg_lower for word in p['name'].lower().split()):
                if any(k in msg_lower for k in ['harga', 'berapa', 'price', 'murah', 'mahal', 'cost']):
                    if is_en:
                        return f"For {p['name']}, the price is Rp {p['price']:,.0f}. We have {p['stock']} units in stock! 😊"
                    else:
                        return f"Untuk {p['name']}, harganya Rp {p['price']:,.0f} ya Kak. Stok masih ada {p['stock']} unit! 😊"
                stock_kw = {'stok', 'stock', 'habis', 'available', 'tersedia'}
                if stock_kw & msg_words or 'ada' in msg_words:
                    if p['stock'] > 0:
                        if is_en:
                            return f"{p['name']} has {p['stock']} units available. Price: Rp {p['price']:,.0f}. Want to order? 😉"
                        else:
                            return f"{p['name']} masih ada {p['stock']} unit Kak. Harga Rp {p['price']:,.0f}. Mau diorder? 😉"
                    else:
                        if is_en:
                            return f"Sorry, {p['name']} is out of stock 😔 We'll let you know when restocked!"
                        else:
                            return f"Maaf Kak, {p['name']} lagi kosong 😔 Kami bisa kabarin kalau sudah restok ya?"
                if is_en:
                    return f"{p['name']} - Rp {p['price']:,.0f} (Stock: {p['stock']}). Which one would you like? 😊"
                else:
                    return f"{p['name']} - Rp {p['price']:,.0f} (Stok: {p['stock']}). Mau yang mana Kak? 😊"

        if any(k in msg_lower for k in ['harga', 'berapa', 'price', 'cost']):
            p = random.choice(products) if products else None
            if p:
                return f"Example: {p['name']} Rp {p['price']:,.0f}. Ask about a specific product! 😊" if is_en else f"Contoh: {p['name']} Rp {p['price']:,.0f}. Tanya produk spesifik ya Kak! 😊"
            return "Ask about a specific product price. Example: 'How much is [product name]?' 😊" if is_en else "Bisa tanya harga produk tertentu ya Kak. Contoh: 'Berapa harga [nama produk]?' 😊"

        if stock_kw & msg_words or 'ada' in msg_words:
            return "Which product would you like to check stock for? 😊" if is_en else "Produk apa yang ingin dicek stoknya Kak? 😊"
        
        return ("Thank you! 😊 Anything else we can help with about products or store info?" if is_en else f"Makasih Kak! 😊 Ada yang bisa kami bantu soal produk atau info {shop['name']}?")
    
    def _call_gemini(self, user_message, context, history=None):
        """Call Gemini API with rate limiter and fallback"""
        if not self._check_rate_limit():
            return None
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            
            # Detect if customer message is English (use word boundaries)
            msg_lower = user_message.lower()
            words = re.findall(r'[a-z]+', msg_lower)
            _id_set = {'halo', 'hai', 'pagi', 'siang', 'sore', 'malam', 'berapa', 'harga', 'stok',
                        'produk', 'pesan', 'beli', 'toko', 'buka', 'tutup', 'alamat', 'lokasi',
                        'rekomendasi', 'saran', 'murah', 'bagus', 'yang', 'ini', 'itu', 'ada', 'apa',
                        'siapa', 'dimana', 'kapan', 'kenapa', 'bagaimana', 'mau', 'dong', 'ya', 'nih',
                        'kah', 'kak', 'mbak', 'mas', 'pak', 'tolong', 'terima', 'kasih', 'makasih',
                        'permisi', 'maaf', 'sedang', 'lagi', 'saya', 'kami', 'belum', 'masih', 'sudah'}
            _en_set = {'hello', 'hey', 'price', 'stock', 'product', 'recommend', 'how', 'what', 'where',
                       'have', 'available', 'order', 'buy', 'store', 'shop', 'open', 'close', 'want',
                       'do', 'you', 'show', 'please', 'need', 'about', 'help', 'check', 'good'}
            id_count = sum(1 for w in words if w in _id_set)
            en_count = sum(1 for w in words if w in _en_set)
            is_en_msg = id_count == 0 and en_count >= 1
            
            if is_en_msg:
                lang_instruction = (
                    "\\n\\n=== LANGUAGE RULE ==="
                    "\\nThe customer message is in ENGLISH. You MUST respond ENTIRELY in ENGLISH."
                    "\\nDo NOT use Indonesian words like 'Kak', 'ya', 'nih', 'dong'."
                    "\\nUse English equivalents: 'Hello', 'Sure', 'Here you go', 'Thank you'."
                    "\\nProduct names (e.g. Kemeja Batik Pria) can stay as-is since they are proper names."
                    "\\nALL other text MUST be in English."
                )
            else:
                lang_instruction = "\\n\\nIMPORTANT: The customer message is in Bahasa Indonesia. Respond in Bahasa Indonesia. Use polite forms like 'Kak', 'ya', 'nih'."

            full_prompt = f"{self.SYSTEM_PROMPT}{lang_instruction}\n\n{context}\n\nCUSTOMER MESSAGE: {user_message}"
            
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



@app.route('/evidence/<path:filename>')
def serve_evidence(filename):
    """Serve evidence files for Devpost"""
    evidence_dir = os.path.join(os.path.dirname(__file__), 'evidence')
    filepath = os.path.join(evidence_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        from flask import Response
        return Response(content, mimetype='application/json')
    return jsonify({'error': 'File not found'}), 404

@app.route('/evidence')
def evidence_index():
    """Evidence index page"""
    evidence_dir = os.path.join(os.path.dirname(__file__), 'evidence')
    files = os.listdir(evidence_dir) if os.path.exists(evidence_dir) else []
    return jsonify({'files': files, 'base_url': '/evidence/'})


@app.route('/push-to-github', methods=['GET', 'POST'])
def push_to_github():
    """Push all project files to GitHub via browser — no terminal needed.
    Token: browser → Vercel server → GitHub API. Never enters LLM context.
    """
    import urllib.request as _urlreq
    import urllib.error as _urlerr
    from concurrent.futures import ThreadPoolExecutor
    import base64 as _b64

    if request.method == 'GET':
        return '''<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Push ke GitHub — UMKM Copilot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#0f0f0f;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{max-width:520px;width:100%;background:#1a1a2e;border-radius:16px;padding:36px;box-shadow:0 8px 32px rgba(0,0,0,.4)}
h1{font-size:22px;margin-bottom:6px}
.sub{color:#888;font-size:13px;margin-bottom:20px}
.steps{margin:0 0 20px 18px;font-size:13px;color:#999;line-height:1.8}
.steps b{color:#ccc}
.steps a{color:#4CAF50;text-decoration:none}
.steps a:hover{text-decoration:underline}
input{width:100%;padding:14px;background:#16213e;border:1px solid #333;border-radius:8px;color:#fff;font-size:15px;margin-bottom:14px;font-family:monospace}
input:focus{outline:none;border-color:#4CAF50}
.btn{width:100%;padding:14px;background:#4CAF50;border:none;border-radius:8px;color:#fff;font-size:15px;font-weight:700;cursor:pointer;transition:background .2s}
.btn:hover{background:#45a049}
.btn:disabled{background:#333;cursor:not-allowed}
#status{margin-top:16px;padding:14px;border-radius:8px;display:none;font-size:13px;line-height:1.7;word-break:break-all}
.ok{display:block!important;background:#1b4332;border:1px solid #2d6a4f;color:#95d5b2}
.err{display:block!important;background:#3d1f1f;border:1px solid #6b2727;color:#f5a3a3}
.wait{display:block!important;background:#1a1a2e;border:1px solid #333;color:#aaa}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #4CAF50;border-top-color:transparent;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
code{background:#16213e;padding:2px 6px;border-radius:4px;font-size:12px}
</style>
</head>
<body>
<div class="card">
<h1>\U0001f4e6 Push ke GitHub</h1>
<p class="sub">Upload semua file project ke GitHub — tanpa terminal</p>
<ol class="steps">
<li>Buka <a href="https://github.com/settings/tokens" target="_blank">github.com/settings/tokens</a></li>
<li>Klik <b>"Generate new token (classic)"</b></li>
<li>Nama: <b>umkm-push</b>, Expiry: <b>7 days</b></li>
<li>Checklist: <b>\u2611 repo</b> (Full control of private repositories)</li>
<li>Klik <b>Generate token</b> \u2192 Copy token</li>
<li>Paste token di bawah, klik Push</li>
</ol>
<form id="f">
<input type="password" id="tok" placeholder="ghp_xx...xxxx" required autocomplete="off" spellcheck="false">
<button class="btn" type="submit" id="btn">\U0001f680 Push ke GitHub</button>
</form>
<div id="status"></div>
</div>
<script>
document.getElementById('f').onsubmit=async e=>{
e.preventDefault();
const b=document.getElementById('btn'),s=document.getElementById('status'),t=document.getElementById('tok').value;
b.disabled=true;b.textContent='\u23f3 Pushing...';
s.className='wait';s.style.display='block';
s.innerHTML='<span class=spinner></span> Mengirim ke GitHub... Tunggu 10\u201330 detik';
try{
const r=await fetch('/push-to-github',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'github_token='+encodeURIComponent(t)});
const j=await r.json();
if(j.success){
s.className='ok';
s.innerHTML='\u2705 Berhasil! <b>'+j.files_uploaded+'</b> file di-push.<br>Commit: <code>'+j.commit_sha+'</code><br><a href="'+j.repo_url+'" target="_blank" style="color:#95d5b2">Buka GitHub \u2192</a>';
}else{
s.className='err';s.innerHTML='\u274c '+j.error;
}
}catch(x){s.className='err';s.innerHTML='\u274c Network error: '+x.message}
b.disabled=false;b.textContent='\U0001f680 Push ke GitHub';
};
</script>
</body>
</html>'''

    # ---- POST: receive token and push via GitHub API ----
    token = (request.form.get('github_token') or '').strip()
    if not token:
        return jsonify(success=False, error='Token kosong'), 400

    owner, repo_name = 'mjfendin', 'UMKM-COPILOT'
    API = 'https://api.github.com'

    def _gh(method, path, data=None):
        url = f'{API}{path}'
        hdrs = {'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'UMKM-Copilot'}
        body = json.dumps(data).encode() if data else None
        req = _urlreq.Request(url, data=body, headers=hdrs, method=method)
        try:
            with _urlreq.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except _urlerr.HTTPError as e:
            return {'error': f'HTTP {e.code}: {e.read().decode()[:300]}'}
        except Exception as e:
            return {'error': str(e)}

    # 1) Locate project root
    here = os.path.dirname(os.path.abspath(__file__))
    proj = os.path.dirname(here)

    # 2) Collect all text files
    skip_dirs = {'.git', '__pycache__', '.hermes', 'node_modules', '.vercel',
                 'venv', '.venv', '.cache', 'instance', 'static/gen'}
    skip_ext = ('.pyc', '.pyo', '.db', '.zip', '.bundle')
    file_list = []

    for dp, dns, fns in os.walk(proj):
        dns[:] = [d for d in dns if d not in skip_dirs and not d.startswith('.')]
        for fn in fns:
            if fn.startswith('.') or fn.endswith(skip_ext):
                continue
            fp = os.path.join(dp, fn)
            rp = os.path.relpath(fp, proj)
            try:
                raw = open(fp, 'rb').read()
                if len(raw) > 1_500_000:
                    continue
                raw.decode('utf-8')
                file_list.append((rp, _b64.b64encode(raw).decode()))
            except (UnicodeDecodeError, IOError):
                pass

    if not file_list:
        return jsonify(success=False, error='Tidak ada file ditemukan'), 400

    # 3) Get current HEAD
    ref = _gh('GET', f'/repos/{owner}/{repo_name}/git/refs/heads/main')
    branch = 'main'
    if 'error' in ref:
        ref = _gh('GET', f'/repos/{owner}/{repo_name}/git/refs/heads/master')
        branch = 'master'
    if 'error' in ref:
        return jsonify(success=False, error=f'Repo tidak bisa diakses: {ref.get("error")}')
    base_sha = ref['object']['sha']

    # 4) Create blobs (parallel, 8 workers)
    def _mkblob(item):
        rp, b64c = item
        return rp, _gh('POST', f'/repos/{owner}/{repo_name}/git/blobs',
                       {'content': b64c, 'encoding': 'base64'})

    tree_items, uploaded, errors = [], 0, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for rp, res in pool.map(_mkblob, file_list):
            if 'sha' in res:
                tree_items.append({'path': rp, 'mode': '100644',
                                   'type': 'blob', 'sha': res['sha']})
                uploaded += 1
            else:
                errors.append(f'{rp}: {res.get("error","?")}')

    # 5) Create tree -> commit -> update ref
    tree = _gh('POST', f'/repos/{owner}/{repo_name}/git/trees',
               {'tree': tree_items, 'base_tree': base_sha})
    if 'sha' not in tree:
        return jsonify(success=False, error=f'Tree gagal: {tree.get("error")}')

    commit = _gh('POST', f'/repos/{owner}/{repo_name}/git/commits',
                 {'message': f'Web push: {uploaded} files via UMKM Copilot',
                  'tree': tree['sha'], 'parents': [base_sha]})
    if 'sha' not in commit:
        return jsonify(success=False, error=f'Commit gagal: {commit.get("error")}')

    _gh('PATCH', f'/repos/{owner}/{repo_name}/git/refs/heads/{branch}',
        {'sha': commit['sha'], 'force': False})

    return jsonify(success=True, files_uploaded=uploaded,
                   commit_sha=commit['sha'][:7],
                   errors=errors[:5],
                   repo_url=f'https://github.com/{owner}/{repo_name}')


@app.route('/debug/whatsapp')
def debug_whatsapp():
    """Debug: Check WhatsApp config (admin only)"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({
        'token_set': bool(os.environ.get('WHATSAPP_TOKEN')),
        'token_length': len(os.environ.get('WHATSAPP_TOKEN', '')),
        'phone_id': os.environ.get('WHATSAPP_PHONE_NUMBER_ID', ''),
        'verify_token': os.environ.get('WHATSAPP_VERIFY_TOKEN', ''),
        'business_account_id': os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', ''),
    })


@app.route('/debug/test-send')
def test_send_message():
    """Test: send WhatsApp message using stored token"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'unauthorized'}), 401
    
    import requests
    token = os.environ.get('WHATSAPP_TOKEN', '')
    phone_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    
    if not token or not phone_id:
        return jsonify({'error': 'missing config', 'token_set': bool(token), 'phone_id': phone_id})
    
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": "6281283839494",
        "type": "text",
        "text": {"body": "✅ Test dari UMKM Copilot! Token berfungsi."}
    }
    
    resp = requests.post(url, headers=headers, json=data)
    return jsonify(resp.json())

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
@login_required
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
            vision_status='Active' if HAS_VISION else 'Local Fallback',
            lang=session.get('lang', 'id')
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
@login_required
def products_page():
    """Products management"""
    shop = get_or_create_shop()
    products = Product.query.filter_by(shop_id=shop.id).order_by(Product.created_at.desc()).all()
    return render_template('products.html', shop=shop, products=products, lang=session.get('lang', 'id'))


@app.route('/products/create', methods=['GET', 'POST'])
@login_required
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
    
    return render_template('product_form.html', shop=shop, product=None, lang=session.get('lang', 'id'))


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
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
    
    return render_template('product_form.html', shop=shop, product=product, lang=session.get('lang', 'id'))


@app.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
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
@login_required
def conversations_page():
    """View conversations"""
    shop = get_or_create_shop()
    convs = db_get_conversations(50)
    return render_template('conversations.html', shop=shop, conversations=convs, lang=session.get('lang', 'id'))


# ============================================================
# ANALYTICS ROUTE
# ============================================================
@app.route('/analytics')
@login_required
def analytics_page():
    """View analytics — computes daily_data and intent_counts from real conversations"""
    shop = get_or_create_shop()
    convs = db_get_conversations(200)
    
    from datetime import date as date_type, timedelta
    today = date_type.today()
    
    # --- Daily data (last 7 days) ---
    daily_map = {}
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        daily_map[d.strftime('%d %b')] = {'date': d.strftime('%d %b'), 'conversations': 0, 'inquiries': 0, 'orders': 0}
    
    for c in convs:
        try:
            ts = c.get('created_at', '') or c.get('timestamp', '')
            if ts:
                conv_date = str(ts)[:10]  # YYYY-MM-DD
                from datetime import datetime as dt
                d_obj = dt.strptime(conv_date, '%Y-%m-%d').date()
                key = d_obj.strftime('%d %b')
                if key in daily_map:
                    daily_map[key]['conversations'] += 1
                    intent = c.get('intent', 'general')
                    if intent in ('price_inquiry', 'stock_inquiry', 'product_inquiry'):
                        daily_map[key]['inquiries'] += 1
                    if intent == 'order' or 'pesan' in c.get('message', '').lower() or 'order' in c.get('message', '').lower():
                        daily_map[key]['orders'] += 1
        except Exception:
            pass
    
    daily_data = list(daily_map.values())
    
    # --- Intent counts ---
    intents = {}
    for c in convs:
        intent = c.get('intent', 'general')
        intents[intent] = intents.get(intent, 0) + 1
    intent_counts = sorted(intents.items(), key=lambda x: -x[1])
    
    # --- AI performance (avg response time) ---
    times = [c.get('response_time_ms', 0) for c in convs if c.get('response_time_ms', 0) > 0]
    avg_time = round(sum(times) / len(times) / 1000, 1) if times else 0
    
    return render_template('analytics.html',
        shop=shop, 
        daily_data=daily_data,
        intent_counts=intent_counts,
        avg_response_time=avg_time,
        lang=session.get('lang', 'id')
    )


# ============================================================
# SETTINGS ROUTE
# ============================================================
@app.route('/settings', methods=['GET', 'POST'])
@login_required
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
    
    return render_template('settings.html', shop=shop, lang=session.get('lang', 'id'))


# ============================================================
# DEMO ROUTE
# ============================================================
@app.route('/demo')
def demo_page():
    """Demo chat page"""
    # Support both session and URL parameter for language
    lang = request.args.get('lang', session.get('lang', 'id'))
    if lang in ('id', 'en'):
        session['lang'] = lang
    return render_template('demo.html', lang=lang)


@app.route('/demo/test', methods=['POST'])
def demo_test():
    """Test the AI agent from demo page — saves conversation for analytics"""
    data = request.get_json()
    message = data.get('message', 'Halo')
    lang = data.get('lang', session.get('lang', 'id'))
    
    shop_data = db_get_shop_dict()
    products_data = db_get_products_list()
    
    result = ai_agent.handle_message(message, shop_data, products_data)
    
    # Save conversation for analytics
    try:
        shop = get_or_create_shop()
        db_save_conversation(shop.id, {
            'customer_phone': 'demo',
            'customer_name': 'Demo User',
            'message_in': message,
            'message_out': result.get('response', ''),
            'intent': result.get('intent', 'general'),
            'response_time_ms': result.get('response_time_ms', 0)
        })
    except Exception:
        pass  # Don't fail the request if save fails
    
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
