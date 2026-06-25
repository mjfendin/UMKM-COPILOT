# 🤖 UMKM Copilot — Build with Gemini XPRIZE

> **AI Business Agent yang mengotomasi operasional UMKM Indonesia**
> 90 hari untuk launch, acquire users, dan generate revenue.

---

## 📋 Ringkasan Eksekutif

**Nama:** UMKM Copilot
**Tagline:** "Toko pintar, tanpa karyawan AI"
**Kategori:** Small Business Services + Entrepreneurship & Job Creation
**Platform:** Google Cloud (Gemini API, Vertex AI, Cloud Vision, Firestore)

**Masalah:** 65 juta UMKM Indonesia kekurangan SDM untuk:
- Balas chat customer 24/7 (butuh 1-3 karyawan)
- Kelola stok barang secara real-time
- Bikin konten marketing (foto, deskripsi, caption)
- Analisis penjualan mingguan

**Solusi:** AI agent yang handles SEMUA ini via WhatsApp — UMKM tinggal chat seperti biasa.

---

## 🎯 Judging Criteria Alignment

### 1. Business Viability (33%)
| Metric | Target | Strategy |
|--------|--------|----------|
| Revenue in 90 days | Rp 50 juta+ | Freemium → Rp 99K/bulan per toko |
| Real users | 500+ toko | Onboard via WhatsApp komunitas UMKM |
| Business model | SaaS subscription | Monthly recurring revenue |
| User retention | 60%+ month-2 | Value = waktu hemat (2 jam/hari) |

### 2. AI-Native Operations (33%)
| AI Component | What It Does | Google Cloud Service |
|-------------|-------------|---------------------|
| Customer Service Agent | Auto-reply chat via WA | **Gemini Pro** (reasoning + function calling) |
| Product Content Generator | Foto + deskripsi + caption | **Gemini Pro Vision** + Cloud Vision |
| Inventory Predictor | Prediksi stok habis | **Vertex AI** (time series forecasting) |
| Sales Analyzer | Ringkasan penjualan | **Gemini Pro** (text generation) |
| Marketing Scheduler | Auto-post konten | **Cloud Functions** (scheduled) |

### 3. Category Impact (33%)
| Impact Area | Scale |
|------------|-------|
| UMKM yang terbantu | 65 juta di Indonesia |
| Waktu hemat per toko | 2-4 jam/hari |
| Cost saving per toko | Rp 2-5 juta/bulan (gaji 1 CS) |
| Revenue increase | 15-30% dari AI marketing |
| Market expansion | Bisa scale ke SE Asia (600M+ UMKM) |

---

## 🏗️ Tech Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER LAYER                        │
│  📱 WhatsApp (primary) │ 💻 Dashboard (admin)       │
└──────────┬──────────────────────┬────────────────────┘
           │                      │
┌──────────▼──────────────────────▼────────────────────┐
│                  API GATEWAY (Cloud Run)              │
│  Auth │ Rate Limit │ Request Routing                  │
└───┬──────────┬──────────┬──────────┬─────────────────┘
    │          │          │          │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│ CS    │ │Inv.   │ │Content│ │Sales  │
