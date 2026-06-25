# 📱 WhatsApp Webhook Setup Guide

## Arsitektur

```
Customer (WhatsApp) → Meta Cloud API → Webhook (/webhook) → AI Agent → Reply
```

## Langkah-langkah

### 1. Buat Meta Business Account

1. Buka https://business.facebook.com
2. Login dengan Facebook
3. Buat Business Account baru (nama: "UMKM Copilot" atau nama bisnis kamu)
4. Isi informasi bisnis

### 2. Buat WhatsApp Business App

1. Buka https://developers.facebook.com
2. Klik **"Create App"**
3. Pilih **"Business"** sebagai app type
4. Isi:
   - App Name: `UMKM Copilot`
   - Contact Email: email kamu
   - Business Account: pilih yang sudah dibuat tadi
5. Klik **"Create App"**

### 3. Tambah WhatsApp Product

1. Di halaman app, klik **"Add Product"**
2. Cari **"WhatsApp"** → klik **"Set up"**
3. Pilih **"Quick start"** atau **"Continue"**
4. Kamu akan dapat:
   - **Phone Number ID**: `1234567890`
   - **WhatsApp Business Account ID**: `123456789012345`
   - **Temporary Access Token**: `EAAG...`

### 4. Buat Permanent Token

1. Di Meta Business Suite → **Settings** → **Business Settings**
2. **System Users** → Klik **"Add"**
   - Name: `UMKM Bot`
   - Role: `Admin`
3. Klik **"Generate New Token"**
   - Pilih app: `UMKM Copilot`
   - Permissions: `whatsapp_business_messaging`, `whatsapp_business_management`
4. **Copy token** dan simpan (ini permanent token)

### 5. Daftarkan Phone Number

1. Di WhatsApp Manager → **Phone Numbers**
2. Klik **"Add Phone Number"**
3. Isi nama bisnis: `Toko MJF Endin`
4. Masukkan nomor HP yang akan jadi bot
5. Verifikasi via SMS/WhatsApp
6. **Catatan**: Nomor ini TIDAK bisa digunakan di WhatsApp biasa

### 6. Setup Webhook di Meta

1. Buka https://developers.facebook.com
2. Pilih app **"UMKM Copilot"**
3. Di sidebar → **WhatsApp** → **Configuration**
4. Di bagian **Webhook**, klik **"Edit"**
5. Isi:
   - **Callback URL**: `https://umkm-copilot.vercel.app/webhook`
   - **Verify Token**: `umkm-copilot-verify`
6. Klik **"Verify and Save"**
7. Di bagian **Webhook fields**, klik **"Subscribe"** pada:
   - `messages` ✅
   - `messaging_postbacks` ✅

### 7. Set Environment Variables di Vercel

```bash
# Token WhatsApp (permanent token dari step 4)
npx vercel env add WHATSAPP_TOKEN production
# Paste token: EAAG...

# Phone Number ID (dari step 3)
npx vercel env add WHATSAPP_PHONE_NUMBER_ID production
# Isi: 1234567890

# Verify Token (sudah default)
npx vercel env add WHATSAPP_VERIFY_TOKEN production
# Isi: umkm-copilot-verify

# App Secret (dari Meta App Settings)
npx vercel env add WHATSAPP_APP_SECRET production
# Isi: abc123...
```

### 8. Deploy Ulang

```bash
cd /root/umkm-copilot
npx vercel --prod --yes
```

### 9. Test Webhook

#### Test Verifikasi (GET request)
```bash
curl "https://umkm-copilot.vercel.app/webhook?hub.mode=subscribe&hub.verify_token=umkm-copilot-verify&hub.challenge=test123"
# Expected: test123
```

#### Test Kirim Pesan
Buka WhatsApp → Kirim pesan ke nomor bot:
```
Halo
```
Expected: Bot membalas dengan sapaan

```
Ada produk apa?
```
Expected: Bot membalas daftar produk

```
Berapa harga kemeja batik?
```
Expected: Bot membalas harga produk

### 10. Verifikasi di Meta Dashboard

1. Buka https://developers.facebook.com
2. Pilih app → **WhatsApp** → **Configuration**
3. Di bagian **Webhook**, pastikan:
   - Status: ✅ Connected
   - Last delivery: waktu terakhir ada pesan masuk

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Webhook tidak terverifikasi | Cek verify token sama dengan di env var |
| Pesan tidak terkirim | Cek WHATSAPP_TOKEN dan WHATSAPP_PHONE_NUMBER_ID |
| Bot tidak membalas | Cek logs di Vercel: `vercel logs` |
| Error 403 | Token expired, buat token baru |
| Error 400 | Phone number belum terdaftar |

---

## Flow Lengkap

```
1. Customer kirim "Halo" via WhatsApp
   ↓
2. Meta Cloud API terima pesan
   ↓
3. Meta kirim POST ke /webhook
   ↓
4. App proses dengan AI Agent (Gemini)
   ↓
5. App simpan conversation ke database
   ↓
6. App kirim balasan via WhatsApp Cloud API
   ↓
7. Customer terima balasan di WhatsApp
```

---

## API Endpoints

| Endpoint | Method | Fungsi |
|----------|--------|--------|
| `/webhook` | GET | Verifikasi webhook |
| `/webhook` | POST | Terima pesan WhatsApp |
| `/demo` | GET | Halaman demo (public) |
| `/demo/test` | POST | Test AI chat |
| `/` | GET | Dashboard (admin only) |
| `/products` | GET | Kelola produk (admin only) |
| `/analytics` | GET | Analitik (admin only) |
| `/login` | GET/POST | Login admin |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | API key Google Gemini |
| `WHATSAPP_TOKEN` | ⚠️ Untuk production | Permanent token Meta |
| `WHATSAPP_PHONE_NUMBER_ID` | ⚠️ Untuk production | Phone Number ID |
| `WHATSAPP_VERIFY_TOKEN` | ✅ | Token verifikasi webhook |
| `ADMIN_PASSWORD` | ✅ | Password admin dashboard |
| `SECRET_KEY` | ✅ | Flask secret key |
| `GOOGLE_APPLICATION_CREDENTIALS` | ❌ Optional | Service account JSON |
| `FIRESTORE_PROJECT_ID` | ❌ Optional | Firestore project ID |
