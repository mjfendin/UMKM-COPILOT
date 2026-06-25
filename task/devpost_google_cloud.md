## Please explain which product from Google Cloud you used during the hackathon and how.

We used **three Google Cloud products** as the core AI infrastructure for UMKM Copilot:

---

### 1. Google Gemini 2.5 Flash

**What it is:** Google's most efficient large language model, optimized for speed, cost, and multilingual capabilities.

**How we used it:**

**A. Primary AI Agent — All Customer Conversations**

Every WhatsApp message sent to a shop using UMKM Copilot is processed by Gemini 2.5 Flash:

```python
# Simplified flow in app.py
response = model.generate_content([
    f"You are the AI assistant for shop '{shop_name}'.",
    f"Available products: {products_json}",
    f"Customer message: {user_message}",
    "Reply in the same language the customer uses."
])
```

Gemini receives:
- Shop context (name, products, prices, stock)
- Customer message (natural language in Indonesian or English)
- Instructions (respond in appropriate language, be helpful, format nicely)

Gemini returns:
- Natural language response in the correct language
- Formatted with emojis for WhatsApp readability
- Contextually appropriate (stock check, price inquiry, order processing, recommendation)

**B. Language Detection & Code-Switching**

Indonesian users naturally mix languages: "How much harga kemeja batik?" Gemini handles this code-switching seamlessly — detecting mixed languages and responding in the most appropriate language (usually Indonesian for local businesses).

**C. Photo-to-Product Structuring**

When a shop owner uploads a product photo, Cloud Vision API extracts raw visual data, and Gemini structures it into a complete product listing:

```python
# After Cloud Vision analysis
gemini_response = model.generate_content([
    f"Analyze this product image data: {vision_result}",
    "Extract and return JSON with:",
    "1. Product name (Indonesian)",
    "2. Description (2-3 sentences, Indonesian)",
    "3. Suggested price range (in Rupiah)",
    "4. Suggested stock quantity",
    "5. Product category"
])
```

**D. Product Recommendations**

Gemini analyzes conversation context and purchase patterns to suggest complementary products, increasing average order value.

**Why Gemini 2.5 Flash specifically:**
- **Speed**: Sub-3-second response times (critical for WhatsApp chat UX)
- **Multilingual**: Excellent Indonesian + English support with code-switching
- **Structured Output**: Can return JSON for product data extraction
- **Cost**: Most cost-efficient Gemini model for high-volume chat
- **Free Tier**: 15 RPM — sufficient for MVP and early users

---

### 2. Google Cloud Vision API

**What it is:** Industry-leading image recognition and analysis service.

**How we used it:**

**A. Product Photo Analysis**

When a shop owner uploads a product photo through the admin dashboard:

```python
from google.cloud import vision

client = vision.ImageAnnotatorClient()
image = vision.Image(content=image_bytes)

# Multiple detection types
labels = client.label_detection(image=image)
objects = client.object_localization(image=image)
text = client.text_detection(image=image)
properties = client.image_properties(image=image)

# Results combined:
# labels: ["Clothing", "Jacket", "Denim", "Fashion"]
# objects: ["Jacket" at (x, y, w, h)]
# properties: dominant colors = [blue, dark blue]
```

**B. How Vision Data Feeds into Gemini**

The raw Vision API output is passed to Gemini for structuring:

```
Cloud Vision Output:
  Labels: ["Clothing", "Jacket", "Denim", "Fashion"]
  Objects: ["Jacket" detected at center]
  Colors: Blue (dominant), Dark Blue (secondary)
  Text: None detected

         ↓ Passed to Gemini ↓

Gemini Output:
  Name: "Jaket Denim Pria"
  Description: "Jaket denim warna biru gelap dengan resleting..."
  Price: Rp 350,000
  Stock: 10 units
  Category: "Pakaian Pria"
```

**Why Cloud Vision API:**
- **Accuracy**: Industry-leading image recognition for product categorization
- **Speed**: Sub-1-second analysis
- **Multiple Features**: Labels, objects, colors, text — all in one API call
- **Integration**: Seamless with Gemini for post-processing
- **Free Tier**: 1,000 units/month — sufficient for MVP

---

### 3. Google Cloud Firestore

**What it is:** NoSQL cloud database with real-time synchronization.

**How we used it:**

**A. Product Catalog Storage**

```python
# Store product
db.collection("products").add({
    "name": "Kemeja Batik Pria",
    "description": "Kemeja batik motif tradisional...",
    "price": 285000,
    "stock": 25,
    "shop_id": "toko_mjf_endin",
    "category": "Pakaian Pria",
    "created_at": datetime.now()
})

# Query products
products = db.collection("products")\
    .where("shop_id", "==", "toko_mjf_endin")\
    .where("stock", ">", 0)\
    .stream()
```

**B. Conversation History**

```python
# Store every conversation
db.collection("conversations").add({
    "customer_phone": "+62812xxxxxxx",
    "message": "Berapa harga kemeja batik?",
    "response": "Kemeja Batik Pria harganya Rp 285,000...",
    "language": "id",
    "intent": "price_inquiry",
    "timestamp": datetime.now()
})
```

**C. Order Management**

```python
# Store orders
db.collection("orders").add({
    "customer_phone": "+62812xxxxxxx",
    "items": [{"product": "Kemeja Batik", "qty": 2, "price": 285000}],
    "total": 570000,
    "status": "pending",
    "timestamp": datetime.now()
})
```

