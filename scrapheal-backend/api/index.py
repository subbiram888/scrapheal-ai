import os
import json
import asyncio
import re
from typing import Any, Dict
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from google import genai


# =========================================================
# CONFIG
# =========================================================

load_dotenv()

BRIGHT_DATA_API_TOKEN = os.getenv("BRIGHT_DATA_API_TOKEN")
BRIGHT_DATA_COLLECTOR_ID = os.getenv("BRIGHT_DATA_COLLECTOR_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

TRIGGER_URL = "https://api.brightdata.com/dca/trigger"
RESULT_URL = "https://api.brightdata.com/dca/dataset"
HEAL_URL = "https://api.brightdata.com/dca/collector"


# =========================================================
# GEMINI
# =========================================================

gemini = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="ScrapeHeal AI",
    description="AI-powered self-healing web extraction using Bright Data and Gemini",
    version="4.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# =========================================================
# URL CLEANING
# =========================================================

def clean_url(value: str) -> str:
    """
    Clean and validate URL before sending it to Bright Data.
    Removes newline, tab, carriage return and other
    non-printable ASCII characters.
    """

    if not value:
        raise ValueError("URL is required")

    # Remove leading/trailing whitespace
    value = value.strip()

    # Remove non-printable ASCII characters
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)

    # Final trim
    value = value.strip()

    parsed = urlparse(value)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            "URL must start with http:// or https://"
        )

    if not parsed.netloc:
        raise ValueError("Invalid URL")

    return value


# =========================================================
# REQUEST MODEL
# =========================================================

class ScrapeRequest(BaseModel):

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return clean_url(value)


# =========================================================
# BRIGHT DATA EXTRACTION
# =========================================================

async def run_bright_data_collector(
    url: str,
) -> Dict[str, Any]:

    if not BRIGHT_DATA_API_TOKEN:
        raise Exception(
            "BRIGHT_DATA_API_TOKEN is missing."
        )

    if not BRIGHT_DATA_COLLECTOR_ID:
        raise Exception(
            "BRIGHT_DATA_COLLECTOR_ID is missing."
        )

    # Always clean again before sending to Bright Data
    url = clean_url(url)

    headers = {
        "Authorization": f"Bearer {BRIGHT_DATA_API_TOKEN}",
        "Content-Type": "application/json",
    }

    trigger_endpoint = (
        f"{TRIGGER_URL}"
        f"?collector={BRIGHT_DATA_COLLECTOR_ID}"
        f"&queue_next=1"
    )

    async with httpx.AsyncClient(
        timeout=90.0
    ) as client:

        response = await client.post(
            trigger_endpoint,
            headers=headers,
            json=[
                {
                    "url": url
                }
            ],
        )

        if response.status_code not in [
            200,
            201,
            202,
        ]:
            raise Exception(
                f"Bright Data trigger failed: "
                f"{response.text}"
            )

        trigger_data = response.json()

        collection_id = (
            trigger_data.get("collection_id")
            or trigger_data.get("id")
            or trigger_data.get("snapshot_id")
        )

        if not collection_id:
            raise Exception(
                "Bright Data did not return a collection ID: "
                f"{trigger_data}"
            )

        # =================================================
        # POLL RESULT
        # =================================================

        result_endpoint = (
            f"{RESULT_URL}?id={collection_id}"
        )

        for _ in range(45):

            result_response = await client.get(
                result_endpoint,
                headers=headers,
            )

            if result_response.status_code == 200:

                try:
                    data = result_response.json()
                except Exception:
                    data = result_response.text

                return {
                    "collection_id": collection_id,
                    "data": data,
                }

            if result_response.status_code in [
                202,
                404,
            ]:
                await asyncio.sleep(2)
                continue

            raise Exception(
                f"Bright Data result failed: "
                f"{result_response.text}"
            )

        raise Exception(
            "Bright Data extraction timed out."
        )


# =========================================================
# GEMINI ANALYSIS
# =========================================================

