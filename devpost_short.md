## Accomplishments that we're proud of

- Built a working WhatsApp AI agent in 48 hours using Gemini 2.5 Flash
- True bilingual support (Indonesian + English) with auto-detection and code-switching
- Photo-to-Product AI: take a photo → AI extracts name, price, description, stock automatically
- Zero-friction: no app install needed, works directly on WhatsApp
- Production-ready architecture with rate limiting, fallback AI, and Firestore persistence
- Fully eligible for Gemini XPRIZE (Google Cloud Stack + underserved population impact)

## What we learned

- WhatsApp is the ultimate distribution channel in Southeast Asia — no app install = no friction
- Gemini handles Indonesian-English code-switching remarkably well
- AI Vision + LLM combo: pass raw image data to Gemini for structured output instead of perfecting OCR
- Local fallback AI is essential — keeps the system working 99.9% even when API is rate-limited
- UMKM owners need one thing done well, not a feature-heavy platform
- Serverless (Vercel) is perfect for MVP — zero server management, free tier

## What's next for UMKM COPILOT

- Production WhatsApp token + real phone number (remove test limitations)
- Multi-tenant platform: one bot serves thousands of UMKM shops simultaneously
- Payment integration: QRIS, GoPay, OVO directly in chat
- Voice message support — customer sends voice note, AI responds
- Sales analytics dashboard with peak hours, popular products, revenue trends
- Expand to Thailand, Vietnam, Philippines (WhatsApp-heavy markets)
- Partner with Tokopedia, Shopee, Lazada for inventory sync
