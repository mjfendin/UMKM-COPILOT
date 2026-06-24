"""
Cloud Vision API Helper for UMKM Copilot
Auto-describe products from photos
"""

import os
from io import BytesIO

# Vision client (lazy init)
_vision_client = None

def get_vision_client():
    """Get Cloud Vision client"""
    global _vision_client
    if _vision_client is None:
        try:
            from google.cloud import vision
            _vision_client = vision.ImageAnnotatorClient()
        except Exception as e:
            print(f"Vision init error: {e}")
            _vision_client = None
    return _vision_client


def is_vision_available():
    """Check if Cloud Vision is configured"""
    return get_vision_client() is not None


def analyze_product_image(image_url=None, image_bytes=None):
    """
    Analyze product image using Cloud Vision API
    Returns: dict with labels, description, colors, etc.
    """
    client = get_vision_client()
    if not client:
        return {'error': 'Cloud Vision not configured'}
    
    try:
        from google.cloud import vision
        
        if image_bytes:
            image = vision.Image(content=image_bytes)
        elif image_url:
            image = vision.Image()
            image.source.image_uri = image_url
        else:
            return {'error': 'No image provided'}
        
        # Run multiple detection types
        features = [
            vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION, max_results=10),
            vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION, max_results=5),
            vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION),
            vision.Feature(type_=vision.Feature.Type.IMAGE_PROPERTIES),
        ]
        
        request = vision.AnnotateImageRequest(image=image, features=features)
        response = client.annotate_image(request=request)
        
        if response.error.message:
            return {'error': response.error.message}
        
        result = {}
        
        # Labels (objects/categories)
        if response.label_annotations:
            result['labels'] = [label.description for label in response.label_annotations]
            result['category_suggestion'] = _suggest_category(result['labels'])
        
        # Object localization
        if response.localized_object_annotations:
            result['objects'] = [obj.name for obj in response.localized_object_annotations]
        
        # Text (for price tags, brand names)
        if response.text_annotations:
            result['text_found'] = response.text_annotations[0].description if response.text_annotations else ''
        
        # Dominant colors
        if response.image_properties_annotation:
            colors = response.image_properties_annotation.dominant_colors.colors
            if colors:
                top_color = colors[0]
                r, g, b = int(top_color.color.red), int(top_color.color.green), int(top_color.color.blue)
                result['dominant_color'] = f'#{r:02x}{g:02x}{b:02x}'
                result['color_name'] = _hex_to_color_name(r, g, b)
        
        # Generate AI description
        result['ai_description'] = _generate_description(result)
        
        return result
        
    except Exception as e:
        print(f"Vision API error: {e}")
        return {'error': str(e)}


def analyze_product_image_local(image_bytes):
    """
    Local fallback for image analysis (no Cloud Vision)
    Uses basic heuristics
    """
    result = {
        'labels': ['product'],
        'category_suggestion': 'Umum',
        'ai_description': 'Gambar produk berhasil diupload. Silakan deskripsikan produk secara manual.',
        'color_name': 'Unknown'
    }
    return result


def _suggest_category(labels):
    """Suggest product category from labels"""
    category_map = {
        'Pakaian Pria': ['shirt', 'menswear', 'man', 'male'],
        'Pakaian Wanita': ['dress', 'womenswear', 'woman', 'female', 'skirt'],
        'Aksesoris': ['watch', 'jewelry', 'hat', 'bag', 'sunglasses', 'accessory'],
        'Sepatu': ['shoe', 'footwear', 'sneaker', 'boot', 'sandal'],
        'Elektronik': ['electronic', 'phone', 'computer', 'gadget'],
    }
    
    labels_lower = [l.lower() for l in labels]
    
    for category, keywords in category_map.items():
        if any(kw in ' '.join(labels_lower) for kw in keywords):
            return category
    
    return 'Umum'


def _hex_to_color_name(r, g, b):
    """Convert RGB to basic color name"""
    colors = {
        (0, 0, 0): 'Hitam',
        (255, 255, 255): 'Putih',
        (255, 0, 0): 'Merah',
        (0, 128, 0): 'Hijau',
        (0, 0, 255): 'Biru',
        (255, 255, 0): 'Kuning',
        (255, 165, 0): 'Oranye',
        (128, 0, 128): 'Ungu',
        (165, 42, 42): 'Coklat',
    }
    
    min_dist = float('inf')
    closest = 'Unknown'
    for (cr, cg, cb), name in colors.items():
        dist = (r-cr)**2 + (g-cg)**2 + (b-cb)**2
        if dist < min_dist:
            min_dist = dist
            closest = name
    
    return closest


def _generate_description(analysis):
    """Generate product description from analysis"""
    parts = []
    
    if 'objects' in analysis and analysis['objects']:
        parts.append(f"Produk: {', '.join(analysis['objects'][:3])}")
    
    if 'color_name' in analysis and analysis['color_name'] != 'Unknown':
        parts.append(f"Warna dominan: {analysis['color_name']}")
    
    if 'labels' in analysis:
        relevant_labels = [l for l in analysis['labels'][:5] if l.lower() not in ['product', 'image', 'photo', 'goods']]
        if relevant_labels:
            parts.append(f"Kategori: {', '.join(relevant_labels[:3])}")
    
    if 'text_found' in analysis and analysis['text_found']:
        text = analysis['text_found'][:100]
        parts.append(f"Teks terdeteksi: {text}")
    
    if parts:
        return '. '.join(parts)
    
    return 'Gambar produk berhasil dianalisis. Silakan tambahkan deskripsi manual.'
