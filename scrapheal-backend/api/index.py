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
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# ENVIRONMENT CLEANING
# =========================================================

def clean_env_value(value: str | None) -> str:
    """
    Remove hidden newline, tab, carriage-return and other
    non-printable ASCII characters from environment values.
    """

    if not value:
        return ""

    value = str(value)

    # Remove all ASCII control characters
    value = re.sub(
        r"[\x00-\x1f\x7f]",
        "",
        value,
    )

    return value.strip()


BRIGHT_DATA_API_TOKEN = clean_env_value(
    os.getenv("BRIGHT_DATA_API_TOKEN")
)

BRIGHT_DATA_COLLECTOR_ID = clean_env_value(
    os.getenv("BRIGHT_DATA_COLLECTOR_ID")
)

GEMINI_API_KEY = clean_env_value(
    os.getenv("GEMINI_API_KEY")
)


# =========================================================
# BRIGHT DATA ENDPOINTS
# =========================================================

BRIGHT_DATA_TRIGGER_URL = (
    "https://api.brightdata.com/dca/trigger"
)

BRIGHT_DATA_DATASET_URL = (
    "https://api.brightdata.com/dca/dataset"
)

BRIGHT_DATA_SELF_HEAL_URL = (
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
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)"
        r"(:\d+)?"
        r"|https://.*\.vercel\.app"
    ),
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
    Clean and validate a URL.

    This specifically prevents errors such as:

    Invalid non-printable ASCII character in URL,
    '\\n' at position 82
    """

    if value is None:
        raise ValueError(
            "URL is required"
        )

    value = str(value)

    # Remove leading/trailing whitespace
    value = value.strip()

    # Remove newline, tab, carriage return and other
    # non-printable ASCII characters
    value = re.sub(
        r"[\x00-\x1f\x7f]",
        "",
        value,
    )

    value = value.strip()

    if not value:
        raise ValueError(
            "URL is required"
        )

    parsed = urlparse(value)

    if parsed.scheme.lower() not in (
        "http",
        "https",
    ):
        raise ValueError(
            "URL must start with http:// or https://"
        )

    if not parsed.netloc:
        raise ValueError(
            "Invalid URL"
        )

    return value


# =========================================================
# COLLECTOR ID VALIDATION
# =========================================================

def clean_collector_id(value: str) -> str:
    """
    Clean and validate the Bright Data Collector ID.
    Published Scraper Studio collector IDs start with c_.
    """

    value = clean_env_value(value)

    if not value:
        raise ValueError(
            "BRIGHT_DATA_COLLECTOR_ID is missing."
        )

    if not value.startswith("c_"):
        raise ValueError(
            "Invalid BRIGHT_DATA_COLLECTOR_ID. "
            "A published Bright Data Scraper Studio "
            "Collector ID should begin with c_."
        )

    return value


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

        return clean_url(value)


# =========================================================
# BRIGHT DATA HEADERS
# =========================================================

def bright_data_headers() -> Dict[str, str]:

    token = clean_env_value(
        BRIGHT_DATA_API_TOKEN
    )

    if not token:
        raise ValueError(
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
    target_url: str,
) -> Dict[str, Any]:

    # Clean URL again immediately before
    # sending it to Bright Data.
    target_url = clean_url(
        target_url
    )

    collector_id = clean_collector_id(
        BRIGHT_DATA_COLLECTOR_ID
    )

    headers = bright_data_headers()

    # IMPORTANT:
    # urlencode prevents an invalid collector ID
    # from becoming an invalid HTTP URL.
    query = urlencode(
        {
            "collector": collector_id,
            "queue_next": "1",
        }
    )

    trigger_url = (
        f"{BRIGHT_DATA_TRIGGER_URL}"
        f"?{query}"
    )

    payload = [
        {
            "url": target_url
        }
    ]

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        # =================================================
        # TRIGGER COLLECTOR
        # =================================================

        response = await client.post(
            trigger_url,
            headers=headers,
            json=payload,
        )

        if response.status_code not in (
            200,
            201,
            202,
        ):

            error_text = response.text

            raise Exception(
                "Bright Data trigger failed: "
                f"{error_text}"
            )

        try:

            trigger_data = response.json()

        except Exception:

            raise Exception(
                "Bright Data returned an invalid "
                "JSON response: "
                f"{response.text}"
            )

        collection_id = (
            trigger_data.get(
                "collection_id"
            )
        )

        if not collection_id:

            raise Exception(
                "Bright Data did not return "
                "collection_id: "
                f"{trigger_data}"
            )

        # =================================================
        # POLL DATASET
        # =================================================

        dataset_url = (
            f"{BRIGHT_DATA_DATASET_URL}"
            f"?id={collection_id}"
        )

        max_attempts = 36

        for poll_number in range(
            max_attempts
        ):

            dataset_response = (
                await client.get(
                    dataset_url,
                    headers=headers,
                )
            )

            if dataset_response.status_code == 200:

                try:

                    data = (
                        dataset_response.json()
                    )

                except Exception:

                    data = (
                        dataset_response.text
                    )

                # Bright Data returns a JSON array
                # when the dataset is ready.
                if isinstance(data, list):

                    return {
                        "collection_id": (
                            collection_id
                        ),
                        "data": data,
                    }

                # Still building
                await asyncio.sleep(5)
                continue

            if dataset_response.status_code in (
                202,
                404,
            ):

                await asyncio.sleep(5)
                continue

            raise Exception(
                "Bright Data dataset request failed: "
                f"{dataset_response.text}"
            )

        raise Exception(
            "Bright Data extraction timed out "
            "while waiting for the dataset."
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
You are ScrapeHeal AI, an AI-powered
web extraction reliability engine.

Your job is to inspect extracted web data
and determine whether the extraction is trustworthy.

Check for:

1. Missing important fields
2. Empty values
3. Null values
4. Invalid values
5. Broken records
6. Inconsistent structure
7. Unexpected HTML
8. Wrong data types
9. Suspicious extraction patterns
10. Incomplete extraction

IMPORTANT:

Do not invent an anomaly.

If the data looks correct, mark it valid.

If there is a real anomaly, explain it
and provide a repair instruction.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "is_valid": true,
    "confidence": 95,
    "risk_level": "low",
    "issues": [],
    "explanation": "The extracted data is valid.",
    "repair_instruction": "",
    "recommended_action": "accept"
}}

For invalid data:

{{
    "is_valid": false,
    "confidence": 90,
    "risk_level": "medium",
    "issues": [
        "Important field is missing"
    ],
    "explanation": "The extraction is incomplete.",
    "repair_instruction": "Fix the selector for the missing field.",
    "recommended_action": "repair"
}}

EXTRACTED DATA:

{data_text[:30000]}
"""

    response = await asyncio.to_thread(
        gemini.models.generate_content,
        model="gemini-2.0-flash",
        contents=prompt,
    )

    text = (
        response.text
        if response.text
        else ""
    ).strip()

    # Remove markdown JSON fences
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

    collector_id = clean_collector_id(
        collector_id
    )

    instruction = (
        instruction.strip()
        if instruction
        else "Fix the extraction selector issues."
    )

    if len(instruction) > 1000:

        instruction = (
            instruction[:1000]
        )

    headers = bright_data_headers()

    # Current Bright Data AI Flow endpoint:
    #
    # POST
    # /dca/collectors/{collector_id}/refactor_template
    #
    heal_url = (
        f"{BRIGHT_DATA_SELF_HEAL_URL}/"
        f"{collector_id}/"
        f"refactor_template"
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
            heal_url,
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

            result = response.json()

        except Exception:

            result = {
                "raw_response":
                    response.text
            }

        return result


# =========================================================
# SELF HEALING PROGRESS
# =========================================================

async def get_healing_progress(
    collector_id: str,
) -> Dict[str, Any]:

    collector_id = clean_collector_id(
        collector_id
    )

    headers = bright_data_headers()

    progress_url = (
        f"{BRIGHT_DATA_SELF_HEAL_URL}/"
        f"{collector_id}/"
        f"refactor_template/"
        f"progress"
    )

    async with httpx.AsyncClient(
        timeout=60.0
    ) as client:

        response = await client.get(
            progress_url,
            headers=headers,
        )

        if response.status_code != 200:

            raise Exception(
                "Could not get Bright Data "
                "self-healing progress: "
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
# WAIT FOR SELF HEAL
# =========================================================

async def wait_for_healing(
    collector_id: str,
    max_checks: int = 12,
) -> Dict[str, Any]:

    last_progress = {}

    for _ in range(max_checks):

        try:

            last_progress = (
                await get_healing_progress(
                    collector_id
                )
            )

            progress_text = (
                json.dumps(
                    last_progress
                ).lower()
            )

            # Common successful states
            if any(
                word in progress_text
                for word in [
                    "completed",
                    "complete",
                    "success",
                    "succeeded",
                    "done",
                ]
            ):

                return {
                    "status": "completed",
                    "progress": last_progress,
                }

            # Common failed states
            if any(
                word in progress_text
                for word in [
                    "failed",
                    "error",
                ]
            ):

                return {
                    "status": "failed",
                    "progress": last_progress,
                }

        except Exception as e:

            last_progress = {
                "error": str(e)
            }

        await asyncio.sleep(5)

    # Don't pretend it completed if Bright Data
    # did not confirm completion.
    return {
        "status": "timeout",
        "progress": last_progress,
    }


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
        ),

        "collector": bool(
            BRIGHT_DATA_COLLECTOR_ID
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

    collector = clean_env_value(
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
        # STEP 0 - CLEAN URL
        # =================================================

        target_url = clean_url(
            request.url
        )

        history.append({
            "step": 1,
            "action": "url_validation",
            "status": "completed",
        })

        # =================================================
        # STEP 1 - BRIGHT DATA EXTRACTION
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
        # STEP 2 - GEMINI DIAGNOSIS
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
        # STEP 3 - VALIDATION
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
        # STEP 4 - ANOMALY DETECTED
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
                "Inspect the extraction for "
                "missing or incorrect selectors "
                "and repair the scraper so that "
                "the expected structured data is "
                "returned correctly."
            )

        # =================================================
        # STEP 5 - BRIGHT DATA AI SELF HEALING
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

        history.append({
            "step": 6,
            "action": "self_healing_progress",
            "status": "running",
        })

        progress = (
            await wait_for_healing(
                BRIGHT_DATA_COLLECTOR_ID
            )
        )

        if progress["status"] == "failed":

            history[-1]["status"] = (
                "failed"
            )

            return {
                "status": "failed",
                "message": (
                    "Bright Data self-healing "
                    "failed."
                ),
                "attempts": attempts,
                "url": target_url,
                "analysis": analysis,
                "heal_result": heal_result,
                "progress": progress,
                "history": history,
            }

        if progress["status"] == "timeout":

            history[-1]["status"] = (
                "timeout"
            )

            return {
                "status": "healing_in_progress",
                "message": (
                    "Bright Data self-healing "
                    "was triggered but has not "
                    "confirmed completion yet."
                ),
                "attempts": attempts,
                "url": target_url,
                "analysis": analysis,
                "heal_result": heal_result,
                "progress": progress,
                "history": history,
            }

        history[-1]["status"] = (
            "completed"
        )

        # =================================================
        # STEP 7 - RE-EXTRACTION
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
        # SUCCESS
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
                    "triggered Bright Data "
                    "self-healing, re-extracted "
                    "the data, and verified "
                    "the repaired result."
                ),
                "attempts": attempts,
                "url": target_url,
                "initial_analysis": analysis,
                "final_data": repaired_data,
                "analysis": final_analysis,
                "history": history,
            }

        # =================================================
        # STILL INVALID
        # =================================================

        history[-1]["status"] = (
            "failed"
        )

        return {
            "status": "repair_failed",
            "message": (
                "The extraction was repaired "
                "but the final verification "
                "still detected anomalies."
            ),
            "attempts": attempts,
            "url": target_url,
            "initial_analysis": analysis,
            "final_data": repaired_data,
            "analysis": final_analysis,
            "history": history,
        }

    # =====================================================
    # INVALID INPUT
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