│ Agent │ │Agent  │ │Agent  │ │Agent  │
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │          │          │          │
┌───▼──────────▼──────────▼──────────▼─────────────────┐
│              GOOGLE CLOUD SERVICES                   │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Gemini Pro  │  │ Cloud Vision │  │ Vertex AI  │  │
│  │ (NLP/CX)    │  │ (Product     │  │ (Forecast) │  │
│  │             │  │  Photos)     │  │            │  │
│  └─────────────┘  └──────────────┘  └────────────┘  │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Firestore   │  │ Cloud        │  │ Cloud      │  │
│  │ (Data)      │  │ Functions    │  │ Storage    │  │
│  │             │  │ (Scheduled)  │  │ (Media)    │  │
│  └─────────────┘  └──────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────┘
```

### Google Cloud Products Used (Required)
| Product | Usage | Why Essential |
|---------|-------|---------------|
| **Gemini API** | Core AI reasoning, NLP, function calling | Handles all customer conversations + business logic |
| **Vertex AI** | Custom model training, time series forecasting | Inventory prediction needs custom training |
| **Cloud Vision API** | Product photo analysis, OCR | Auto-categorize products from photos |
| **Cloud Run** | Serverless backend hosting | Auto-scales with traffic, pay-per-use |
| **Firestore** | NoSQL database | Real-time data sync for inventory |
| **Cloud Functions** | Scheduled tasks (daily reports, alerts) | Cron-like automation |
| **Cloud Storage** | Product images, generated content | Media storage |

---

## 💰 Business Model

### Pricing Tiers
| Tier | Price | Features |
|------|-------|----------|
| **Free** | Rp 0 | 10 AI conversations/day, basic inventory |
| **Starter** | Rp 49.000/bulan | Unlimited AI chat, inventory tracking |
| **Pro** | Rp 99.000/bulan | + AI marketing, auto-content, analytics |
| **Business** | Rp 199.000/bulan | + Multi-user, API access, priority support |

### Revenue Projections (90 days)
| Month | Users (Free) | Users (Paid) | MRR |
|-------|-------------|-------------|-----|
| Month 1 | 100 | 15 | Rp 1.4 juta |
| Month 2 | 300 | 60 | Rp 5.9 juta |
| Month 3 | 500 | 150 | Rp 14.8 juta |
| **Total** | | | **Rp 22.1 juta** |

### Expansion Revenue
- **WhatsApp Business API integration**: +Rp 50K/bulan
- **Custom AI training** (brand voice): +Rp 200K one-time
- **Marketplace fee**: 2% dari transaksi yang difasilitasi AI

---

## 🚀 Feature Roadmap (90 Days)

### Phase 1: MVP (Week 1-4) — "Proof of Concept"
**Goal:** Working product, 50 beta users

| Feature | Description | Google Cloud |
|---------|-------------|-------------|
| WhatsApp CS Agent | Auto-reply pertanyaan customer | Gemini Pro |
| Basic Inventory | Input + tracking stok manual | Firestore |
| Dashboard Web | Lihat status toko | Cloud Run |
| User Onboarding | Via WhatsApp link | Cloud Functions |

**Deliverable:** 10 toko pilot di Bandung

### Phase 2: Growth (Week 5-8) — "Real Users, Real Revenue"
**Goal:** 200 users, Rp 5 juta MRR

| Feature | Description | Google Cloud |
|---------|-------------|-------------|
| AI Content Generator | Foto → deskripsi + caption | Gemini Vision |
| Inventory Alerts | Notif stok habis via WA | Cloud Functions |
| Sales Summary | Ringkasan harian/mingguan | Gemini Pro |
| Payment Integration | QRIS for subscription | Midtrans API |

**Deliverable:** 50 paid users

### Phase 3: Scale (Week 9-13) — "Competition Ready"
**Goal:** 500 users, Rp 15 juta MRR, polished demo

| Feature | Description | Google Cloud |
|---------|-------------|-------------|
| Smart Recommendations | Rekomendasi produk | Vertex AI |
| Multi-language | Bahasa + English | Gemini Pro |
| Marketing Scheduler | Auto-post konten | Cloud Functions |
| Advanced Analytics | Predictive insights | Vertex AI |

**Deliverable:** Full product + 3-min demo video

---

## 📱 WhatsApp Integration Flow

### Customer Journey
```
Toko Daftar → Setup Profil → Connect WA → Mulai AI Handle
     │              │              │              │
     ▼              ▼              ▼              ▼
  Onboarding    Set products    Link WA bot    Auto-reply
  (5 min)       (10 min)        (2 min)        dimulai!
```

### AI Agent Flow (Customer Side)
```
Customer: "Kak, ada tasLouis Vuitton yang harganya berapa?"

AI Agent:
1. Gemini Pro analyze → intent: product inquiry
2. Firestore query → find "Louis Vuitton" products
3. Gemini Pro generate → natural response
4. Send via WhatsApp → "Halo Kak! 😊 Untuk Louis Vuitton Neverfull, 
   harganya Rp 18.500.000. Ada diskon 5% untuk pembelian hari ini!"

If out of stock:
"Maaf Kak, Louis Vuitton Neverfull lagi kosong. 
Kami bisa kabarin kalau sudah restok ya? 📱"
```

### Store Owner Flow
```
Store Owner via WA: "Stok tas LV berapa?"

AI Agent:
1. Gemini Pro analyze → intent: inventory check
2. Firestore query → get stock levels
3. Gemini Pro generate → formatted response
4. Send: "📦 Stok Tas LV:
   - Neverfull MM: 3 unit ✅
   - Speedy 25: 0 unit ❌ (habis)
   - Alma BB: 2 unit ✅
   
   ⚠️ Neverfull tinggal 3, mungkin perlu restok!"
