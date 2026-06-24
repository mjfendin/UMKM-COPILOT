# UMKM Copilot — Your AI-Powered Store Assistant on WhatsApp

## 💡 What Inspired Us

In Indonesia, there are **64+ million UMKM** (micro, small, and medium enterprises) — the backbone of our economy. Yet most of them still manage customer inquiries manually through WhatsApp, one message at a time.

As a small business owner myself, I know the struggle: **you can't be online 24/7.** When you sleep, customers message. When you're busy with orders, new inquiries pile up. And hiring staff? Too expensive for a small warung or toko.

What if every UMKM could have a **24/7 AI assistant** that answers product questions, checks stock, and even processes orders — all through the app they already use every day: **WhatsApp**?

No app downloads. No new platforms. Just chat.

---

## 🧠 What We Learned

### 1. The Power of "Zero Friction"
The biggest lesson: **don't ask users to change their behavior.** UMKM owners already live on WhatsApp. By building directly on WhatsApp Cloud API, we eliminated the #1 barrier — adoption.

### 2. Gemini is Fast and Multilingual
We tested Gemini 2.5 Flash across Indonesian and English conversations. It handles **code-switching** (mixing Bahasa and English in one message) remarkably well — critical for Indonesian users who often mix languages naturally.

### 3. AI Vision is a Game Changer for Inventory
Using Google Cloud Vision API, shop owners can **take a photo of a product** and the AI automatically extracts the product name, description, price, and suggested stock level. No typing required. This alone saves 10-15 minutes per product listing.

### 4. Multilingual ≠ Just Translation
True bilingual support isn't just swapping words. It's about understanding context: "How much is the batik?" vs "Berapa harga batik?" — same intent, different language. We built a detection system that identifies language from the customer's message and responds accordingly.

---

## ⚙️ How We Built It

### Architecture

```
Customer (WhatsApp) → Meta Cloud API → Flask Webhook → Gemini 2.5 Flash AI
                                                          ↓
                                                  Product Database (SQLite)
                                                  Cloud Vision API (Photos)
                                                          ↓
                                          Response → WhatsApp API → Customer
```

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **AI Engine** | Gemini 2.5 Flash | Fast, multilingual, structured output |
| **Vision** | Google Cloud Vision API | Extract product info from photos |
| **Backend** | Python Flask | Lightweight, fast to prototype |
| **Database** | SQLite + Firestore | Local dev + cloud persistence |
| **Messaging** | WhatsApp Cloud API | Zero-friction for end users |
| **Hosting** | Vercel Serverless | Free tier, auto-scaling |
| **Frontend** | Bootstrap 5 + Jinja2 | Responsive, dark/light mode |

### Key Features

1. **WhatsApp AI Agent** — Customers chat naturally, AI responds intelligently
2. **Photo-to-Product** — Take a photo → AI extracts name, price, description, stock
3. **Bilingual Support** — Full Indonesian + English with auto-detection
4. **Smart Fallback** — If Gemini API is rate-limited, local intelligence handles basic queries
5. **Admin Dashboard** — Manage products, view analytics, track conversations
6. **Order Management** — AI can process orders and confirm with customers

### How It Works (User Flow)

```
1. Customer sends WhatsApp: "Ada sepatu sneakers?"
2. AI Agent receives message via webhook
3. Gemini processes: detects Indonesian, queries product DB
4. AI finds: Sepatu Sneakers - Rp 450,000 (Stock: 3)
5. Response sent: "Sepatu Sneakers masih ada 3 unit Kak. 
   Harga Rp 450,000. Mau diorder? 😉"
6. Customer replies: "Iya, mau 1"
7. AI creates order, sends confirmation
8. Owner gets notified via admin dashboard
```

---

## 🚧 Challenges We Faced

### Challenge 1: WhatsApp Rate Limits
**Problem:** Meta's Cloud API has strict rate limits (12 requests/minute for free tier). During testing, we hit limits quickly.

**Solution:** Built a **smart rate limiter** with queuing system. When rate-limited, requests are queued and retried with exponential backoff. Also implemented **local fallback AI** that handles simple queries without hitting the API.

### Challenge 2: Language Detection in Code-Switching
**Problem:** Indonesian users often mix languages: "How much harga kemeja batik?" — neither purely English nor Indonesian.

**Solution:** Priority-based detection: check for Indonesian keywords first (higher false positive risk with English), then fall back to English. Uses word-boundary regex matching to prevent "hi" in "shirt" from triggering Indonesian mode.

### Challenge 3: Serverless Cold Starts
**Problem:** Vercel's serverless functions have cold start delays. First request after idle takes 3-5 seconds.

**Solution:** Implemented **health check pinging** and optimized imports. Reduced cold start to ~1.5 seconds by lazy-loading heavy dependencies.

### Challenge 4: Photo Product Extraction Accuracy
**Problem:** Raw Cloud Vision API returns generic labels, not structured product data.

**Solution:** Passed Vision API results to Gemini with a structured prompt: "Extract product name, description, price range, and suggest stock from this image." Gemini transforms raw labels into structured JSON.

### Challenge 5: Demo vs Production Gap
**Problem:** Demo mode works perfectly, but real WhatsApp integration requires Meta app review, business verification, and production phone numbers.

**Solution:** Built a **hybrid architecture** — demo page works instantly for judges, while WhatsApp integration works end-to-end for verified business accounts. Documented the full production setup path.

---

## 🎯 Impact & Vision

### Current State
- ✅ Fully functional AI agent on WhatsApp
- ✅ 8 sample products with real Indonesian pricing
- ✅ Bilingual support (ID/EN)
- ✅ Photo-to-product extraction
- ✅ Live demo at umkm-copilot.vercel.app

### Vision: Empowering 64 Million UMKM

If every UMKM in Indonesia could have an AI assistant for just **Rp 49,000/month** (~$3):
- A warung owner could serve customers while sleeping
- A batik seller could handle 100+ inquiries simultaneously
- A food stall could take orders via WhatsApp 24/7

**UMKM Copilot isn't just a chatbot — it's a digital employee that never sleeps, speaks every language, and costs less than a cup of coffee per day.**

---

## 🏗️ What's Next

1. **Multi-tenant architecture** — One platform, thousands of UMKM shops
2. **Payment integration** — QRIS, GoPay, OVO directly in chat
3. **Inventory sync** — Real-time stock updates across platforms
4. **Voice messages** — AI responds to voice notes (Whisper API)
5. **Analytics dashboard** — Sales trends, peak hours, customer insights

---

*"The best technology is the one you don't notice. For 64 million UMKM, that technology is already in their pocket — WhatsApp. We just added the AI."*
