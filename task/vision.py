"""
Gemini Vision for UMKM Copilot
Analyze product images using Gemini API (multimodal) with smart local fallback
"""
import os
import json
import time
import base64
import urllib.request
import urllib.error

_GEMINI_KEY_VAR = 'GEMINI_API_KEY'
GEMINI_API_KEY = os.environ.get(_GEMINI_KEY_VAR, '')
VISION_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']

_call_times = []
_quota_exhausted = False
_quota_exhausted_at = 0
_cooldown_seconds = 62
_last_working_model = None


def is_vision_available():
    return bool(GEMINI_API_KEY)


def _check_rate_limit():
    global _quota_exhausted, _quota_exhausted_at, _call_times
    now = time.time()
    if _quota_exhausted:
        if now - _quota_exhausted_at < _cooldown_seconds:
            return False
        else:
            _quota_exhausted = False
            _call_times = []
    _call_times = [t for t in _call_times if now - t < 60]
    if len(_call_times) >= 8:
        return False
    _call_times.append(now)
    return True


def _mark_quota_exhausted():
    global _quota_exhausted, _quota_exhausted_at
    _quota_exhausted = True
    _quota_exhausted_at = time.time()


def _call_gemini_vision_REST(image_bytes, model_name):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}'
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    prompt = """Analisis gambar produk ini dan berikan informasi dalam format JSON HANYA:
{"name":"nama produk","description":"deskripsi 1-2 kalimat","category":"Pakaian Pria|Pakaian Wanita|Celana|Aksesoris|Sepatu|Elektronik|Lainnya","price":150000,"stock":10,"colors":["warna"],"dominant_color":"warna"}
Petunjuk: price=estimasi harga pasar Indonesia, stock=10 default, HANYA JSON."""
    payload = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
        ]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512}
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode('utf-8'))
    text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    return text.strip()


# ============================================================
# LOCAL ANALYSIS — smart fallback when Gemini is unavailable
# ============================================================

