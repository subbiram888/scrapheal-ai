import os
import re
import json
import asyncio
from typing import Any, Dict
from urllib.parse import urlparse, urlencode

import httpx
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, field_validator

from google import genai


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()


# =========================================================
# ENVIRONMENT CLEANING
# =========================================================

def clean_env(value: str | None) -> str:
    """
    Remove whitespace and non-printable ASCII characters
    such as \\n, \\r and tabs.

    This prevents the Bright Data URL error:
    Invalid non-printable ASCII character in URL.
    """

    if not value:
        return ""

    value = str(value)

    value = re.sub(
        r"[\x00-\x1f\x7f]",
        "",
        value,
    )

    return value.strip()


BRIGHT_DATA_API_TOKEN = clean_env(
    os.getenv("BRIGHT_DATA_API_TOKEN")
)

BRIGHT_DATA_COLLECTOR_ID = clean_env(
    os.getenv("BRIGHT_DATA_COLLECTOR_ID")
)

GEMINI_API_KEY = clean_env(
    os.getenv("GEMINI_API_KEY")
)


# =========================================================
# GEMINI MODEL
# =========================================================

GEMINI_MODEL = "gemini-2.5-flash"


# =========================================================
# BRIGHT DATA ENDPOINTS
# =========================================================

TRIGGER_URL = (
    "https://api.brightdata.com/dca/trigger"
)

RESULT_URL = (
    "https://api.brightdata.com/dca/dataset"
)

SELF_HEAL_BASE_URL = (
    "https://api.brightdata.com/dca/collectors"
)


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini = None

if GEMINI_API_KEY:

    gemini = genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="ScrapeHeal AI",
    description=(
        "AI-powered self-healing web extraction "
        "using Bright Data and Gemini"
    ),
    version="4.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://scrapeheal-ai.vercel.app",
    ],

    allow_origin_regex=(
        r"https://.*\.vercel\.app"
    ),

    allow_credentials=False,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ],
)


# =========================================================
# REQUEST MODEL
# =========================================================

class ScrapeRequest(BaseModel):

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(
        cls,
        value: str,
    ) -> str:

        if not value:

            raise ValueError(
                "URL is required."
            )

        # Remove whitespace
        value = value.strip()

        # Remove hidden control characters
        value = re.sub(
            r"[\x00-\x1f\x7f]",
            "",
            value,
        )

        value = value.strip()

        parsed = urlparse(value)

        if parsed.scheme not in (
            "http",
            "https",
        ):

            raise ValueError(
                "URL must start with "
                "http:// or https://"
            )

        if not parsed.netloc:

            raise ValueError(
                "Invalid URL."
            )

        return value


# =========================================================
# COLLECTOR VALIDATION
# =========================================================

def get_clean_collector_id() -> str:

    collector_id = clean_env(
        BRIGHT_DATA_COLLECTOR_ID
    )

    if not collector_id:

        raise Exception(
            "BRIGHT_DATA_COLLECTOR_ID is missing."
        )

    if not collector_id.startswith("c_"):

        raise Exception(
            "Invalid Bright Data Collector ID. "
            "Published Collector IDs should "
            "start with c_."
        )

    return collector_id


# =========================================================
# BRIGHT DATA HEADERS
# =========================================================

