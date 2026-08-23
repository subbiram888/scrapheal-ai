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


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


def clean_env(value: str | None) -> str | None:
    """
    Remove accidental spaces, newlines, tabs and
    non-printable ASCII characters.
    """

    if value is None:
        return None

    value = str(value)

    value = "".join(
        char
        for char in value
        if ord(char) >= 32 and ord(char) != 127
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


# ============================================================
# BRIGHT DATA API
# ============================================================

BRIGHT_DATA_TRIGGER_URL = (
    "https://api.brightdata.com/dca/trigger"
)

BRIGHT_DATA_DATASET_URL = (
    "https://api.brightdata.com/dca/dataset"
)


# ============================================================
# GEMINI
# ============================================================

gemini = None

if GEMINI_API_KEY:
    gemini = genai.Client(
        api_key=GEMINI_API_KEY
    )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="ScrapeHeal AI",
    description=(
        "AI-powered self-healing web extraction "
        "using Bright Data and Gemini"
    ),
    version="4.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ScrapeRequest(BaseModel):
    url: str


# ============================================================
# URL CLEANING
# ============================================================

def clean_url(value: str) -> str:
    """
    Clean and validate the URL received from React.
    """

    if not value:
        raise ValueError(
            "URL is required."
        )

    value = str(value)

    # Remove non-printable ASCII characters
    value = "".join(
        char
        for char in value
        if ord(char) >= 32 and ord(char) != 127
    )

    value = value.strip()

    # Remove accidental quotes
    value = value.strip("\"'")

    if not value:
        raise ValueError(
            "URL is empty after cleaning."
        )

    if not (
        value.startswith("http://")
        or value.startswith("https://")
    ):
        raise ValueError(
            "URL must start with http:// or https://"
        )

    return value


# ============================================================
# COLLECTOR VALIDATION
# ============================================================

def validate_configuration():

    if not BRIGHT_DATA_API_TOKEN:
        raise Exception(
            "BRIGHT_DATA_API_TOKEN is missing."
        )

    if not BRIGHT_DATA_COLLECTOR_ID:
        raise Exception(
            "BRIGHT_DATA_COLLECTOR_ID is missing."
        )

    if not BRIGHT_DATA_COLLECTOR_ID.startswith("c_"):
        raise Exception(
            "Invalid BRIGHT_DATA_COLLECTOR_ID. "
            "Bright Data Scraper Studio Collector IDs "
            "should start with 'c_'. "
            "Do NOT use a collection/job ID such as 'j_...'."
        )

    if not GEMINI_API_KEY:
        raise Exception(
            "GEMINI_API_KEY is missing."
        )


# ============================================================
# BRIGHT DATA EXTRACTION
# ============================================================

async def run_bright_data_collector(
    url: str,
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    validate_configuration()

    # --------------------------------------------------------
    # Clean URL
    # --------------------------------------------------------

    target_url = clean_url(url)

    # --------------------------------------------------------
    # Clean collector ID
    # --------------------------------------------------------

    collector_id = clean_env(
        BRIGHT_DATA_COLLECTOR_ID
    )

    api_token = clean_env(
        BRIGHT_DATA_API_TOKEN
    )

    # --------------------------------------------------------
    # Headers
    # --------------------------------------------------------

    headers = {
        "Authorization": (
            f"Bearer {api_token}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Use params= instead of manually building:
    #
    # ?collector=...
    #
    # This prevents URL encoding/newline problems.
    # --------------------------------------------------------

    params = {
        "collector": collector_id,
        "queue_next": "1",
    }

    payload = [
        {
            "url": target_url
        }
    ]

    print(
        "Scrape URL:",
        repr(target_url)
    )

    print(
        "Collector ID:",
        repr(collector_id)
    )

    # --------------------------------------------------------
    # HTTP client
    # --------------------------------------------------------

    async with httpx.AsyncClient(
        timeout=90.0,
        follow_redirects=True,
    ) as client:

        # ====================================================
        # STEP 1
        # TRIGGER BRIGHT DATA COLLECTOR
        # ====================================================

        response = await client.post(
            BRIGHT_DATA_TRIGGER_URL,
            params=params,
            headers=headers,
            json=payload,
        )

        print(
            "Bright Data trigger status:",
            response.status_code
        )

        print(
            "Bright Data trigger response:",
            response.text[:1000]
        )

        # ----------------------------------------------------
        # Unauthorized
        # ----------------------------------------------------

        if response.status_code == 401:

            raise Exception(
                "Bright Data authentication failed. "
                "Check BRIGHT_DATA_API_TOKEN."
            )

        # ----------------------------------------------------
        # Collector not found
        # ----------------------------------------------------

        if response.status_code == 404:

            raise Exception(
                "Bright Data Collector not found. "
                "Check BRIGHT_DATA_COLLECTOR_ID. "
                "It must be the published Scraper Studio "
                "Collector ID beginning with c_."
            )

        # ----------------------------------------------------
        # Invalid input schema
        # ----------------------------------------------------

        if response.status_code == 422:

            raise Exception(
                "Bright Data rejected the input. "
                "Your collector input schema may not use "
                "a field named 'url'. Check the Inputs tab "
                "of your Bright Data collector."
            )

        # ----------------------------------------------------
        # Other errors
        # ----------------------------------------------------

        if response.status_code not in [
            200,
            201,
            202,
        ]:

            raise Exception(
                "Bright Data trigger failed: "
                f"{response.text}"
            )

        # ----------------------------------------------------
        # Parse response
        # ----------------------------------------------------

        try:

            trigger_data = (
                response.json()
            )

        except Exception:

            raise Exception(
                "Bright Data returned an invalid "
                "trigger response."
            )

        # ----------------------------------------------------
        # Bright Data returns:
        #
        # {
        #     "collection_id": "j_xxxxx"
        # }
        #
        # This is NOT the collector ID.
        # ----------------------------------------------------

        collection_id = (
            trigger_data.get(
                "collection_id"
            )
        )

        if not collection_id:

            raise Exception(
                "Bright Data did not return "
                f"collection_id: {trigger_data}"
            )

        collection_id = clean_env(
            collection_id
        )

        print(
            "Bright Data collection ID:",
            collection_id
        )

        # ====================================================
        # STEP 2
        # POLL DATASET
        # ====================================================

        dataset_params = {
            "id": collection_id
        }

        for attempt in range(60):

            await asyncio.sleep(5)

            result_response = await client.get(
                BRIGHT_DATA_DATASET_URL,
                params=dataset_params,
                headers=headers,
            )

            print(
                f"Dataset attempt {attempt + 1}:",
                result_response.status_code
            )

            # ------------------------------------------------
            # Dataset ready
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Still processing
            # ------------------------------------------------

            if result_response.status_code in [
                202,
                404,
            ]:

                continue

            # ------------------------------------------------
            # Other errors
            # ------------------------------------------------

            raise Exception(
                "Bright Data dataset request failed: "
                f"{result_response.text}"
            )

        # ----------------------------------------------------
        # Timeout
        # ----------------------------------------------------

        raise Exception(
            "Bright Data extraction timed out "
            "after waiting for the dataset."
        )


# ============================================================
# GEMINI ANALYSIS
# ============================================================

async def analyze_with_gemini(
    data: Any,
) -> Dict[str, Any]:

    if gemini is None:

        raise Exception(
            "GEMINI_API_KEY is missing."
        )

    # --------------------------------------------------------
    # Convert result to JSON
    # --------------------------------------------------------

    try:

        data_text = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )

    except Exception:

        data_text = str(data)

    # Prevent excessively large prompt
    data_text = data_text[:30000]

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = f"""
You are ScrapeHeal AI, an AI-powered
web extraction reliability engine.

Your job is to determine whether the extracted
web data is trustworthy.

Analyze the data for:

1. Missing fields
2. Empty values
3. Null values
4. Broken records
5. Incorrect data types
6. Inconsistent structure
7. Suspicious extraction results
8. Unexpected HTML or error pages
9. Incomplete extraction

IMPORTANT:

Do not invent problems.

If the data appears valid, mark it valid.

Return ONLY JSON.

Required format:

{{
    "is_valid": true,
    "confidence": 95,
    "risk_level": "low",
    "issues": [],
    "explanation": "The extracted data appears structurally consistent.",
    "repair_instruction": "",
    "recommended_action": "accept"
}}

If there is an anomaly:

{{
    "is_valid": false,
    "confidence": 90,
    "risk_level": "medium",
    "issues": [
        "Example issue"
    ],
    "explanation": "Explain the problem.",
    "repair_instruction": "Explain what should be repaired.",
    "recommended_action": "repair"
}}

Extracted data:

{data_text}
"""

    # --------------------------------------------------------
    # Gemini request
    # --------------------------------------------------------

    response = await asyncio.to_thread(
        gemini.models.generate_content,

        model="gemini-2.5-flash",

        contents=prompt,
    )

    text = (
        response.text or ""
    ).strip()

    # --------------------------------------------------------
    # Remove markdown fences
    # --------------------------------------------------------

    if text.startswith("```"):

        text = (
            text
            .replace(
                "```json",
                "",
            )
            .replace(
                "```",
                "",
            )
            .strip()
        )

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        analysis = json.loads(
            text
        )

    except Exception:

        raise Exception(
            "Gemini returned invalid JSON: "
            f"{text[:1000]}"
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

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


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
async def home():

    return {
        "name":
            "ScrapeHeal AI",

        "status":
            "online",

        "version":
            "4.0.0",

        "architecture":
            "Bright Data + Gemini AI + FastAPI",
    }


@app.get("/health")
async def health():

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


# ============================================================
# CONFIGURATION CHECK
# ============================================================

@app.get("/config")
async def config():

    """
    Safe diagnostic endpoint.

    NEVER returns API keys.
    """

    collector = (
        BRIGHT_DATA_COLLECTOR_ID
        or ""
    )

    return {

        "bright_data_token_present":
            bool(
                BRIGHT_DATA_API_TOKEN
            ),

        "collector_present":
            bool(
                collector
            ),

        "collector_format_valid":
            collector.startswith("c_"),

        "collector_preview":
            (
                collector[:6] + "..."
                if collector
                else None
            ),

        "gemini_key_present":
            bool(
                GEMINI_API_KEY
            ),
    }


# ============================================================
# SELF HEAL PIPELINE
# ============================================================

@app.post("/self-heal")
async def self_heal(
    request: ScrapeRequest,
):

    history = []

    attempts = 0

    try:

        # ====================================================
        # CLEAN URL
        # ====================================================

        target_url = clean_url(
            request.url
        )

        # ====================================================
        # STEP 1
        # INITIAL EXTRACTION
        # ====================================================

        attempts += 1

        history.append({

            "step":
                1,

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

        # ====================================================
        # STEP 2
        # AI DIAGNOSIS
        # ====================================================

        history.append({

            "step":
                2,

            "action":
                "gemini_ai_diagnosis",

            "status":
                "running",
        })

        analysis = (
            await analyze_with_gemini(
                current_data
            )
        )

        history[-1]["status"] = (
            "completed"
        )

        # ====================================================
        # VALID
        # ====================================================

        if analysis["is_valid"]:

            history.append({

                "step":
                    3,

                "action":
                    "verification",

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

        # ====================================================
        # ANOMALY
        # ====================================================

        history.append({

            "step":
                3,

            "action":
                "anomaly_detection",

            "status":
                "detected",

            "issues":
                analysis["issues"],
        })

        # ====================================================
        # REPAIR STRATEGY
        # ====================================================

        repair_instruction = (
            analysis.get(
                "repair_instruction"
            )
            or
            "Re-run the extraction and verify the result."
        )

        history.append({

            "step":
                4,

            "action":
                "repair_strategy",

            "status":
                "generated",

            "instruction":
                repair_instruction,
        })

        # ====================================================
        # STEP 5
        # RECOVERY / RE-EXTRACTION
        #
        # IMPORTANT:
        # We re-run the published Bright Data collector.
        #
        # We do NOT call a fake /heal endpoint.
        # Bright Data's documented collection API is used.
        # ====================================================

        attempts += 1

        history.append({

            "step":
                5,

            "action":
                "bright_data_re_extraction",

            "status":
                "running",
        })

        repaired_result = (
            await run_bright_data_collector(
                target_url
            )
        )

        repaired_data = (
            repaired_result["data"]
        )

        history[-1]["status"] = (
            "completed"
        )

        # ====================================================
        # STEP 6
        # FINAL VERIFICATION
        # ====================================================

        history.append({

            "step":
                6,

            "action":
                "final_ai_verification",

            "status":
                "running",
        })

        final_analysis = (
            await analyze_with_gemini(
                repaired_data
            )
        )

        # ====================================================
        # SUCCESS AFTER RECOVERY
        # ====================================================

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

                "repair_instruction":
                    repair_instruction,

                "history":
                    history,
            }

        # ====================================================
        # STILL INVALID
        # ====================================================

        history[-1]["status"] = (
            "review_required"
        )

        return {

            "status":
                "needs_review",

            "attempts":
                attempts,

            "url":
                target_url,

            "final_data":
                repaired_data,

            "analysis":
                final_analysis,

            "repair_instruction":
                repair_instruction,

            "history":
                history,
        }

    # ========================================================
    # INVALID REQUEST
    # ========================================================

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

    # ========================================================
    # BRIGHT DATA / GENERAL ERROR
    # ========================================================

    except Exception as e:

        print(
            "ScrapeHeal error:",
            repr(e)
        )

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