async def analyze_with_gemini(
    data: Any,
) -> Dict[str, Any]:

    if not gemini:
        raise Exception(
            "GEMINI_API_KEY is missing."
        )

    data_text = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    )

    prompt = f"""
You are ScrapeHeal AI, a web extraction reliability engine.

Analyze the scraped JSON data below.

Determine whether the extraction is reliable.

Check for:

1. Missing important fields
2. Null values
3. Empty strings
4. Invalid values
5. Type inconsistencies
6. Broken or malformed records
7. Unexpected HTML
8. Inconsistent structure
9. Suspicious extraction results

Do not invent an anomaly.

If the data is valid, say it is valid.

If an anomaly exists, explain it clearly.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "is_valid": true,
  "confidence": 95,
  "risk_level": "low",
  "issues": [],
  "explanation": "The extracted data is structurally consistent.",
  "repair_instruction": "",
  "recommended_action": "accept"
}}

For invalid data:

{{
  "is_valid": false,
  "confidence": 90,
  "risk_level": "medium",
  "issues": [
    "Price field is missing"
  ],
  "explanation": "The extraction contains a missing required field.",
  "repair_instruction": "Re-extract the price field from the product page.",
  "recommended_action": "repair"
}}

DATA:

{data_text[:30000]}
"""

    response = await asyncio.to_thread(
        gemini.models.generate_content,
        model="gemini-2.0-flash",
        contents=prompt,
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = (
            text.replace("```json", "")
            .replace("```", "")
            .strip()
        )

    try:
        analysis = json.loads(text)

    except Exception:
        raise Exception(
            f"Gemini returned invalid JSON: {text}"
        )

    return {
        "is_valid": bool(
            analysis.get("is_valid", False)
        ),
        "confidence": int(
            analysis.get("confidence", 0)
        ),
        "risk_level": analysis.get(
            "risk_level",
            "unknown",
        ),
        "issues": analysis.get(
            "issues",
            [],
        ),
        "explanation": analysis.get(
            "explanation",
            "",
        ),
        "repair_instruction": analysis.get(
            "repair_instruction",
            "",
        ),
        "recommended_action": analysis.get(
            "recommended_action",
            "review",
        ),
    }


# =========================================================
# BRIGHT DATA HEAL
# =========================================================

async def heal_bright_data_collector(
    collector_id: str,
    instruction: str,
) -> bool:

    if not BRIGHT_DATA_API_TOKEN:
        return False

    if not collector_id:
        return False

    endpoint = (
        f"{HEAL_URL}/{collector_id}/heal"
    )

    headers = {
        "Authorization":
            f"Bearer {BRIGHT_DATA_API_TOKEN}",
        "Content-Type":
            "application/json",
    }

    payload = {
        "instructions": instruction,
        "auto_deploy": True,
    }

    async with httpx.AsyncClient(
        timeout=90.0
    ) as client:

        response = await client.post(
            endpoint,
            headers=headers,
            json=payload,
        )

        return response.status_code in [
            200,
            201,
            202,
        ]


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "name": "ScrapeHeal AI",
        "status": "online",
        "version": "4.0.0",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",

        "bright_data": bool(
            BRIGHT_DATA_API_TOKEN
            and BRIGHT_DATA_COLLECTOR_ID
        ),

        "gemini": bool(
            GEMINI_API_KEY
        ),
    }


# =========================================================
# CONFIG DIAGNOSTICS
# =========================================================

@app.get("/config")
def config():

    collector = (
        BRIGHT_DATA_COLLECTOR_ID or ""
    ).strip()

    return {
        "bright_data_token_present": bool(
            BRIGHT_DATA_API_TOKEN
        ),

        "collector_present": bool(
            collector
        ),

        "collector_format_valid": collector.startswith(
            "c_"
        ),

        "collector_preview": (
            collector[:8] + "..."
            if collector
            else ""
        ),

        "gemini_key_present": bool(
            GEMINI_API_KEY
        ),
    }


