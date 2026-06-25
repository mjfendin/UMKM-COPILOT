## Explain the underlying business model of your submission.

UMKM Copilot operates on a **B2C SaaS freemium model** targeting Indonesia's 64 million micro, small, and medium enterprises (UMKM).

**How it works:**

A small business owner (e.g., a warung, batik shop, or clothing store) connects their WhatsApp number to UMKM Copilot. When customers send messages — asking about products, checking prices, placing orders — our AI agent (powered by Gemini 2.5 Flash) responds automatically in Indonesian or English, 24/7.

**Revenue Model — Four Tiers:**

| Tier | Price | Features |
|------|-------|----------|
| **Free** | Rp 0/month | 10 AI conversations/day, 5 products, basic dashboard |
| **Starter** | Rp 49,000/month (~$3) | 100 conversations/day, 50 products, full analytics |
| **Pro** | Rp 99,000/month (~$6) | Unlimited conversations, unlimited products, priority support |
| **Business** | Rp 199,000/month (~$12) | Multi-staff, API integrations, white-label, dedicated support |

**Why this model works:**

1. **Zero-friction distribution**: Customers interact via WhatsApp — the app 87% of Indonesians already use daily. No app install, no new platform to learn.

2. **Natural upsell path**: Shop owners start free, see results (fewer missed messages, faster responses), then upgrade to handle more volume and unlock features.

3. **Low cost structure**: Serverless infrastructure (Vercel) + pay-per-use AI (Gemini API) means near-zero marginal cost per customer. Profitability from day one.

4. **Network effects**: As more UMKM join, we build the largest Indonesian SMB AI dataset — improving response quality, enabling benchmarking, and creating switching costs.

5. **Expansion revenue**: Payment processing (QRIS, GoPay), e-commerce integration (Tokopedia, Shopee), and white-label licensing create additional revenue streams beyond subscriptions.

**Unit Economics:**

| Metric | Value |
|--------|-------|
| Customer Acquisition Cost (CAC) | ~$0 (organic via WhatsApp) |
| Monthly Cost per User | ~$0.50 (API + hosting) |
| Average Revenue per User (ARPU) | ~$5/month (blended) |
| Gross Margin | ~90% |
| Lifetime Value (LTV) | ~$60 (12-month avg retention) |
| LTV:CAC Ratio | ~120:1 |

**Market Size:**

- **TAM** (Total Addressable Market): 64M UMKM × $36/year avg = **$2.3 billion**
- **SAM** (Serviceable Addressable Market): 10M digital-ready UMKM × $36 = **$360 million**
- **SOM** (Serviceable Obtainable Market — Year 5): 150K paying customers × $60/year = **$9 million ARR**

The model is designed to be **self-sustaining from month one** — no external funding required. Revenue from early adopters covers infrastructure costs, and growth funds further development.

---

### Bahasa Indonesia (Arti)

UMKM Copilot beroperasi dengan model **B2C SaaS freemium** yang menargetkan 64 juta UMKM Indonesia.

**Cara kerja:**

Pemilik bisnis kecil (warung, toko batik, atau toko pakaian) menghubungkan nomor WhatsApp mereka ke UMKM Copilot. Ketika pelanggan mengirim pesan — menanyakan produk, cek harga, pesan barang — agen AI kami (Gemini 2.5 Flash) merespon otomatis dalam Bahasa Indonesia atau English, 24/7.

**Model Pendapatan — Empat Tier:**

| Tier | Harga | Fitur |
|------|-------|-------|
| **Free** | Rp 0/bulan | 10 percakapan AI/hari, 5 produk |
| **Starter** | Rp 49.000/bulan (~$3) | 100 percakapan/hari, 50 produk |
| **Pro** | Rp 99.000/bulan (~$6) | Tanpa batas percakapan & produk |
| **Business** | Rp 199.000/bulan (~$12) | Multi-staff, API, white-label |

**Kenapa model ini works:**

1. **Distribusi zero-friction**: Pelanggan chat via WhatsApp — aplikasi yang sudah dipakai 87% orang Indonesia
2. **Natural upsell**: Mulai gratis → lihat hasil → upgrade untuk fitur lebih
3. **Biaya rendah**: Serverless + pay-per-use AI → margin kotor ~90%
4. **Network effect**: Semakin banyak UMKM → dataset lebih besar → AI lebih pintar
5. **Ekspansi revenue**: Payment processing, e-commerce integration, white-label

**Unit Economics:**

| Metrik | Nilai |
|--------|-------|
| Customer Acquisition Cost | ~$0 (organic via WhatsApp) |
| Biaya per User/bulan | ~$0.50 |
| Revenue per User/bulan | ~$5 (blended) |
| Gross Margin | ~90% |
| Lifetime Value | ~$60 |
| LTV:CAC Ratio | ~120:1 |

**Ukuran Pasar:**

- **TAM**: 64M UMKM × $36/tahun = **$2.3 miliar**
- **SAM**: 10M UMKM digital-ready × $36 = **$360 juta**
- **SOM (Year 5)**: 150K pelanggan × $60/tahun = **$9 juta ARR**
