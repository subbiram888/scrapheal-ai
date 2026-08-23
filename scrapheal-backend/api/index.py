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
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    return value.strip()


BRIGHT_DATA_API_TOKEN = clean_env_value(os.getenv("BRIGHT_DATA_API_TOKEN"))
BRIGHT_DATA_COLLECTOR_ID = clean_env_value(os.getenv("BRIGHT_DATA_COLLECTOR_ID"))
GEMINI_API_KEY = clean_env_value(os.getenv("GEMINI_API_KEY"))


# =========================================================
# BRIGHT DATA ENDPOINTS
# =========================================================

BRIGHT_DATA_TRIGGER_URL = "https://api.brightdata.com/dca/trigger"
BRIGHT_DATA_DATASET_URL = "https://api.brightdata.com/dca/dataset"
BRIGHT_DATA_SELF_HEAL_URL = "https://api.brightdata.com/dca/collectors"

# Web Scraper / Datasets v3 API Fallback Endpoints
BRIGHT_DATA_V3_TRIGGER_URL = "https://api.brightdata.com/datasets/v3/trigger"
BRIGHT_DATA_V3_SNAPSHOT_URL = "https://api.brightdata.com/datasets/v3/snapshot"


# =========================================================
# GEMINI CLIENT
# =========================================================

gemini = None

if GEMINI_API_KEY:
    gemini = genai.Client(api_key=GEMINI_API_KEY)


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
# HELPER FUNCTIONS
# =========================================================

def clean_url(value: str) -> str:
    if value is None:
        raise ValueError("URL is required")

    value = str(value).strip()
    value = re.sub(r"[\x00-\x1f\x7f]", "", value).strip()

    if not value:
        raise ValueError("URL is required")

    parsed = urlparse(value)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")

    if not parsed.netloc:
        raise ValueError("Invalid URL")

    return value


def clean_collector_id(value: str) -> str:
    value = clean_env_value(value)
    if not value:
        raise ValueError("BRIGHT_DATA_COLLECTOR_ID is missing from environment variables.")
    return value


class ScrapeRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return clean_url(value)


def bright_data_headers() -> Dict[str, str]:
    token = clean_env_value(BRIGHT_DATA_API_TOKEN)
    if not token:
        raise ValueError("BRIGHT_DATA_API_TOKEN is missing from environment variables.")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# =========================================================
# BRIGHT DATA EXTRACTION
# =========================================================

async def run_bright_data_collector(target_url: str) -> Dict[str, Any]:
    target_url = clean_url(target_url)
    collector_id = clean_collector_id(BRIGHT_DATA_COLLECTOR_ID)
    headers = bright_data_headers()
    payload = [{"url": target_url}]

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check if collector_id is a v3 Dataset ID (e.g., gd_...) or Scraper Studio ID (e.g., c_...)
        if collector_id.startswith("gd_"):
            # Use Datasets V3 API
            trigger_url = f"{BRIGHT_DATA_V3_TRIGGER_URL}?dataset_id={collector_id}&format=json"
            response = await client.post(trigger_url, headers=headers, json=payload)
            
            if response.status_code not in (200, 201, 202):
                raise Exception(f"Bright Data v3 trigger failed: {response.text}")

            trigger_data = response.json()
            snapshot_id = trigger_data.get("snapshot_id") or trigger_data.get("id")

            if not snapshot_id:
                raise Exception(f"Bright Data did not return snapshot_id: {trigger_data}")

            # Poll Snapshot
            poll_url = f"{BRIGHT_DATA_V3_SNAPSHOT_URL}/{snapshot_id}?format=json"
            for _ in range(25):
                res = await client.get(poll_url, headers=headers)
                if res.status_code == 200:
                    try:
                        data = res.json()
                    except Exception:
                        data = res.text
                    
                    if isinstance(data, list):
                        return {"collection_id": snapshot_id, "data": data}

                await asyncio.sleep(2)

            raise Exception("Bright Data extraction timed out waiting for dataset.")

        else:
            # Use Scraper Studio DCA API
            query = urlencode({"collector": collector_id, "queue_next": "1"})
            trigger_url = f"{BRIGHT_DATA_TRIGGER_URL}?{query}"

            response = await client.post(trigger_url, headers=headers, json=payload)
            if response.status_code not in (200, 201, 202):
                raise Exception(f"Bright Data trigger failed: {response.text}")

            trigger_data = response.json()
            collection_id = trigger_data.get("collection_id")

            if not collection_id:
                raise Exception(f"Bright Data did not return collection_id: {trigger_data}")

            dataset_url = f"{BRIGHT_DATA_DATASET_URL}?id={collection_id}"
            for _ in range(25):
                dataset_response = await client.get(dataset_url, headers=headers)
                if dataset_response.status_code == 200:
                    try:
                        data = dataset_response.json()
                    except Exception:
                        data = dataset_response.text

                    if isinstance(data, list):
                        return {"collection_id": collection_id, "data": data}

                await asyncio.sleep(2)

            raise Exception("Bright Data extraction timed out while waiting for dataset.")


