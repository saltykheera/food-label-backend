# 🥗 Food Label Analyzer Backend API

High-performance Python + FastAPI backend for analyzing food product packages and nutrition labels to calculate instant Health Scores using Google Gemini Multimodal Vision AI.

---

## ⚡ Features

- **FastAPI Endpoints**:
  - `POST /api/analyze`: Multimodal food label image analysis and health scoring.
  - `GET /api/health`: Healthcheck, loaded keys count, supported models.
  - `GET /`: Service status and interactive documentation.
- **Scientific Nutritional Health Score (0–100)**: Letter grade (`A`–`E`), NOVA processing group (1–4), positive factors, warning points, and macro/micronutrient highlights.
- **Image Optimization**: Downsamples oversized mobile camera uploads to prevent high network latency while preserving high-contrast text for OCR/vision analysis.
- **Key Rotation & High-Demand Spikes Resiliency**: Automatically cycles through multiple Gemini keys upon encountering rate limits (429) or high-demand spikes (503).

---

## 🔐 Environment Variables

Create a `.env` file (or set in your hosting provider's dashboard):
```env
# Single key or comma-separated keys for auto-rotation
GEMINI_API_KEYS=your_gemini_api_key_1,your_gemini_api_key_2
PORT=8000
```
*(See `.env.example`)*

---

## 🚀 Local Development

1. **Setup & Start**:
   ```bash
   ./run.sh
   ```
   Or manually:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Interactive API Documentation (Swagger)**:
   - Visit: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Docker & Deployment

Deploy to Render, Railway, Fly.io, or Google Cloud Run:
```bash
docker build -t food-label-backend .
docker run -p 8000:8000 --env GEMINI_API_KEYS="your_key" food-label-backend
```