def get_bright_data_headers():

    token = clean_env(
        BRIGHT_DATA_API_TOKEN
    )

    if not token:

        raise Exception(
            "BRIGHT_DATA_API_TOKEN is missing."
        )

    return {
        "Authorization": (
            f"Bearer {token}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }


# =========================================================
# BRIGHT DATA EXTRACTION
# =========================================================

async def run_bright_data_collector(
    url: str,
) -> Dict[str, Any]:

    # Clean URL one final time
    url = url.strip()

    url = re.sub(
        r"[\x00-\x1f\x7f]",
        "",
        url,
    )

    url = url.strip()

    # Validate
    parsed = urlparse(url)

    if parsed.scheme not in (
        "http",
        "https",
    ):

        raise Exception(
            "Invalid target URL."
        )

    if not parsed.netloc:

        raise Exception(
            "Invalid target URL."
        )

    collector_id = (
        get_clean_collector_id()
    )

    headers = (
        get_bright_data_headers()
    )

    # IMPORTANT:
    # urlencode prevents hidden characters
    # from corrupting the request URL.
    query = urlencode(
        {
            "collector": collector_id,
            "queue_next": "1",
        }
    )

    trigger_endpoint = (
        f"{TRIGGER_URL}?{query}"
    )

    payload = [
        {
            "url": url
        }
    ]

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        # =================================================
        # TRIGGER
        # =================================================

        response = await client.post(
            trigger_endpoint,
            headers=headers,
            json=payload,
        )

        if response.status_code not in (
            200,
            201,
            202,
        ):

            raise Exception(
                "Bright Data trigger failed: "
                f"{response.text}"
            )

        try:

            trigger_data = (
                response.json()
            )

        except Exception:

            raise Exception(
                "Bright Data returned "
                "invalid JSON: "
                f"{response.text}"
            )

        collection_id = (
            trigger_data.get(
                "collection_id"
            )
            or trigger_data.get("id")
            or trigger_data.get(
                "snapshot_id"
            )
        )

        if not collection_id:

            raise Exception(
                "Bright Data did not return "
                f"a collection ID: {trigger_data}"
            )

        # =================================================
        # POLL DATASET
        # =================================================

        result_endpoint = (
            f"{RESULT_URL}"
            f"?id={collection_id}"
        )

        for _ in range(45):

            result_response = (
                await client.get(
                    result_endpoint,
                    headers=headers,
                )
            )

            if result_response.status_code == 200:

                try:

                    data = (
                        result_response.json()
                    )

                except Exception:

                    data = (
                        result_response.text
                    )

                return {
                    "collection_id": (
                        collection_id
                    ),
                    "data": data,
                }

            if result_response.status_code in (
                202,
                404,
            ):

                await asyncio.sleep(2)

                continue

            raise Exception(
                "Bright Data result failed: "
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

    if gemini is None:

        raise Exception(
            "GEMINI_API_KEY is missing."
        )

    try:

        data_text = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

    except Exception:

        data_text = str(data)

    prompt = f"""
You are ScrapeHeal AI.

You are an AI-powered web extraction
reliability and self-healing engine.

Analyze the extracted web data below.

Your job is to determine whether the
scraped data is reliable.

Check for:

1. Missing important fields
2. Null values
3. Empty strings
4. Invalid values
5. Type inconsistencies
6. Broken records
7. Malformed records
8. Unexpected HTML
9. Inconsistent structure
10. Suspicious extraction results
11. Incomplete extraction

IMPORTANT RULES:

- Do NOT invent problems.
- If the data is valid, mark it valid.
- If there is a real problem, explain it.
- Give a useful repair instruction.
- Return ONLY valid JSON.
- Do not use markdown.
- Do not put JSON inside ``` blocks.

Return exactly this structure:

{{
    "is_valid": true,
    "confidence": 95,
    "risk_level": "low",
    "issues": [],
    "explanation": "The extracted data is valid.",
    "repair_instruction": "",
    "recommended_action": "accept"
}}

If the extraction has problems:

{{
    "is_valid": false,
    "confidence": 90,
    "risk_level": "medium",
    "issues": [
        "Missing important field"
    ],
    "explanation": "The extraction is incomplete.",
    "repair_instruction": "Repair the selector responsible for the missing field.",
    "recommended_action": "repair"
}}

EXTRACTED DATA:

{data_text[:30000]}
"""

    # =====================================================
    # GEMINI 2.5 FLASH
    # =====================================================

    response = await asyncio.to_thread(
        gemini.models.generate_content,

        model=GEMINI_MODEL,

        contents=prompt,
    )

    text = (
        response.text
        if response.text
        else ""
    )

    text = text.strip()

    # Remove accidental markdown fences
    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?",
            "",
            text,
        )

        text = re.sub(
            r"```$",
            "",
            text,
        )

        text = text.strip()

    try:

        analysis = json.loads(
            text
        )

    except Exception:

        raise Exception(
            "Gemini returned invalid JSON: "
            f"{text}"
        )

    return {
        "is_valid": bool(
            analysis.get(
                "is_valid",
                False,
            )
        ),

        "confidence": int(
            analysis.get(
                "confidence",
                0,
            )
        ),

        "risk_level": (
            analysis.get(
                "risk_level",
                "unknown",
            )
        ),

        "issues": (
            analysis.get(
                "issues",
                [],
            )
        ),

        "explanation": (
            analysis.get(
                "explanation",
                "",
            )
        ),

        "repair_instruction": (
            analysis.get(
                "repair_instruction",
                "",
            )
        ),

        "recommended_action": (
            analysis.get(
                "recommended_action",
                "review",
            )
        ),
    }


# =========================================================
# BRIGHT DATA SELF HEALING
# =========================================================

async def heal_bright_data_collector(
    collector_id: str,
    instruction: str,
) -> Dict[str, Any]:

    collector_id = clean_env(
        collector_id
    )

    if not collector_id:

        raise Exception(
            "Collector ID is missing."
        )

    if not collector_id.startswith("c_"):

        raise Exception(
            "Invalid Collector ID."
        )

    instruction = (
        instruction.strip()
        if instruction
        else
        "Repair the extraction selectors "
        "and restore the expected structured "
        "data extraction."
    )

    endpoint = (
        f"{SELF_HEAL_BASE_URL}/"
        f"{collector_id}/"
        f"refactor_template"
    )

    headers = (
        get_bright_data_headers()
    )

    payload = {
        "prompt": instruction,
        "custom_input": [
            {}
        ],
    }

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(
            endpoint,
            headers=headers,
            json=payload,
        )

        if response.status_code not in (
            200,
            201,
            202,
        ):

            raise Exception(
                "Bright Data self-healing "
                "request failed: "
                f"{response.text}"
            )

        try:

            return response.json()

        except Exception:

            return {
                "raw_response":
                    response.text
            }


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def home():

    return {
        "name": "ScrapeHeal AI",
        "status": "online",
        "version": "4.0.0",
        "gemini_model": GEMINI_MODEL,
    }


@app.get("/health")
def health():

    return {
        "status": "healthy",

        "bright_data": bool(
            BRIGHT_DATA_API_TOKEN
        ),

        "collector": bool(
            BRIGHT_DATA_COLLECTOR_ID
        ),

        "gemini": bool(
            GEMINI_API_KEY
        ),

        "gemini_model": GEMINI_MODEL,
    }


# =========================================================
# CONFIG DIAGNOSTICS
# =========================================================

@app.get("/config")
def config():

    collector = clean_env(
        BRIGHT_DATA_COLLECTOR_ID
    )

    return {

        "bright_data_token_present": bool(
            BRIGHT_DATA_API_TOKEN
        ),

        "collector_present": bool(
            collector
        ),

        "collector_format_valid": (
            collector.startswith("c_")
        ),

        "collector_length": len(
            collector
        ),

        "collector_has_newline": (
            "\n" in collector
            or "\r" in collector
        ),

        "collector_preview": (
            collector[:8] + "..."
            if collector
            else ""
        ),

        "gemini_key_present": bool(
            GEMINI_API_KEY
        ),

        "gemini_model": GEMINI_MODEL,
    }


# =========================================================
# SELF HEAL PIPELINE
# =========================================================

@app.post("/self-heal")
async def self_heal(
    request: ScrapeRequest,
):

    history = []

    attempts = 0

    try:

        # =================================================
        # CLEAN TARGET URL
        # =================================================

        target_url = (
            request.url.strip()
        )

        target_url = re.sub(
            r"[\x00-\x1f\x7f]",
            "",
            target_url,
        )

        target_url = (
            target_url.strip()
        )

        # =================================================
        # STEP 1
        # =================================================

        history.append({
            "step": 1,
            "action": "url_validation",
            "status": "completed",
        })

        # =================================================
        # STEP 2
        # =================================================

        attempts += 1

        history.append({
            "step": 2,
            "action": "bright_data_extraction",
            "status": "running",
        })

        first_result = (
            await run_bright_data_collector(
                target_url
            )
        )

        current_data = (
            first_result["data"]
        )

        history[-1]["status"] = (
            "completed"
        )

        # =================================================
        # STEP 3
        # =================================================

        history.append({
            "step": 3,
            "action": "gemini_diagnosis",
            "status": "running",
        })

        analysis = (
            await analyze_with_gemini(
                current_data
            )
        )

        history[-1]["status"] = (
            "completed"
        )

        # =================================================
        # DATA IS VALID
        # =================================================

        if analysis["is_valid"]:

            history.append({
                "step": 4,
                "action": "verification",
                "status": "verified",
            })

            return {

                "status": "success",

                "message": (
                    "Extraction completed "
                    "and verified successfully."
                ),

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
            "step": 4,
            "action": "anomaly_detection",
            "status": "detected",
            "issues": analysis[
                "issues"
            ],
        })

        repair_instruction = (
            analysis.get(
                "repair_instruction",
                "",
            )
        )

        if not repair_instruction:

            repair_instruction = (
                "Repair the extraction selectors "
                "and restore correct structured "
                "data extraction."
            )

        # =================================================
        # STEP 5 - AI REPAIR
        # =================================================

        history.append({
            "step": 5,
            "action": "bright_data_self_healing",
            "status": "running",
        })

        heal_result = (
            await heal_bright_data_collector(
                BRIGHT_DATA_COLLECTOR_ID,
                repair_instruction,
            )
        )

        history[-1]["status"] = (
            "triggered"
        )

        # =================================================
        # STEP 6 - WAIT
        # =================================================

        history.append({
            "step": 6,
            "action": "repair_wait",
            "status": "completed",
        })

        # Give Bright Data some time
        # before re-running extraction.
        await asyncio.sleep(5)

        # =================================================
        # STEP 7 - RE-EXTRACT
        # =================================================

        attempts += 1

        history.append({
            "step": 7,
            "action": "bright_data_re_extraction",
            "status": "running",
        })

        second_result = (
            await run_bright_data_collector(
                target_url
            )
        )

        repaired_data = (
            second_result["data"]
        )

        history[-1]["status"] = (
            "completed"
        )

        # =================================================
        # STEP 8 - FINAL GEMINI VERIFICATION
        # =================================================

        history.append({
            "step": 8,
            "action": "gemini_verification",
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

            history[-1]["status"] = (
                "verified"
            )

            return {

                "status": "self_healed",

                "message": (
                    "ScrapeHeal detected an "
                    "extraction anomaly, "
                    "diagnosed it with Gemini, "
                    "triggered Bright Data repair, "
                    "re-extracted the data, "
                    "and verified the result."
                ),

                "attempts": attempts,

                "url": target_url,

                "initial_analysis": analysis,

                "final_data": repaired_data,

                "analysis": final_analysis,

                "history": history,

                "heal_result": heal_result,
            }

        # =================================================
        # REPAIR DID NOT FIX IT
        # =================================================

        history[-1]["status"] = (
            "failed"
        )

        return {

            "status": "repair_failed",

            "message": (
                "The extraction was repaired "
                "but final verification still "
                "detected anomalies."
            ),

            "attempts": attempts,

            "url": target_url,

            "initial_analysis": analysis,

            "final_data": repaired_data,

            "analysis": final_analysis,

            "history": history,

            "heal_result": heal_result,
        }

    # =====================================================
    # VALIDATION ERROR
    # =====================================================

    except ValueError as e:

        history.append({
            "step": len(history) + 1,
            "action": "validation_error",
            "status": "failed",
        })

        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "attempts": attempts,
                "history": history,
            },
        )

    # =====================================================
    # GENERAL ERROR
    # =====================================================

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