import os
import json
import asyncio
from typing import Any, Dict
from urllib.parse import urlparse

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


# =========================================================
# ENVIRONMENT VARIABLE CLEANER
# =========================================================

def clean_env(value):
    """
    Removes accidental newlines, tabs and other
    whitespace/control characters from environment
    variables.
    """

    if value is None:
        return None

    cleaned = str(value)

    # Remove ASCII control characters
    cleaned = "".join(
        char
        for char in cleaned
        if ord(char) >= 32 and ord(char) != 127
    )

    return cleaned.strip()


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
# BRIGHT DATA ENDPOINTS
# =========================================================

TRIGGER_URL = (
    "https://api.brightdata.com/dca/trigger"
)

RESULT_URL = (
    "https://api.brightdata.com/dca/dataset"
)

HEAL_URL = (
    "https://api.brightdata.com/dca/collector"
)


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

    allow_origins=["*"],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# REQUEST MODEL
# =========================================================

class ScrapeRequest(BaseModel):
    url: str


# =========================================================
# URL CLEANER
# =========================================================

def clean_url(value: str) -> str:
    """
    Cleans a URL before sending it to Bright Data.

    This specifically prevents errors such as:

    Invalid non-printable ASCII character in URL,
    '\\n'
    """

    if value is None:
        raise ValueError(
            "URL is required."
        )

    value = str(value)

    # Remove ASCII control characters
    cleaned = "".join(
        char
        for char in value
        if ord(char) >= 32 and ord(char) != 127
    )

    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    # Remove accidental surrounding quotes
    cleaned = cleaned.strip(
        "\"'"
    )

    # Remove whitespace/control characters again
    cleaned = "".join(
        char
        for char in cleaned
        if not char.isspace()
    )

    if not cleaned:
        raise ValueError(
            "URL cannot be empty."
        )

    # Validate URL
    parsed = urlparse(cleaned)

    if parsed.scheme not in [
        "http",
        "https",
    ]:
        raise ValueError(
            "URL must start with http:// or https://"
        )

    if not parsed.netloc:
        raise ValueError(
            "Invalid website URL."
        )

    return cleaned


# =========================================================
# BRIGHT DATA SCRAPER
# =========================================================