# =========================================================
# SELF HEAL
# =========================================================

@app.post("/self-heal")
async def self_heal(
    request: ScrapeRequest,
):

    history = []

    attempts = 0

    try:

        # =================================================
        # IMPORTANT FIX
        # =================================================

        # Clean the URL BEFORE using it.
        # This fixes:
        #
        # Invalid non-printable ASCII character in URL
        #
        # and:
        #
        # cannot access local variable 'target_url'
        #
        target_url = clean_url(request.url)

        # =================================================
        # ATTEMPT 1 - INITIAL EXTRACTION
        # =================================================

        attempts += 1

        history.append({
            "step": len(history) + 1,
            "action": "bright_data_extraction",
            "status": "running",
        })

        first_result = (
            await run_bright_data_collector(
                target_url
            )
        )

        current_data = first_result["data"]

        history[-1]["status"] = "completed"

        # =================================================
        # GEMINI DIAGNOSIS
        # =================================================

        history.append({
            "step": len(history) + 1,
            "action": "gemini_diagnosis",
            "status": "running",
        })

        analysis = await analyze_with_gemini(
            current_data
        )

        history[-1]["status"] = "completed"

        # =================================================
        # DATA IS VALID
        # =================================================

        if analysis["is_valid"]:

            history.append({
                "step": len(history) + 1,
                "action": "verification_completed",
                "status": "verified",
            })

            return {
                "status": "success",
                "attempts": attempts,
                "url": target_url,
                "final_data": current_data,
                "analysis": analysis,
                "history": history,
            }

        # =================================================
        # ANOMALY FOUND
        # =================================================

        history.append({
            "step": len(history) + 1,
            "action": "anomaly_detected",
            "status": "detected",
            "issues": analysis["issues"],
        })

        repair_instruction = (
            analysis.get(
                "repair_instruction"
            )
            or "Repair the detected extraction issues."
        )

        # =================================================
        # REPAIR
        # =================================================

        history.append({
            "step": len(history) + 1,
            "action": "repair_requested",
            "status": "running",
        })

        healed = (
            await heal_bright_data_collector(
                BRIGHT_DATA_COLLECTOR_ID,
                repair_instruction,
            )
        )

        if not healed:

            history[-1]["status"] = "failed"

            return {
                "status": "failed",
                "attempts": attempts,
                "url": target_url,
                "final_data": current_data,
                "analysis": analysis,
                "history": history,
            }

        history[-1]["status"] = "completed"

        # =================================================
        # ATTEMPT 2 - RE-EXTRACTION
        # =================================================

        attempts += 1

        history.append({
            "step": len(history) + 1,
            "action": "bright_data_re_extraction",
            "status": "running",
        })

        second_result = (
            await run_bright_data_collector(
                target_url
            )
        )

        repaired_data = second_result["data"]

        history[-1]["status"] = "completed"

        # =================================================
        # GEMINI VERIFICATION
        # =================================================

        history.append({
            "step": len(history) + 1,
            "action": "post_repair_verification",
            "status": "running",
        })

        final_analysis = (
            await analyze_with_gemini(
                repaired_data
            )
        )

        # =================================================
        # SUCCESS
        # =================================================

        if final_analysis["is_valid"]:

            history[-1]["status"] = "verified"

            return {
                "status": "self_healed",
                "attempts": attempts,
                "url": target_url,
                "final_data": repaired_data,
                "analysis": final_analysis,
                "history": history,
            }

        # =================================================
        # REPAIR FAILED
        # =================================================

        history[-1]["status"] = "failed"

        return {
            "status": "failed",
            "attempts": attempts,
            "url": target_url,
            "final_data": repaired_data,
            "analysis": final_analysis,
            "history": history,
        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "attempts": attempts,
                "history": history,
            },
        )

    except Exception as e:

        history.append({
            "step": len(history) + 1,
            "action": "pipeline_error",
            "status": "failed",
        })

        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "attempts": attempts,
                "history": history,
            },
        )
