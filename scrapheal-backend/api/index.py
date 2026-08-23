import os
import json
import asyncio
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
# CORS CONFIGURATION - VERCEL FIX
# =========================================================

# Allow requests from:
# 1. All Vercel preview/production domains
# 2. Local development
# 3. Any subdomain during testing

ALLOWED_ORIGINS = [
    # Local development
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    
    # Vercel production (update with your actual domain)
    "https://scrapheal-ai.vercel.app",
    
    # Vercel preview deployments (allow all *.vercel.app)
    # Note: These are regex patterns
]

# More permissive CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="http.*localhost.*|.*\.vercel\.app",  # Allow localhost and all Vercel domains
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    max_age=3600,
)

# Alternatively, for strict production use:
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=ALLOWED_ORIGINS,
#     allow_credentials=False,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# =========================================================
# REQUEST MODEL
# =========================================================

class ScrapeRequest(BaseModel):
    url: str


# =========================================================
# BRIGHT DATA SCRAPER
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

        # -------------------------------------------------
        # TRIGGER
        # -------------------------------------------------

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
                f"Bright Data did not return a collection ID: "
                f"{trigger_data}"
            )

        # -------------------------------------------------
        # POLL RESULT
        # -------------------------------------------------

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
You are ScrapeHeal AI, a web extraction reliability
engine.

Analyze the scraped JSON data below.

Determine whether the extraction is actually reliable.

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

IMPORTANT:

Do not invent an anomaly.

If the data is valid, say it is valid.

If an anomaly exists, clearly explain it.

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
        text = text.replace(
            "```json",
            "",
        ).replace(
            "```",
            "",
        ).strip()

    try:
        analysis = json.loads(text)
    except Exception:
        raise Exception(
            f"Gemini returned invalid JSON: {text}"
        )

    # -----------------------------------------------------
    # NORMALIZE
    # -----------------------------------------------------

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
# HEALTH
# =========================================================

@app.get("/")
def home():

    return {
        "name": "ScrapeHeal AI",
        "status": "online",
        "version": "4.0.0",
    }


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
                request.url
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
            "status": "completed",
        })

        analysis = await analyze_with_gemini(
            current_data
        )

        # =================================================
        # VALID DATA
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

                "final_data": current_data,

                "analysis": analysis,

                "history": history,
            }

        history[-1]["status"] = "completed"

        # =================================================
        # ATTEMPT 2 - AFTER REPAIR
        # =================================================

        attempts += 1

        history.append({
            "step": len(history) + 1,
            "action": "bright_data_re_extraction",
            "status": "running",
        })

        second_result = (
            await run_bright_data_collector(
                request.url
            )
        )

        repaired_data = second_result["data"]

        history[-1]["status"] = "completed"

        # =================================================
        # VERIFY REPAIRED DATA WITH GEMINI
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
        # REPAIR SUCCESS
        # =================================================

        if final_analysis["is_valid"]:

            history[-1]["status"] = "verified"

            return {
                "status": "self_healed",

                "attempts": attempts,

                "final_data": repaired_data,

                "analysis": final_analysis,

                "history": history,
            }

        # =================================================
        # REPAIR DID NOT FIX DATA
        # =================================================

        history[-1]["status"] = "failed"

        return {
            "status": "failed",

            "attempts": attempts,

            "final_data": repaired_data,

            "analysis": final_analysis,

            "history": history,
        }

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