# =========================================================
# GEMINI ANALYSIS
# =========================================================

async def analyze_with_gemini(data: Any) -> Dict[str, Any]:
    if gemini is None:
        raise Exception("GEMINI_API_KEY is missing.")

    try:
        data_text = json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        data_text = str(data)

    prompt = f"""
You are ScrapeHeal AI, an AI-powered web extraction reliability engine.
Your job is to inspect extracted web data and determine whether the extraction is trustworthy.

Check for:
1. Missing important fields
2. Empty/null values
3. Broken records or improper structure

Return ONLY valid JSON matching this structure:
{{
    "is_valid": true,
    "confidence": 95,
    "risk_level": "low",
    "issues": [],
    "explanation": "The extracted data is valid.",
    "repair_instruction": "",
    "recommended_action": "accept"
}}

EXTRACTED DATA:
{data_text[:30000]}
"""

    response = await asyncio.to_thread(
        gemini.models.generate_content,
        model="gemini-2.0-flash",
        contents=prompt,
    )

    text = (response.text if response.text else "").strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text).strip()

    try:
        analysis = json.loads(text)
    except Exception:
        raise Exception(f"Gemini returned invalid JSON: {text}")

    return {
        "is_valid": bool(analysis.get("is_valid", False)),
        "confidence": int(analysis.get("confidence", 0)),
        "risk_level": analysis.get("risk_level", "unknown"),
        "issues": analysis.get("issues", []),
        "explanation": analysis.get("explanation", ""),
        "repair_instruction": analysis.get("repair_instruction", ""),
        "recommended_action": analysis.get("recommended_action", "review"),
    }


# =========================================================
# BRIGHT DATA SELF HEALING
# =========================================================

