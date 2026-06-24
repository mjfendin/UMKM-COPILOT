"""
UMKM Copilot — AI Business Agent for Small Businesses
Build with Gemini XPRIZE Hackathon
"""

import os
import json
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps

# ============================================================
# APP CONFIG
# ============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'umkm-copilot-secret-key-change-in-production')

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
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash-lite')

db = SQLAlchemy(app)

# ============================================================
# DATABASE MODELS
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
        self._cooldown_seconds = 62  # Reset every 62s
    
    def _check_rate_limit(self):
        """Check if we should skip Gemini API call"""
        import time
        now = time.time()
        
        # Auto-recovery: if quota was exhausted, try again after cooldown
        if self._quota_exhausted:
            if now - self._quota_exhausted_at < self._cooldown_seconds:
                return False  # Skip API call
            else:
                self._quota_exhausted = False
                self._call_times = []
                print("Rate limiter: cooldown expired, retrying Gemini API")
        
        # Clean old timestamps (older than 60s)
        self._call_times = [t for t in self._call_times if now - t < 60]
        
        # Free tier: ~15 RPM, keep 3 buffer
        if len(self._call_times) >= 12:
            return False
        
        self._call_times.append(now)
        return True
    
    def _mark_quota_exhausted(self):
        """Mark quota as exhausted"""
        import time
        self._quota_exhausted = True
        self._quota_exhausted_at = time.time()
        print("Rate limiter: Gemini API quota exhausted, switching to fallback")
    
    def _build_context(self, shop, products):
        """Build context from shop data for the AI"""
        product_list = "\n".join([
            f"- {p.name}: Rp {p.price:,.0f} (Stok: {p.stock}) - {p.category}"
            for p in products[:20]
        ])
        
        return f"""
DATA TOKO:
- Nama: {shop.name}
- Pemilik: {shop.owner_name}
- Kategori: {shop.category}
- Alamat: {shop.address}
- Telepon: {shop.phone}
- Jam Buka: {shop.open_hours} - {shop.close_hours}
- WhatsApp: {shop.whatsapp_number}

PRODUK TERSEDIA:
{product_list if product_list else "Belum ada produk terdaftar"}

TOTAL PRODUK: {len(products)}
"""
    
    def _fallback_response(self, message, shop, products):
        """Smart fallback when Gemini API is unavailable"""
        import random
        msg_lower = message.lower()
        
        # Store info (check FIRST)
        if any(k in msg_lower for k in ['alamat', 'lokasi', 'kontak', 'jam buka', 'buka jam', 'toko buka', 'tutup', 'jam berapa']):
            return f"📍 {shop.name}\n🏠 {shop.address}\n🕐 Jam: {shop.open_hours} - {shop.close_hours}\n📞 {shop.phone}\n📱 WA: {shop.whatsapp_number}"
        
        # Order
        if any(k in msg_lower for k in ['pesan', 'order', 'beli', 'checkout']):
            for p in products:
                if any(word in msg_lower for word in p.name.lower().split()):
                    if p.stock > 0:
                        return f"✅ Pesanan {p.name} sudah kami catat!\n💰 Harga: Rp {p.price:,.0f}\n📦 Stok: {p.stock} unit\n\nUntuk konfirmasi, chat langsung:\n📱 WA: {shop.whatsapp_number or shop.phone}\n\nTerima kasih Kak! 😊"
                    else:
                        return f"Maaf Kak, {p.name} lagi kosong 😔\nKami bisa kabarin kalau sudah restok ya?"
            return "Produk apa yang mau dipesan Kak? 😊\nContoh: PESAN [nama produk]"
        
        # Product list (check BEFORE greeting)
        if any(k in msg_lower for k in ['produk', 'apa saja', 'daftar', 'catalog', 'katalog', 'list']):
            plist = "\n".join([f"• {p.name} - Rp {p.price:,.0f} (Stok: {p.stock})" for p in products[:6]])
            return f"Produk {shop.name} Kak:\n{plist}\n\nMau tanya yang mana? 😊"
        
        # Greeting (AFTER product check)
        if any(k in msg_lower for k in ['halo', 'hai', 'hello', 'hi', 'pagi', 'siang', 'sore', 'malam']):
            # If also mentions product, show products
            if any(k in msg_lower for k in ['produk', 'apa', 'ada']):
                plist = "\n".join([f"• {p.name} - Rp {p.price:,.0f} (Stok: {p.stock})" for p in products[:6]])
                return f"Produk {shop.name} Kak:\n{plist}\n\nMau tanya yang mana? 😊"
            return f"Halo Kak! 👋 Selamat datang di {shop.name}. Ada yang bisa kami bantu hari ini? 😊"
        
        # Recommendation
        if any(k in msg_lower for k in ['rekomendasi', 'saran', 'recommend', 'cocok']):
            p = random.choice(products) if products else None
            if p:
                return f"Rekomendasi: {p.name} Rp {p.price:,.0f} 🔥\n{p.description}\nMau lihat detail? 😊"
            return "Tanya produk spesifik ya Kak, nanti kami bantu carikan yang cocok! 😊"
        
        # Price inquiry - match specific product
        for p in products:
            if any(word in msg_lower for word in p.name.lower().split()):
                if any(k in msg_lower for k in ['harga', 'berapa', 'price', 'murah', 'mahal']):
                    return f"Untuk {p.name}, harganya Rp {p.price:,.0f} ya Kak. Stok masih ada {p.stock} unit! 😊"
                if any(k in msg_lower for k in ['stok', 'stock', 'ada', 'habis']):
                    if p.stock > 0:
                        return f"{p.name} masih ada {p.stock} unit Kak. Harga Rp {p.price:,.0f}. Mau diorder? 😉"
                    else:
                        return f"Maaf Kak, {p.name} lagi kosong 😔 Kami bisa kabarin kalau sudah restok ya?"
                return f"{p.name} - Rp {p.price:,.0f} (Stok: {p.stock}). Mau yang mana Kak? 😊"
        
        # Generic price inquiry
        if any(k in msg_lower for k in ['harga', 'berapa', 'price']):
            p = random.choice(products) if products else None
            if p:
                return f"Contoh: {p.name} Rp {p.price:,.0f}. Tanya produk spesifik ya Kak! 😊"
            return "Bisa tanya harga produk tertentu ya Kak. Contoh: 'Berapa harga [nama produk]?' 😊"
        
        # Stock inquiry
        if any(k in msg_lower for k in ['stok', 'stock', 'ada', 'habis', 'kosong']):
            return "Produk apa yang ingin dicek stoknya Kak? 😊"
        
        # Default
        return f"Makasih Kak! 😊 Ada yang bisa kami bantu soal produk atau info {shop.name}?"
    
    def _call_gemini(self, user_message, context, history=None):
        """Call Gemini API with rate limiter and fallback"""
        # Check rate limit
        if not self._check_rate_limit():
            print("Rate limiter: skipping Gemini API call, using fallback")
            return None  # Signal to use fallback
        
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
            print(f"Gemini API error: {type(e).__name__}: {err_str[:200]}")
            
            # Detect quota exhaustion
            if '429' in err_str or 'quota' in err_str.lower() or 'ResourceExhausted' in type(e).__name__:
                self._mark_quota_exhausted()
            
            return None  # Signal to use fallback
    
    def handle_message(self, message, shop_id):
        """Process incoming WhatsApp message"""
        import time
        start_time = time.time()
        
        shop = Shop.query.get(shop_id)
        if not shop or not shop.ai_enabled:
            return {
                'response': 'Maaf, layanan AI belum aktif untuk toko ini.',
                'intent': 'error',
                'response_time_ms': 0
            }
        
        products = Product.query.filter_by(shop_id=shop_id, is_active=True).all()
        
        # Detect intent
        intent = self._detect_intent(message, products)
        
        # Try Gemini API first
        context = self._build_context(shop, products)
        response = self._call_gemini(message, context)
        
        # Fallback to local responses if Gemini fails
        if not response:
            response = self._fallback_response(message, shop, products)
        
        response_time = int((time.time() - start_time) * 1000)
        
        return {
            'response': response,
            'intent': intent,
            'response_time_ms': response_time
        }
    
    def _detect_intent(self, message, products):
        """Simple intent detection based on keywords"""
        msg_lower = message.lower()
        
        # Store info (check first)
        if any(k in msg_lower for k in ['alamat', 'jam buka', 'lokasi', 'toko', 'kontak', 'buka jam', 'jam berapa']):
            return 'store_info'
        
        # Order
        if any(k in msg_lower for k in ['pesan', 'order', 'beli', 'checkout', 'bayar']):
            return 'order'
        
        for p in products:
            if p.name.lower() in msg_lower:
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
# WHATSAPP WEBHOOK HANDLER
# ============================================================
@app.route('/webhook', methods=['GET', 'POST'])
def whatsapp_webhook():
    """WhatsApp Cloud API webhook endpoint"""
    
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
            print(f"Webhook verified! Challenge: {challenge}")
            return challenge, 200
        else:
            return 'Verification failed', 403
    
    elif request.method == 'POST':
        # Handle incoming messages
        data = request.get_json()
        
        try:
            # Parse WhatsApp message structure
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
            
            # Only handle text messages for MVP
            if msg_type != 'text' or not text:
                return 'OK', 200
            
            # Find which shop this phone number belongs to
            shop = Shop.query.filter_by(whatsapp_number=phone).first()
            if not shop:
                # Default to first shop for testing
                shop = get_or_create_shop()
            
            if not shop:
                return 'OK', 200
            
            # Get customer name from contacts
            contacts = value.get('contacts', [])
            customer_name = contacts[0].get('profile', {}).get('name', '') if contacts else ''
            
            # Process with AI
            result = ai_agent.handle_message(text, shop.id)
            
            # Log conversation
            conv = Conversation(
                shop_id=shop.id,
                customer_phone=phone,
                customer_name=customer_name,
                message_in=text,
                message_out=result['response'],
                intent=result['intent'],
                response_time_ms=result['response_time_ms']
            )
            db.session.add(conv)
            
            # Update analytics - use naive date for SQLite
            from datetime import date as date_type
            today = date_type.today()
            analytics = Analytics.query.filter_by(shop_id=shop.id, date=today).first()
            if not analytics:
                analytics = Analytics(shop_id=shop.id, date=today)
                db.session.add(analytics)
            analytics.total_conversations += 1
            if result['intent'] in ['product_inquiry', 'price_inquiry', 'stock_inquiry']:
                analytics.total_inquiries += 1
            if result['intent'] == 'order':
                analytics.total_orders += 1
            
            db.session.commit()
            
            # Send reply via WhatsApp Cloud API
            _send_whatsapp_message(phone, result['response'])
            
            return 'OK', 200
            
        except Exception as e:
            print(f"Webhook error: {e}")
            return 'Error', 500


