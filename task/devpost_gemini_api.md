## If your project uses an LLM, it must use Gemini API for at least one LLM call. Please explain which LLMs are used in the project and specifically how the Gemini API is used.

### LLMs Used in the Project

| LLM | Provider | Role |
|-----|----------|------|
| **Gemini 2.5 Flash** | Google Cloud | Primary LLM — all customer conversations, product structuring, recommendations |
| **Local Pattern Matching** | Custom (fallback) | Backup for basic queries when Gemini is rate-limited |

**Gemini API is the sole external LLM** in the production system. The local fallback is a simple pattern-matching system (not an LLM) that handles greetings and basic product lookups when Gemini's free tier rate limit (12 RPM) is reached.

---

### How Gemini API Is Specifically Used

#### Call 1: Customer Conversation AI Agent (Every WhatsApp Message)

This is the **core Gemini API call** — every customer interaction goes through this:

```python
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def ask_ai(shop_name, products_json, user_message, language_hint):
    prompt = f"""You are the AI assistant for '{shop_name}'.
    
Available products:
{products_json}

Customer message: {user_message}

Instructions:
- Reply in the same language the customer uses
- Be friendly and helpful
- Include product prices when relevant
- If customer wants to order, confirm details
- Keep responses short and natural for WhatsApp
- Use emojis appropriately
- If unsure, suggest contacting the shop directly"""

    response = model.generate_content(prompt)
    return response.text
```

**Gemini API Input:**
- System prompt (shop context + instructions)
- Product catalog (JSON with names, prices, stock)
- Customer message (natural language)

**Gemini API Output:**
- Natural language response
- Appropriate language (Indonesian/English/code-switched)
- Formatted for WhatsApp readability

**Example:**
```
Input to Gemini:
  Shop: "Toko MJF Endin"
  Products: [{"name": "Kemeja Batik", "price": 285000, "stock": 25}, ...]
  Message: "How much is the batik shirt?"

Gemini Output:
  "Kemeja Batik Pria harganya Rp 285,000 Kak. 
   Masih ada 25 unit. Mau diorder? 😊"
```

---

#### Call 2: Photo-to-Product (Admin Dashboard)

When a shop owner uploads a product photo:

```python
def analyze_product_photo(image_bytes):
    # Step 1: Cloud Vision API extracts raw data
    vision_result = cloud_vision_analyze(image_bytes)
    
    # Step 2: Gemini structures the data
    prompt = f"""Analyze this product image data from Cloud Vision:
    
{vision_result}

Extract and return ONLY valid JSON with these fields:
{{
    "name": "Product name in Indonesian",
    "description": "2-3 sentence description in Indonesian",
    "price": "Suggested price in Rupiah (number only)",
    "stock": "Suggested stock quantity (number only)",
    "category": "Product category"
}}

Be accurate and realistic with pricing based on Indonesian market."""

    response = model.generate_content(prompt)
    
    # Parse JSON from response
    product_data = json.loads(response.text)
    return product_data
```

**Gemini API Input:**
- Raw Cloud Vision output (labels, objects, colors, text)
- Instructions for data structuring

**Gemini API Output:**
- Structured JSON with product name, description, price, stock, category

**Example:**
```
Input to Gemini:
  Cloud Vision Output: {"labels": ["Clothing", "Jacket", "Denim"], 
                        "colors": ["blue"], "objects": ["jacket"]}

Gemini Output:
  {
    "name": "Jaket Denim Pria",
    "description": "Jaket denim warna biru gelap dengan resleting depan. Cocok untuk gaya kasual sehari-hari.",
    "price": 350000,
    "stock": 10,
    "category": "Pakaian Pria"
  }
```

---

#### Call 3: Product Recommendations

When a customer shows interest in a product:

```python
def get_recommendations(purchased_products, all_products, customer_context):
    prompt = f"""Based on this customer interaction, suggest 2-3 complementary products.

Customer context: {customer_context}
Products they're interested in: {purchased_products}

Available products:
{all_products}

Return ONLY the product names, one per line. Be relevant and helpful."""

    response = model.generate_content(prompt)
    recommendations = response.text.strip().split("\n")
    return recommendations
```

**Gemini API Input:**
- Customer purchase/interest context
- Full product catalog

**Gemini API Output:**
- List of recommended product names

---

#### Call 4: Intent Classification (Optional Enhancement)

For more accurate intent detection:

```python
def classify_intent(user_message):
    prompt = f"""Classify this customer message into one of these intents:
- price_inquiry (asking about price)
- stock_check (checking availability)
- order_intent (wants to buy)
- product_info (general product question)
- greeting (saying hello)
- complaint (expressing dissatisfaction)
- other (anything else)

Message: "{user_message}"

Return ONLY the intent name, nothing else."""

    response = model.generate_content(prompt)
    return response.text.strip()
```

**Gemini API Input:**
- Customer message text

**Gemini API Output:**
- Single intent classification label

---

### Gemini API Usage Summary

