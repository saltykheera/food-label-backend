import base64
import io
import logging
from typing import Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from config import key_manager
from gemini_service import call_gemini_multimodal, GEMINI_MODELS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("food_label_backend")

app = FastAPI(
    title="NutriScore - Food Label Analyzer API",
    description="Analyzes food products and nutritional labels to calculate health scores using Gemini Vision AI.",
    version="1.0.0"
)

# Enable CORS for frontend clients (Vercel, local dev, mobile apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def optimize_image(image_bytes: bytes, max_dim: int = 1600) -> tuple[bytes, str]:
    """
    Downsamples large camera photos to a reasonable dimension (max 1600px)
    to reduce network payload and accelerate Gemini inference, returning JPEG bytes and mime type.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert RGBA / CMYK / P to RGB
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            # Downscale if wider or taller than max_dim
            width, height = img.size
            if max(width, height) > max_dim:
                scale = max_dim / max(width, height)
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            output_io = io.BytesIO()
            img.save(output_io, format="JPEG", quality=85, optimize=True)
            return output_io.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning(f"Image optimization skipped due to error: {e}. Using original bytes.")
        return image_bytes, "image/jpeg"

@app.get("/")
async def root():
    """Welcome route with links to docs and healthcheck."""
    return {
        "service": "NutriScore Food Label Analyzer API",
        "status": "online",
        "documentation": "/docs",
        "health": "/api/health",
        "endpoints": {
            "analyze": "POST /api/analyze",
            "health": "GET /api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    """Healthcheck endpoint returning API key status and available models."""
    keys_count = len(key_manager.get_all_keys())
    return {
        "status": "healthy",
        "keys_loaded": keys_count,
        "supported_models": GEMINI_MODELS,
        "message": f"NutriScore backend is running with {keys_count} Gemini keys."
    }

@app.post("/api/analyze")
async def analyze_food(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Receives a food product or nutrition label photo, analyzes it with Gemini,
    and returns nutritional health scoring and analysis.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        pass

    try:
        contents = await file.read()
        if not contents or len(contents) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty or corrupted."
            )
        
        # Max 20MB upload limit
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image exceeds 20MB limit."
            )

        # Optimize image for optimal bandwidth & low-latency Gemini vision processing
        optimized_bytes, mime_type = optimize_image(contents, max_dim=1600)
        image_b64 = base64.b64encode(optimized_bytes).decode("utf-8")

        logger.info(f"Processing image analysis ({len(optimized_bytes)} bytes)...")
        result = await call_gemini_multimodal(image_b64, mime_type=mime_type)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during food analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