def _analyze_local(image_bytes):
    """Analyze image locally: detect dominant color and guess product info"""
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # --- Dominant color from center crop (skip background edges) ---
        w, h = img.size
        cx, cy = w // 2, h // 2
        box = (max(cx - w // 4, 0), max(cy - h // 4, 0),
               min(cx + w // 4, w), min(cy + h // 4, h))
        crop = img.crop(box).resize((20, 20))
        pixels = list(crop.getdata())
        r_avg = sum(p[0] for p in pixels) // len(pixels)
        g_avg = sum(p[1] for p in pixels) // len(pixels)
        b_avg = sum(p[2] for p in pixels) // len(pixels)

        color_name = _rgb_to_color_name(r_avg, g_avg, b_avg)
        category = _guess_category(color_name)
        price = _estimate_price(category)
        name = f"Produk {color_name.title()}"

        return {
            'name': name,
            'description': f"Produk berwarna {color_name}. Silakan tambahkan deskripsi lengkap.",
            'category': category,
            'price': price,
            'stock': 10,
            'colors': [color_name] if color_name != 'unknown' else [],
            'dominant_color': color_name,
            'ai_description': f"{name}: Produk berwarna {color_name}",
            'ai_model': 'Local Analysis',
            'success': True
        }
    except Exception as e:
        print(f"Local analysis error: {e}")
        return {
            'name': 'Produk Baru', 'description': 'Silakan isi detail produk secara manual.',
            'category': 'Lainnya', 'price': 0, 'stock': 10,
            'colors': [], 'dominant_color': '',
            'ai_description': 'Silakan isi detail produk secara manual.',
            'ai_model': 'Fallback', 'success': False
        }


def _rgb_to_color_name(r, g, b):
    """Map RGB to Indonesian color name — optimized for clothing/products"""
    # Order matters: most specific first
    colors = [
        # Browns / Earth tones (must come before gray)
        ('coklat',       139,  90,  43),
        ('coklat',       160, 110,  60),
        ('coklat',       120,  80,  40),
        ('krem',         230, 210, 180),
        ('beige',        210, 190, 160),
        # Blacks / Darks
        ('hitam',         40,  40,  40),
        ('hitam',         60,  60,  60),
        ('hitam',         20,  20,  20),
        # Whites
        ('putih',        245, 245, 245),
        ('putih',        235, 235, 235),
        ('putih',        250, 250, 250),
        # Grays
        ('abu-abu',      140, 140, 140),
        ('abu-abu',      170, 170, 170),
        ('abu-abu',      110, 110, 110),
        # Reds
        ('merah',        200,  40,  40),
        ('merah',        180,  30,  30),
        ('marun',        120,  20,  40),
        ('pink',         240, 100, 130),
        ('pink',         250, 150, 170),
        ('salmon',       240, 130, 100),
        # Blues
        ('biru',          30,  80, 180),
        ('biru',          50, 100, 200),
        ('navy',          20,  40,  90),
        ('biru muda',    100, 170, 230),
        ('cyan',          50, 200, 200),
        # Greens
        ('hijau',         40, 160,  50),
        ('hijau',         50, 140,  40),
        ('hijau tua',     20,  80,  30),
        ('olive',        120, 120,  40),
        # Yellows
        ('kuning',       240, 220,  40),
        ('kuning',       230, 200,  30),
        ('emas',         210, 180,  50),
        # Orange
        ('orange',       240, 150,  30),
        ('orange',       230, 130,  20),
        # Purples
        ('ungu',         130,  50, 180),
        ('ungu',         150,  70, 200),
        ('lavender',     180, 140, 220),
    ]

    best_color = 'lainnya'
    best_dist = float('inf')

    for name, cr, cg, cb in colors:
        dist = ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_color = name

    # If too far from any known color, it's multi-color
    if best_dist > 100:
        return 'multi-warna'

    return best_color


def _guess_category(color):
    """Guess UMKM product category from dominant color"""
    # Dark neutral colors → most common for men's clothing / shoes / bags
    if color in ('hitam', 'navy', 'abu-abu', 'coklat', 'olive'):
        return 'Pakaian Pria'
    # Bright / warm colors → more common for women's clothing
    if color in ('merah', 'pink', 'salmon', 'ungu', 'lavender', 'kuning', 'emas'):
        return 'Pakaian Wanita'
    # Light neutral → could be either, default men's
    if color in ('putih', 'krem', 'beige'):
        return 'Pakaian Pria'
    # Blues → unisex, default men's
    if color in ('biru', 'biru muda', 'cyan'):
        return 'Pakaian Pria'
    # Greens → unisex
    if color in ('hijau', 'hijau tua'):
        return 'Pakaian Pria'
    return 'Lainnya'


def _estimate_price(category):
    prices = {
        'Pakaian Pria': 175000, 'Pakaian Wanita': 225000,
        'Celana': 200000, 'Aksesoris': 125000,
        'Sepatu': 350000, 'Elektronik': 500000, 'Lainnya': 150000,
    }
    return prices.get(category, 150000)


# ============================================================
# GEMINI VISION — primary analysis
# ============================================================

def analyze_product_image(image_url=None, image_bytes=None):
    global _last_working_model, _quota_exhausted, _quota_exhausted_at, _call_times

    img_bytes = image_bytes
    if not img_bytes and image_url:
        req = urllib.request.Request(image_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_bytes = resp.read()
    if not img_bytes:
        return {'error': 'No image provided'}

    # If no API key or quota exhausted → local immediately
    if not GEMINI_API_KEY or _quota_exhausted:
        if _quota_exhausted:
            now = time.time()
            if now - _quota_exhausted_at < _cooldown_seconds:
                return _analyze_local(img_bytes)
            else:
                _quota_exhausted = False
                _call_times = []
        else:
            return _analyze_local(img_bytes)

    if not _check_rate_limit():
        return _analyze_local(img_bytes)

    # Try Gemini models
    models = VISION_MODELS[:]
    if _last_working_model and _last_working_model in models:
        models.remove(_last_working_model)
        models.insert(0, _last_working_model)

    for model in models:
        try:
            text = _call_gemini_vision_REST(img_bytes, model)
            _last_working_model = model

            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                result = json.loads(text[start:end])
                if result.get('name') or result.get('category'):
                    result['ai_description'] = f"{result.get('name', 'Produk')}: {result.get('description', '')}"
                    result['ai_model'] = model
                    result['success'] = True
                    return result

            return _analyze_local(img_bytes)

        except Exception as e:
            error_str = str(e).lower()
            if '429' in str(e) or 'quota' in error_str or 'rate' in error_str:
                _mark_quota_exhausted()
                print(f"Vision quota exhausted on {model}: {e}")
                break
            print(f"Vision error on {model}: {e}")
            continue

    return _analyze_local(img_bytes)


def analyze_product_image_local(image_bytes):
    return _analyze_local(image_bytes)