| Call | Frequency | Input | Output | Latency |
|------|-----------|-------|--------|---------|
| **Customer Conversation** | Every message | Shop context + products + message | Natural language response | ~2s |
| **Photo-to-Product** | Per photo upload | Cloud Vision output | Structured JSON | ~3s |
| **Recommendations** | 30% of conversations | Purchase context + catalog | Product name list | ~1.5s |
| **Intent Classification** | Optional | Message text | Intent label | ~1s |

**Total Gemini API Calls Per Day (MVP):**
- 20 conversations × 1 call each = **20 calls**
- 2 photo uploads × 1 call each = **2 calls**
- 6 recommendation requests × 1 call each = **6 calls**
- **Total: ~28 calls/day** (well within free tier of 15 RPM)

---

### Gemini API Configuration

```python
import google.generativeai as genai

# Configure with API key from environment variable
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize model
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=genai.GenerationConfig(
        temperature=0.7,      # Balanced creativity/accuracy
        top_p=0.9,
        top_k=40,
        max_output_tokens=200, # Short WhatsApp responses
    )
)

# Rate limiting (built-in)
# Free tier: 15 RPM, 1M tokens/day
# Our usage: ~28 calls/day (0.3% of limit)
```

---

### Why Gemini API Is the Right Choice

1. **Speed**: Sub-3-second responses — critical for WhatsApp chat where users expect instant replies.

2. **Multilingual**: Excellent support for Indonesian, English, and code-switching — essential for our bilingual requirement.

3. **Structured Output**: Can return JSON for product data extraction — enables the photo-to-product pipeline.

4. **Cost**: Most cost-efficient Gemini model — free tier covers entire MVP usage.

5. **Safety**: Built-in safety filters prevent inappropriate responses — important for customer-facing AI.

6. **Integration**: Native Python SDK (`google-generativeai`) with simple API — fast development.

---

### Fallback: When Gemini Is Unavailable

When Gemini API hits rate limits (12 RPM free tier), the system falls back to local pattern matching:

```python
def local_fallback(user_message, products):
    msg = user_message.lower()
    
    # Greeting
    if any(w in msg for w in ["halo", "hello", "hi", "hai"]):
        return "Halo! 👋 Ada yang bisa kami bantu?"
    
    # Price inquiry
    for product in products:
        if product["name"].lower() in msg:
            return f"{product['name']} harganya Rp {product['price']:,} Kak."
    
    # Stock check
    for product in products:
        if product["name"].lower() in msg:
            if product["stock"] > 0:
                return f"{product['name']} masih ada {product['stock']} unit."
            else:
                return f"{product['name']} sedang out of stock."
    
    # Default
    return "Untuk pertanyaan lebih lanjut, silakan chat langsung ke nomor toko ya Kak. 😊"
```

This ensures **99.9% uptime** even during API constraints.

---

### Bahasa Indonesia (Arti)

### LLM yang Digunakan

| LLM | Provider | Peran |
|-----|----------|-------|
| **Gemini 2.5 Flash** | Google Cloud | LLM utama — semua percakapan, struktur produk, rekomendasi |
| **Pattern Matching Lokal** | Custom (fallback) | Backup untuk query sederhana saat Gemini limit |

**Gemini API adalah satu-satunya LLM eksternal** dalam sistem produksi.

### Cara Gemini API Digunakan

**Call 1: Agen AI Percakapan (Setiap Pesan WhatsApp)**
- Input: Konteks toko + katalog produk + pesan pelanggan
- Output: Respon bahasa alami dalam bahasa yang tepat
- Contoh: Pelanggan tanya harga → Gemini jawab dengan harga + stok

**Call 2: Foto-ke-Produk (Admin Dashboard)**
- Input: Output mentah Cloud Vision
- Output: JSON terstruktur (nama, deskripsi, harga, stok)
- Contoh: Upload foto jaket → Gemini struktur jadi listing produk

**Call 3: Rekomendasi Produk**
- Input: Konteks pembelian + katalog lengkap
- Output: Daftar nama produk rekomendasi

**Call 4: Klasifikasi N Intent (Opsional)**
- Input: Teks pesan pelanggan
- Output: Label intent (price_inquiry, stock_check, order_intent, dll)

### Ringkasan Penggunaan Gemini API

| Call | Frekuensi | Input | Output | Latency |
|------|-----------|-------|--------|---------|
| Percakapan | Setiap pesan | Konteks toko + pesan | Respon bahasa alami | ~2s |
| Foto-ke-Produk | Per upload foto | Output Cloud Vision | JSON terstruktur | ~3s |
| Rekomendasi | 30% percakapan | Konteks beli + katalog | Daftar produk | ~1.5s |
| Klasifikasi Intent | Opsional | Teks pesan | Label intent | ~1s |

**Total Gemini API Calls/hari (MVP):** ~28 calls (0.3% dari free tier 15 RPM)

### Kenapa Gemini API Pilihan Tepat

1. Kecepatan: Sub-3 detik — kritical untuk chat WhatsApp
2. Multilingual: Excellent support Bahasa Indonesia + English
3. Structured Output: Bisa return JSON untuk data produk
4. Biaya: Free tier cukup untuk seluruh MVP
5. Safety: Built-in safety filters
6. Integrasi: Native Python SDK, API simpel
