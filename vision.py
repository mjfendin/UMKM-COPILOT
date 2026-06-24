"""
Gemini Vision for UMKM Copilot
Analyze product images using Gemini 2.0 Flash (multimodal)
"""

import os
import base64

# Gemini API config
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')


def is_vision_available():
    """Check if Gemini API is configured for vision"""
    return bool(GEMINI_API_KEY)


def analyze_product_image(image_url=None, image_bytes=None):
    """
    Analyze product image using Gemini Vision API
    Returns: dict with labels, description, colors, category suggestion
    """
    if not GEMINI_API_KEY:
        return {'error': 'Gemini API key not configured'}
    
    try:
        import google.generativeai as genai
        from PIL import Image
        import io
        
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Prepare image
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
        elif image_url:
            import requests
            response = requests.get(image_url, timeout=10)
            img = Image.open(io.BytesIO(response.content))
        else:
            return {'error': 'No image provided'}
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Analyze with Gemini
        prompt = """Analisis gambar produk ini dan berikan informasi dalam format JSON:
{
    "name": "nama produk yang terlihat",
    "description": "deskripsi singkat produk dalam Bahasa Indonesia (1-2 kalimat)",
    "category": "kategori: Pakaian Pria, Pakaian Wanita, Aksesoris, Sepatu, Elektronik, Lainnya",
    "colors": ["warna1", "warna2"],
    "dominant_color": "warna dominan",
    "condition": "kondisi: Baru/Bekas/Tidak Diketahui",
    "estimated_price_range": "range harga estimasi (misal: Rp 100.000 - Rp 300.000)"
}

Berikan analisis yang akurat berdasarkan gambar. Jika tidak yakin, gunakan "Tidak Diketahui"."""
        
        response = model.generate_content([prompt, img])
        
        # Parse response
        text = response.text.strip()
        
        # Try to extract JSON from response
        import json
        try:
            # Find JSON in response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                result = json.loads(text[start:end])
                result['ai_description'] = f"{result.get('name', 'Produk')}: {result.get('description', '')}"
                result['ai_model'] = 'Gemini 2.0 Flash'
                return result
        except json.JSONDecodeError:
            pass
        
        # Fallback: return raw description
        return {
            'ai_description': text[:500],
            'category_suggestion': 'Lainnya',
            'ai_model': 'Gemini 2.0 Flash'
        }
        
    except Exception as e:
        print(f"Gemini Vision error: {e}")
        return {'error': str(e)}


def analyze_product_image_local(image_bytes):
    """
    Local fallback for image analysis (no API)
    """
    result = {
        'ai_description': 'Gambar produk berhasil diupload. Silakan deskripsikan produk secara manual.',
        'category_suggestion': 'Lainnya',
        'colors': [],
        'ai_model': 'Local Fallback'
    }
    return result