def _send_whatsapp_message(phone, message):
    """Send message via WhatsApp Cloud API"""
    import requests
    
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print(f"[DRY RUN] Would send to {phone}: {message[:100]}...")
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
        if resp.status_code != 200:
            print(f"WhatsApp send error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"WhatsApp send exception: {e}")


# ============================================================
# HELPER: ensure shop exists
# ============================================================
def get_or_create_shop():
    """Get existing shop or create default one"""
    shop = Shop.query.first()
    if not shop:
        shop = Shop(
            name='Toko MJF Endin', owner_name='MJF Endin', phone='081283839494',
            address='JL. Cempaka No.45, Kota Tangerang', category='Retail',
            whatsapp_number='6281283839494', ai_enabled=True
        )
        db.session.add(shop)
        db.session.commit()
    return shop


# ============================================================
# DASHBOARD ROUTES
# ============================================================
@app.route('/')
def index():
    """Main dashboard"""
    shop = get_or_create_shop()
    
    # Get stats - use naive dates for SQLite compatibility
    from datetime import date as date_type
    today = date_type.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    total_products = Product.query.filter_by(shop_id=shop.id, is_active=True).count()
    low_stock = Product.query.filter(
        Product.shop_id == shop.id,
        Product.is_active == True,
        Product.stock <= 5
    ).count()
    
    today_analytics = Analytics.query.filter_by(shop_id=shop.id, date=today).first()
    week_conversations = db.session.query(db.func.sum(Analytics.total_conversations)).filter(
        Analytics.shop_id == shop.id,
        Analytics.date >= week_ago
    ).scalar() or 0
    
    week_orders = db.session.query(db.func.sum(Analytics.total_orders)).filter(
        Analytics.shop_id == shop.id,
        Analytics.date >= week_ago
    ).scalar() or 0
    
    recent_conversations = Conversation.query.filter_by(shop_id=shop.id)\
        .order_by(Conversation.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
        shop=shop,
        total_products=total_products,
        low_stock=low_stock,
        today_conversations=today_analytics.total_conversations if today_analytics else 0,
        week_conversations=week_conversations,
        week_orders=week_orders,
        recent_conversations=recent_conversations
    )


@app.route('/products')
def products_list():
    """Product management page"""
    shop = get_or_create_shop()
    products = Product.query.filter_by(shop_id=shop.id).order_by(Product.name).all()
    return render_template('products.html', shop=shop, products=products)


@app.route('/products/create', methods=['GET', 'POST'])
def product_create():
    """Create new product"""
    shop = get_or_create_shop()
    
    if request.method == 'POST':
        try:
            product = Product(
                shop_id=shop.id,
                name=request.form.get('name', ''),
                description=request.form.get('description', ''),
                price=float(request.form.get('price', 0) or 0),
                stock=int(request.form.get('stock', 0) or 0),
                category=request.form.get('category', 'Umum'),
                image_url=request.form.get('image_url', '')
            )
            db.session.add(product)
            db.session.commit()
            flash('Produk berhasil ditambahkan!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('products_list'))
    
    return render_template('product_form.html', shop=shop, mode='create')


@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def product_edit(product_id):
    """Edit product"""
    shop = get_or_create_shop()
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form.get('name', product.name)
            product.description = request.form.get('description', product.description)
            product.price = float(request.form.get('price', product.price) or 0)
            product.stock = int(request.form.get('stock', product.stock) or 0)
            product.category = request.form.get('category', product.category)
            product.image_url = request.form.get('image_url', product.image_url)
            db.session.commit()
            flash('Produk berhasil diupdate!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
        
        return redirect(url_for('products_list'))
    
    return render_template('product_form.html', shop=shop, product=product, mode='edit')


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
    
    return redirect(url_for('products_list'))


@app.route('/conversations')
def conversations_list():
    """Conversation history"""
    shop = get_or_create_shop()
    convs = Conversation.query.filter_by(shop_id=shop.id)\
        .order_by(Conversation.created_at.desc()).limit(50).all()
    return render_template('conversations.html', shop=shop, conversations=convs)


@app.route('/analytics')
def analytics_page():
    """Analytics dashboard"""
    shop = get_or_create_shop()
    
    # Last 7 days
    today = datetime.now(timezone.utc).date()
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    daily_data = []
    for d in dates:
        a = Analytics.query.filter_by(shop_id=shop.id, date=d).first()
        daily_data.append({
            'date': d.strftime('%d %b'),
            'conversations': a.total_conversations if a else 0,
            'inquiries': a.total_inquiries if a else 0,
            'orders': a.total_orders if a else 0
        })
    
    # Intent breakdown
    intent_counts = db.session.query(
        Conversation.intent,
        db.func.count(Conversation.id)
    ).filter_by(shop_id=shop.id).group_by(Conversation.intent).all()
    
    return render_template('analytics.html',
        shop=shop,
        daily_data=daily_data,
        intent_counts=intent_counts,
        dates=dates
    )


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
# API ENDPOINTS
# ============================================================
@app.route('/api/products', methods=['GET'])
def api_products():
    """API: List products"""
    shop = get_or_create_shop()
    products = Product.query.filter_by(shop_id=shop.id, is_active=True).all()
    return jsonify([p.to_dict() for p in products])


@app.route('/api/products', methods=['POST'])
def api_product_create():
    """API: Create product"""
    data = request.get_json()
    shop = get_or_create_shop()
    
    product = Product(
        shop_id=shop.id,
        name=data.get('name', ''),
        description=data.get('description', ''),
        price=float(data.get('price', 0)),
        stock=int(data.get('stock', 0)),
        category=data.get('category', 'Umum')
    )
    db.session.add(product)
    db.session.commit()
    
    return jsonify(product.to_dict()), 201


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API: Test chat with AI (for demo)"""
    data = request.get_json()
    message = data.get('message', '')
    shop_id = data.get('shop_id', 1)
    
    result = ai_agent.handle_message(message, shop_id)
    return jsonify(result)


@app.route('/api/stats', methods=['GET'])
def api_stats():
    """API: Get dashboard stats"""
    shop = get_or_create_shop()
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)
    
    return jsonify({
        'total_products': Product.query.filter_by(shop_id=shop.id, is_active=True).count(),
        'today_conversations': Analytics.query.filter_by(shop_id=shop.id, date=today).first().total_conversations if Analytics.query.filter_by(shop_id=shop.id, date=today).first() else 0,
        'week_conversations': db.session.query(db.func.sum(Analytics.total_conversations)).filter(
            Analytics.shop_id == shop.id, Analytics.date >= week_ago
        ).scalar() or 0
    })


# ============================================================
# DEMO / TEST ENDPOINTS
# ============================================================
@app.route('/demo')
def demo_page():
    """Interactive demo page for hackathon judges"""
    shop = get_or_create_shop()
    return render_template('demo.html', shop=shop)


@app.route('/demo/test', methods=['POST'])
def demo_test():
    """Test the AI agent from demo page"""
    data = request.get_json()
    message = data.get('message', 'Halo')
    result = ai_agent.handle_message(message, 1)
    return jsonify(result)


# ============================================================
# SEED DATA
# ============================================================
def seed_data():
    """Create sample data for demo"""
    if Shop.query.first():
        return  # Already seeded
    
    # Create shop
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
    
    # Create products
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
    
    # Create sample conversations
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
        Conversation(shop_id=shop.id, customer_phone='628444444444', customer_name='Deni',
            message_in='Pesan hoodie oversize', message_out='Maaf Kak, Hoodie Oversize lagi kosong 😔 Stok habis. Kami bisa kabarin kalau sudah restok ya? Atau mau lihat produk lain yang mirip?',
            intent='order', response_time_ms=1100),
        Conversation(shop_id=shop.id, customer_phone='628555555555', customer_name='Maya',
            message_in='Toko buka jam berapa?', message_out='Halo Kak Maya! 🏪 Toko MJF Endin buka setiap hari jam 09:00 - 21:00 WIB. Alamat di JL. Cempaka No.45, Kota Tangerang. Datang ya Kak!',
            intent='store_info', response_time_ms=750),
    ]
    for c in sample_convs:
        db.session.add(c)
    
    # Create sample analytics (last 7 days)
    from datetime import date as date_type
    today = date_type.today()
    for i in range(7):
        d = today - timedelta(days=i)
        import random
        a = Analytics(
            shop_id=shop.id,
            date=d,
            total_conversations=random.randint(15, 45),
            total_inquiries=random.randint(10, 30),
            total_orders=random.randint(2, 8),
            products_viewed=random.randint(20, 60),
            avg_response_time_ms=random.randint(800, 1500)
        )
        db.session.add(a)
    
    db.session.commit()
    print("✅ Seed data created!")


# ============================================================
# TEMPLATE HELPERS
# ============================================================
@app.template_filter('format_rupiah')
def format_rupiah(value):
    """Format number as Rupiah"""
    if value is None:
        return 'Rp 0'
    return f"Rp {value:,.0f}".replace(',', '.')


@app.template_filter('timeago')
def timeago(dt):
    """Relative time filter"""
    if not dt:
        return ''
    now = datetime.now(timezone.utc)
    # Make dt timezone-aware if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    if diff.days > 0:
        return f"{diff.days} hari lalu"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} jam lalu"
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} menit lalu"
    return 'Baru saja'


# ============================================================
# MAIN
# ============================================================
with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