**D. Real-time Analytics**

Firestore powers the admin dashboard analytics:
- Total conversations today
- Top products by inquiry count
- Language distribution (ID vs EN)
- Peak hours analysis
- Stock level alerts

**Why Firestore:**
- **Real-time**: Instant reads/writes — critical for WhatsApp chat response speed
- **Scalability**: Auto-scales with traffic — no database management needed
- **Free Tier**: 50K reads/day, 20K writes/day — sufficient for MVP
- **Integration**: Native Python SDK, easy Flask integration
- **Query Support**: Complex queries for analytics and product filtering

---

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UMKM COPILOT ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Customer WhatsApp → Meta Cloud API → Flask Webhook         │
│                                             ↓               │
│                                    ┌─────────────────┐      │
│                                    │  Gemini 2.5     │      │
│                                    │  Flash (AI)     │      │
│                                    └────────┬────────┘      │
│                                             ↓               │
│              ┌──────────────────────────────┼───────────┐   │
│              ↓                              ↓           ↓   │
│     ┌─────────────────┐          ┌──────────────┐          │
│     │ Cloud Vision    │          │ Firestore    │          │
│     │ API (Photos)    │          │ (Database)   │          │
│     └─────────────────┘          └──────────────┘          │
│              ↓                              ↓               │
│              └──────────────┬───────────────┘               │
│                             ↓                               │
│                    AI Response → WhatsApp API → Customer    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### Why Google Cloud Stack

| Reason | Explanation |
|--------|-------------|
| **Speed** | Gemini 2.5 Flash delivers sub-3-second responses — critical for WhatsApp chat UX |
| **Multilingual** | Gemini's Indonesian + English support with code-switching handles our bilingual requirement |
| **Vision + Language** | Cloud Vision + Gemini combination creates the photo-to-product pipeline |
| **Real-time DB** | Firestore's instant reads/writes enable fast conversation processing |
| **Cost Efficiency** | Free tiers cover entire hackathon MVP — $0 infrastructure cost |
| **Scalability** | All three services auto-scale — no capacity planning needed |
| **XPRIZE Compliance** | Using Google Cloud Stack qualifies for the Gemini XPRIZE category |

---

### Bahasa Indonesia (Arti)

Kami menggunakan **tiga produk Google Cloud** sebagai infrastruktur AI inti:

### 1. Google Gemini 2.5 Flash

**Cara penggunaan:**
- **Agen AI Utama**: Semua percakapan WhatsApp diproses oleh Gemini
- **Deteksi Bahasa**: Handle code-switching (campur Bahasa Indonesia + English)
- **Foto-ke-Produk**: Struktur data dari Cloud Vision API jadi listing produk
- **Rekomendasi**: Usulkan produk terkait berdasarkan konteks percakapan

**Kenapa Gemini 2.5 Flash:**
- Kecepatan: Respon sub-3 detik
- Multilingual: Excellent support Bahasa Indonesia + English
- Structured Output: Bisa return JSON untuk data produk
- Biaya: Model paling cost-efficient untuk chat volume tinggi
- Free Tier: 15 RPM — cukup untuk MVP

### 2. Google Cloud Vision API

**Cara penggunaan:**
- **Analisis Foto Produk**: Owner upload foto → Vision ekstrak fitur visual
- **Multi-deteksi**: Labels, objects, colors, text — semua dalam 1 API call
- **Input untuk Gemini**: Raw Vision output → Gemini struktur jadi listing produk

**Kenapa Cloud Vision:**
- Akurasi: Pengenalan gambar terdepan
- Kecepatan: Sub-1 detik analisis
- Fitur: Labels + objects + colors + text
- Integrasi: Seamless dengan Gemini
- Free Tier: 1.000 unit/bulan — cukup untuk MVP

### 3. Google Cloud Firestore

**Cara penggunaan:**
- **Katalog Produk**: Simpan data produk dengan query complex
- **Riwayat Percakapan**: Catat semua chat pelanggan
- **Manajemen Order**: Proses dan simpan pesanan
- **Analitik Real-time**: Dashboard admin menampilkan stats

**Kenapa Firestore:**
- Real-time: Reads/writes instan — kritical untuk kecepatan respon WhatsApp
- Skalabilitas: Auto-scale — tidak perlu manage database
- Free Tier: 50K reads/day, 20K writes/day
- Integrasi: Native Python SDK
- Query: Support query complex untuk analitik

### Arsitektur Integrasi

```
Pelanggan WhatsApp → Meta API → Flask Webhook
                                      ↓
                              Gemini 2.5 Flash (AI)
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                                   ↓
           Cloud Vision API                     Firestore
           (Analisis Foto)                      (Database)
                    ↓                                   ↓
                    └──────────┬────────────────────────┘
                               ↓
                    AI Response → WhatsApp → Pelanggan
```

### Kenapa Google Cloud Stack

| Alasan | Penjelasan |
|--------|-----------|
| Kecepatan | Gemini respon sub-3 detik — kritical untuk chat |
| Multilingual | Support Bahasa Indonesia + English + code-switching |
| Vision + Language | Cloud Vision + Gemini = pipeline foto-ke-produk |
| DB Real-time | Firestore reads/writes instan |
| Efisiensi Biaya | Free tier cukup untuk seluruh MVP |
| Skalabilitas | Semua layanan auto-scale |
| Kepatuhan XPRIZE | Google Cloud Stack = eligible Gemini XPRIZE |