```

---

## 🎬 Demo Video Script (3 minutes)

### Scene 1: Problem (0:00 - 0:30)
```
[Screen: Toko UMKM ramai, owner sibuk handle 5 customer sekaligus]
Narrator: "65 juta UMKM di Indonesia kekurangan karyawan.
Satu orang owner handle semuanya: jualan, chat customer, kelola stok..."
[Show: Chat masuk 20+, owner kewalahan]
```

### Scene 2: Solution (0:30 - 1:30)
```
[Screen: UMKM Copilot dashboard]
Narrator: "UMKM Copilot adalah AI agent yang handle SEMUA itu."
[Show: WhatsApp conversation - AI jawab customer]
[Show: Dashboard - inventory update real-time]
[Show: AI generate konten marketing otomatis]
```

### Scene 3: AI in Action (1:30 - 2:30)
```
[Screen: Split view - Customer chat left, AI reasoning right]
Narrator: "Gemini AI menganalisis setiap percakapan:
- Intent recognition untuk routing
- Context-aware responses
- Multi-modal: teks + gambar"
[Show: AI handle 3 customer berbeda sekaligus]
```

### Scene 4: Results (2:30 - 3:00)
```
[Screen: Dashboard analytics]
Narrator: "Hasil nyata untuk toko:
- 3 jam/hari hemat waktu
- 25% penjualan naik
- 100% customer puas"
[Show: Revenue graph, user testimonials]
"UMKM Copilot. Toko pintar, tanpa karyawan AI."
```

---

## 📊 Google Cloud Cost Estimate (90 days)

| Service | Usage/Month | Cost/Month |
|---------|------------|------------|
| Gemini API | 100K requests | ~$50 |
| Cloud Vision | 10K images | ~$15 |
| Cloud Run | 100K requests | ~$20 |
| Firestore | 10GB storage | ~$18 |
| Cloud Functions | 50K invocations | ~$10 |
| Cloud Storage | 5GB | ~$0.10 |
| **Total** | | **~$113/month** |

**Free tier credits:** Google Cloud provides $300 free credits → covers first 2+ months

---

## 🏆 Competitive Advantage

### Why UMKM Copilot Wins
1. **65M market** — largest UMKM population in SEA
2. **WhatsApp-native** — zero friction, no app install
3. **AI-first** — not a feature, the entire product IS AI
4. **Revenue from day 1** — clear monetization
5. **Google Cloud deep integration** — not bolt-on, architecturally essential
6. **Real impact** — measurably saves time + increases revenue

### What Makes AI "Architecturally Essential" (Bolt-on Test)
- **Remove AI = product breaks** — no human can handle 24/7 customer service for 500 toko
- **Remove AI = no smart responses** — can't do intent recognition, context-aware replies
- **Remove AI = no automation** — can't predict inventory, generate content, analyze sales
- **The AI IS the product** — UMKM Copilot without AI is just a spreadsheet

---

## 📅 Hackathon Timeline

| Date | Milestone | Status |
|------|-----------|--------|
| May 19, 2026 | Submission opens | 🟢 START |
| May 19 - Jun 8 | Phase 1: MVP build | ⬜ |
| Jun 9 - Jun 30 | Phase 2: Beta launch + users | ⬜ |
| Jul 1 - Jul 21 | Phase 3: Scale + polish | ⬜ |
| Jul 22 - Aug 10 | Video recording + docs | ⬜ |
| Aug 11 - Aug 17 | Final submission | ⬜ DEADLINE |
| Aug 18 - Sep 15 | Judging period | ⏳ |
| Sep 25 | Winners announced | 🏆 |

---

## 📝 Submission Requirements Checklist

- [ ] GitHub repo (public or shared with devpost)
- [ ] Working demo (deployed URL)
- [ ] Video demo (< 3 minutes)
- [ ] Text description (how AI transforms workflows)
- [ ] Google Cloud product(s) used (list all)
- [ ] Business model explanation
- [ ] Revenue proof (if any)
- [ ] Category selection (Small Business Services)

---

## 🎯 Success Metrics (90 Days)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Total Users | 500+ | Registration count |
| Paid Users | 150+ | Subscription count |
| MRR | Rp 15 juta+ | Payment records |
| AI Conversations | 50K+ | API usage logs |
| Customer Satisfaction | 4.5+ stars | In-app rating |
| Time Saved/User | 2+ hrs/day | User survey |

---

*Blueprint v1.0 — Build with Gemini XPRIZE Hackathon*
*Created: June 23, 2026*