async def run_bright_data_collector(
    url: str,
) -> Dict[str, Any]:

    # -----------------------------------------------------
    # Clean URL one more time
    # -----------------------------------------------------

    url = clean_url(url)

    # -----------------------------------------------------
    # Check credentials
    # -----------------------------------------------------

    if not BRIGHT_DATA_API_TOKEN:
        raise Exception(
            "BRIGHT_DATA_API_TOKEN is missing."
        )

    if not BRIGHT_DATA_COLLECTOR_ID:
        raise Exception(
            "BRIGHT_DATA_COLLECTOR_ID is missing."
        )

    # -----------------------------------------------------
    # Clean environment values again
    # -----------------------------------------------------

    api_token = clean_env(
        BRIGHT_DATA_API_TOKEN
    )

    collector_id = clean_env(
        BRIGHT_DATA_COLLECTOR_ID
    )

    # -----------------------------------------------------
    # Headers
    # -----------------------------------------------------

    headers = {
        "Authorization":
            f"Bearer {api_token}",

        "Content-Type":
            "application/json",
    }

    # -----------------------------------------------------
    # HTTP CLIENT
    # -----------------------------------------------------

    async with httpx.AsyncClient(
        timeout=90.0,
        follow_redirects=True,
    ) as client:

        # =================================================
        # TRIGGER BRIGHT DATA
        # =================================================

        trigger_params = {
            "collector": collector_id,
            "queue_next": "1",
        }

        trigger_payload = [
            {
                "url": url
            }
        ]

        print(
            "Bright Data target URL:",
            repr(url)
        )

        print(
            "Bright Data collector:",
            repr(collector_id)
        )

        response = await client.post(
            TRIGGER_URL,

            params=trigger_params,

            headers=headers,

            json=trigger_payload,
        )

        if response.status_code not in [
            200,
            201,
            202,
        ]:

            raise Exception(
                "Bright Data trigger failed: "
                f"{response.text}"
            )

        # -------------------------------------------------
        # Parse trigger response
        # -------------------------------------------------

        try:

            trigger_data = (
                response.json()
            )

        except Exception:

            raise Exception(
                "Bright Data returned "
                "an invalid response: "
                f"{response.text}"
            )

        # -------------------------------------------------
        # Find collection ID
        # -------------------------------------------------

        collection_id = (
            trigger_data.get(
                "collection_id"
            )

            or trigger_data.get(
                "id"
            )

            or trigger_data.get(
                "snapshot_id"
            )
        )

        if not collection_id:

            raise Exception(
                "Bright Data did not return "
                f"a collection ID: {trigger_data}"
            )

        collection_id = clean_env(
            collection_id
        )

        # =================================================
        # POLL RESULT
        # =================================================

        for attempt in range(45):

            result_params = {
                "id": collection_id
            }

            result_response = (
                await client.get(
                    RESULT_URL,

                    params=result_params,

                    headers=headers,
                )
            )

            # -------------------------------------------------
            # RESULT READY
            # -------------------------------------------------

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
                    "collection_id":
                        collection_id,

                    "data":
                        data,
                }

            # -------------------------------------------------
            # STILL PROCESSING
            # -------------------------------------------------

            if result_response.status_code in [
                202,
                404,
            ]:

                await asyncio.sleep(2)

                continue

            # -------------------------------------------------
            # OTHER ERROR
            # -------------------------------------------------

            raise Exception(
                "Bright Data result failed: "
                f"{result_response.text}"
            )

        # -------------------------------------------------
        # TIMEOUT
        # -------------------------------------------------

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

    # -----------------------------------------------------
    # Convert data to JSON
    # -----------------------------------------------------

    data_text = json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    )

    # -----------------------------------------------------
    # Gemini prompt
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Gemini call
    # -----------------------------------------------------

    response = await asyncio.to_thread(
        gemini.models.generate_content,

        model="gemini-3.6-flash",

        contents=prompt,
    )

    text = (
        response.text
        or ""
    ).strip()

    # -----------------------------------------------------
    # Remove markdown code fences
    # -----------------------------------------------------

    if text.startswith("```"):

        text = (
            text.replace(
                "```json",
                "",
            )
            .replace(
                "```",
                "",
            )
            .strip()
        )

    # -----------------------------------------------------
    # Parse JSON
    # -----------------------------------------------------

    try:

        analysis = json.loads(
            text
        )

    except Exception:

        raise Exception(
            "Gemini returned invalid JSON: "
            f"{text}"
        )

    # -----------------------------------------------------
    # Normalize result
    # -----------------------------------------------------

    return {

        "is_valid":
            bool(
                analysis.get(
                    "is_valid",
                    False,
                )
            ),

        "confidence":
            int(
                analysis.get(
                    "confidence",
                    0,
                )
            ),

        "risk_level":
            analysis.get(
                "risk_level",
                "unknown",
            ),

        "issues":
            analysis.get(
                "issues",
                [],
            ),

        "explanation":
            analysis.get(
                "explanation",
                "",
            ),

        "repair_instruction":
            analysis.get(
                "repair_instruction",
                "",
            ),

        "recommended_action":
            analysis.get(
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

    # -----------------------------------------------------
    # Clean values
    # -----------------------------------------------------

    collector_id = clean_env(
        collector_id
    )

    instruction = str(
        instruction or ""
    ).strip()

    if not collector_id:
        return False

    # -----------------------------------------------------
    # Build endpoint
    # -----------------------------------------------------

    endpoint = (
        f"{HEAL_URL}/"
        f"{collector_id}/heal"
    )

    # -----------------------------------------------------
    # Headers
    # -----------------------------------------------------

    headers = {
        "Authorization":
            f"Bearer "
            f"{clean_env(BRIGHT_DATA_API_TOKEN)}",

        "Content-Type":
            "application/json",
    }

    # -----------------------------------------------------
    # Payload
    # -----------------------------------------------------

    payload = {

        "instructions":
            instruction,

        "auto_deploy":
            True,
    }

    print(
        "Bright Data heal endpoint:",
        repr(endpoint)
    )

    # -----------------------------------------------------
    # Request
    # -----------------------------------------------------

    async with httpx.AsyncClient(
        timeout=90.0,
        follow_redirects=True,
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

        "name":
            "ScrapeHeal AI",

        "status":
            "online",

        "version":
            "4.0.0",
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {

        "status":
            "healthy",

        "bright_data":
            bool(
                BRIGHT_DATA_API_TOKEN
                and
                BRIGHT_DATA_COLLECTOR_ID
            ),

        "gemini":
            bool(
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
        # CLEAN TARGET URL
        # =================================================

        target_url = clean_url(
            request.url
        )

        print(
            "Received URL:",
            repr(request.url)
        )

        print(
            "Cleaned URL:",
            repr(target_url)
        )

        # =================================================
        # ATTEMPT 1 - INITIAL EXTRACTION
        # =================================================

        attempts += 1

        history.append({

            "step":
                len(history) + 1,

            "action":
                "bright_data_extraction",

            "status":
                "running",
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
        # GEMINI DIAGNOSIS
        # =================================================

        history.append({

            "step":
                len(history) + 1,

            "action":
                "gemini_diagnosis",

            "status":
                "completed",
        })

        analysis = (
            await analyze_with_gemini(
                current_data
            )
        )

        # =================================================
        # VALID DATA
        # =================================================

        if analysis["is_valid"]:

            history.append({

                "step":
                    len(history) + 1,

                "action":
                    "verification_completed",

                "status":
                    "verified",
            })

            return {

                "status":
                    "success",

                "attempts":
                    attempts,

                "url":
                    target_url,

                "final_data":
                    current_data,

                "analysis":
                    analysis,

                "history":
                    history,
            }

        # =================================================
        # ANOMALY FOUND
        # =================================================

        history.append({

            "step":
                len(history) + 1,

            "action":
                "anomaly_detected",

            "status":
                "detected",

            "issues":
                analysis["issues"],
        })

        repair_instruction = (
            analysis.get(
                "repair_instruction"
            )

            or
            "Repair the detected extraction issues."
        )

        # =================================================
        # REPAIR
        # =================================================

        history.append({

            "step":
                len(history) + 1,

            "action":
                "repair_requested",

            "status":
                "running",
        })

        healed = (
            await heal_bright_data_collector(

                BRIGHT_DATA_COLLECTOR_ID,

                repair_instruction,
            )
        )

        if not healed:

            history[-1]["status"] = (
                "failed"
            )

            return {

                "status":
                    "failed",

                "attempts":
                    attempts,

                "url":
                    target_url,

                "final_data":
                    current_data,

                "analysis":
                    analysis,

                "history":
                    history,
            }

        history[-1]["status"] = (
            "completed"
        )

        # =================================================
        # ATTEMPT 2 - AFTER REPAIR
        # =================================================

        attempts += 1

        history.append({

            "step":
                len(history) + 1,

            "action":
                "bright_data_re_extraction",

            "status":
                "running",
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
        # VERIFY REPAIRED DATA
        # =================================================

        history.append({

            "step":
                len(history) + 1,

            "action":
                "post_repair_verification",

            "status":
                "running",
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

                "status":
                    "self_healed",

                "attempts":
                    attempts,

                "url":
                    target_url,

                "final_data":
                    repaired_data,

                "analysis":
                    final_analysis,

                "history":
                    history,
            }

        # =================================================
        # REPAIR FAILED
        # =================================================

        history[-1]["status"] = (
            "failed"
        )

        return {

            "status":
                "failed",

            "attempts":
                attempts,

            "url":
                target_url,

            "final_data":
                repaired_data,

            "analysis":
                final_analysis,

            "history":
                history,
        }

    except ValueError as e:

        raise HTTPException(

            status_code=400,

            detail={
                "error":
                    str(e),

                "type":
                    "invalid_request",
            },
        )

    except Exception as e:

        print(
            "ScrapeHeal pipeline error:",
            repr(e)
        )

        history.append({

            "step":
                len(history) + 1,

            "action":
                "pipeline_error",

            "status":
                "failed",
        })

        raise HTTPException(

            status_code=500,

            detail={

                "error":
                    str(e),

                "attempts":
                    attempts,

                "history":
                    history,
            },
        )