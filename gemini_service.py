import json
import logging
import asyncio
import httpx
from typing import Dict, Any
from config import key_manager

logger = logging.getLogger("food_label_backend")

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]

ANALYSIS_SYSTEM_PROMPT = """
You are an expert clinical nutritionist, food scientist, and consumer health analyst.
Your task is to analyze the provided image of a food product, packaged grocery, beverage, or nutrition facts label.

1. Determine if the image is a food product, beverage, or food nutrition label/ingredients list:
If the image is NOT food-related (e.g. a chair, laptop, car, animal, random object) or is completely unreadable/blurry:
Return STRICT JSON:
{
  "is_food": false,
  "error_message": "Could not identify a clear food product or nutrition label. Please snap a clear photo of the food packaging or nutrition facts."
}

2. If the image IS a food product or label:
Calculate an accurate Health Score from 0 to 100 based on nutritional quality (similar to Nutri-Score and NOVA classification standards):
- Score 80-100 (Grade A): Excellent health profile. Whole foods, single-ingredient or minimally processed, high fiber, high protein, zero or very low added sugars/sodium.
- Score 65-79 (Grade B): Good choice. Generally healthy with minor drawbacks (e.g. moderate sodium or natural sugars).
- Score 50-64 (Grade C): Moderate / Average. Acceptable in moderation; moderate processing or moderate sugars/fats.
- Score 30-49 (Grade D): Poor nutritional value. High in added sugars, saturated fats, sodium, or refined carbs.
- Score 0-29 (Grade E): Unhealthy. Ultra-processed junk food, excessive artificial additives, trans fats, or high sugar/sodium bomb.

Evaluate NOVA processing group:
- Group 1: Unprocessed or minimally processed foods
- Group 2: Processed culinary ingredients
- Group 3: Processed foods
- Group 4: Ultra-processed food products

Return STRICT JSON matching this exact structure:
{
  "is_food": true,
  "product_name": "Identified product name",
  "brand": "Brand name or null",
  "category": "Snacks | Dairy | Beverages | Grains | Produce | Bakery | etc.",
  "health_score": 82,
  "health_grade": "A",
  "verdict": "One clear, punchy sentence explaining the nutritional verdict.",
  "positives": [
    "High dietary fiber (6g per serving)",
    "No added artificial sugars",
    "Clean whole-grain base"
  ],
  "negatives": [
    "Moderate sodium (280mg)",
    "Contains palm oil"
  ],
  "nutritional_highlights": {
    "calories": "160 kcal",
    "serving_size": "40g",
    "sugar": "2g",
    "protein": "5g",
    "fat": "4g",
    "sodium": "180mg",
    "fiber": "4g"
  },
  "nova_group": 3,
  "nova_label": "Processed food",
  "ingredients_summary": "Concise summary of main ingredients and notable additives or lack thereof",
  "allergen_warnings": ["Contains soy", "May contain peanuts"]
}

Important constraints:
- Return ONLY valid JSON.
- Never output markdown conversational text outside the JSON object.
- Be scientifically grounded and objective.
"""

async def call_gemini_multimodal(
    image_base64: str,
    mime_type: str = "image/jpeg"
) -> Dict[str, Any]:
    """
    Sends the image to Gemini multimodal API with automatic key rotation and model fallback.
    """
    keys = key_manager.get_all_keys()
    if not keys:
        raise RuntimeError("No Gemini API keys configured.")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_base64
                        }
                    },
                    {
                        "text": ANALYSIS_SYSTEM_PROMPT
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    last_error = None

    for model in GEMINI_MODELS:
        for attempt in range(len(keys)):
            current_key = key_manager.current_key
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={current_key}"
            
            try:
                async with httpx.AsyncClient(timeout=40.0) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("No response candidates returned by Gemini.")
                    
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise ValueError("Empty content returned by Gemini.")
                    
                    raw_text = parts[0].get("text", "").strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    raw_text = raw_text.strip()

                    parsed_json = json.loads(raw_text)
                    return parsed_json

                elif response.status_code in (429, 403, 503, 500):
                    logger.warning(
                        f"Gemini API returned {response.status_code} on model {model} (key index {key_manager._current_index}). Rotating key..."
                    )
                    key_manager.rotate_key()
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    await asyncio.sleep(1.0)
                    continue
                else:
                    logger.error(f"Gemini API error {response.status_code}: {response.text[:200]}")
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    key_manager.rotate_key()
                    break

            except (httpx.TimeoutException, httpx.RequestError) as e:
                logger.warning(f"Network error on model {model}: {e}. Rotating key...")
                last_error = str(e)
                key_manager.rotate_key()
                await asyncio.sleep(0.5)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                last_error = f"Malformed JSON: {e}"
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_error = str(e)

    raise RuntimeError(f"All Gemini API requests failed. Last error: {last_error}")