async def heal_bright_data_collector(collector_id: str, instruction: str) -> Dict[str, Any]:
    collector_id = clean_collector_id(collector_id)
    instruction = instruction.strip() if instruction else "Fix extraction selectors."
    instruction = instruction[:1000]

    headers = bright_data_headers()
    heal_url = f"{BRIGHT_DATA_SELF_HEAL_URL}/{collector_id}/refactor_template"
    payload = {"prompt": instruction, "custom_input": [{}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(heal_url, headers=headers, json=payload)
        if response.status_code not in (200, 201, 202):
            raise Exception(f"Bright Data self-healing request failed: {response.text}")

        try:
            return response.json()
        except Exception:
            return {"raw_response": response.text}


async def get_healing_progress(collector_id: str) -> Dict[str, Any]:
    collector_id = clean_collector_id(collector_id)
    headers = bright_data_headers()
    progress_url = f"{BRIGHT_DATA_SELF_HEAL_URL}/{collector_id}/refactor_template/progress"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(progress_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Could not get self-healing progress: {response.text}")
        try:
            return response.json()
        except Exception:
            return {"raw_response": response.text}


async def wait_for_healing(collector_id: str, max_checks: int = 6) -> Dict[str, Any]:
    last_progress = {}
    for _ in range(max_checks):
        try:
            last_progress = await get_healing_progress(collector_id)
            progress_text = json.dumps(last_progress).lower()

            if any(w in progress_text for w in ["completed", "complete", "success", "succeeded", "done"]):
                return {"status": "completed", "progress": last_progress}

            if any(w in progress_text for w in ["failed", "error"]):
                return {"status": "failed", "progress": last_progress}

        except Exception as e:
            last_progress = {"error": str(e)}

        await asyncio.sleep(3)

    return {"status": "timeout", "progress": last_progress}


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def home():
    return {"name": "ScrapeHeal AI", "status": "online", "version": "4.0.0"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "bright_data": bool(BRIGHT_DATA_API_TOKEN),
        "collector": bool(BRIGHT_DATA_COLLECTOR_ID),
        "gemini": bool(GEMINI_API_KEY),
    }


@app.get("/config")
def config():
    collector = clean_env_value(BRIGHT_DATA_COLLECTOR_ID)
    return {
        "bright_data_token_present": bool(BRIGHT_DATA_API_TOKEN),
        "collector_present": bool(collector),
        "collector_preview": collector[:8] + "..." if collector else "",
        "gemini_key_present": bool(GEMINI_API_KEY),
    }


@app.post("/self-heal")
async def self_heal(request: ScrapeRequest):
    history = []
    attempts = 0

    try:
        target_url = clean_url(request.url)
        history.append({"step": 1, "action": "url_validation", "status": "completed"})

        attempts += 1
        history.append({"step": 2, "action": "bright_data_extraction", "status": "running"})

        first_result = await run_bright_data_collector(target_url)
        current_data = first_result["data"]
        history[-1]["status"] = "completed"

        history.append({"step": 3, "action": "gemini_diagnosis", "status": "running"})
        analysis = await analyze_with_gemini(current_data)
        history[-1]["status"] = "completed"

        if analysis["is_valid"]:
            history.append({"step": 4, "action": "verification", "status": "verified"})
            return {
                "status": "success",
                "message": "Extraction completed and verified successfully.",
                "attempts": attempts,
                "url": target_url,
                "final_data": current_data,
                "analysis": analysis,
                "history": history,
            }

        history.append({
            "step": 4,
            "action": "anomaly_detection",
            "status": "detected",
            "issues": analysis["issues"],
        })

        repair_instruction = analysis.get("repair_instruction") or "Fix missing or incorrect extraction selectors."

        history.append({"step": 5, "action": "bright_data_self_healing", "status": "running"})
        heal_result = await heal_bright_data_collector(BRIGHT_DATA_COLLECTOR_ID, repair_instruction)
        history[-1]["status"] = "triggered"

        history.append({"step": 6, "action": "self_healing_progress", "status": "running"})
        progress = await wait_for_healing(BRIGHT_DATA_COLLECTOR_ID)

        if progress["status"] in ("failed", "timeout"):
            history[-1]["status"] = progress["status"]
            return {
                "status": progress["status"],
                "message": "Self-healing triggered but did not verify completion.",
                "attempts": attempts,
                "url": target_url,
                "analysis": analysis,
                "heal_result": heal_result,
                "progress": progress,
                "history": history,
            }

        history[-1]["status"] = "completed"

        attempts += 1
        history.append({"step": 7, "action": "bright_data_re_extraction", "status": "running"})
        second_result = await run_bright_data_collector(target_url)
        repaired_data = second_result["data"]
        history[-1]["status"] = "completed"

        history.append({"step": 8, "action": "gemini_verification", "status": "running"})
        final_analysis = await analyze_with_gemini(repaired_data)

        if final_analysis["is_valid"]:
            history[-1]["status"] = "verified"
            return {
                "status": "self_healed",
                "message": "ScrapeHeal successfully repaired and verified the data.",
                "attempts": attempts,
                "url": target_url,
                "initial_analysis": analysis,
                "final_data": repaired_data,
                "analysis": final_analysis,
                "history": history,
            }

        history[-1]["status"] = "failed"
        return {
            "status": "repair_failed",
            "message": "Extraction was repaired but anomalies persist.",
            "attempts": attempts,
            "url": target_url,
            "initial_analysis": analysis,
            "final_data": repaired_data,
            "analysis": final_analysis,
            "history": history,
        }

    except ValueError as e:
        history.append({"step": len(history) + 1, "action": "validation_error", "status": "failed"})
        raise HTTPException(status_code=400, detail={"error": str(e), "attempts": attempts, "history": history})

    except Exception as e:
        history.append({"step": len(history) + 1, "action": "pipeline_error", "status": "failed"})
        raise HTTPException(status_code=500, detail={"error": str(e), "attempts": attempts, "history": history})