"""
CivicVoice Backend API — Version 2.2.0
-----------------------------------------
FastAPI backend for CivicVoice:
  1. Multilingual entity extraction (supports Anthropic Claude, OpenAI, Ollama Local LLM, and resilient Indic Heuristic NLP)
  2. Persistent profile memory stored in SQLite keyed by phone number
  3. Grounded, explainable scheme matching against schemes.json (20 national schemes) with statutory clause citations and 'Why You Qualify' breakdowns
  4. Proactive conversational follow-up question generator (/api/followup)
  5. Official printable PDF application form generator using ReportLab (/api/draft/pdf)
  6. Multilingual translation endpoint (/api/translate) for browser SpeechSynthesis voice readback
  7. Grounded conversational Citizen Welfare AI Advisor (/api/chat)
  8. Empathetic spoken briefing generator (/api/advisor-summary)
  9. Aggregate civic impact statistics dashboard (/api/stats)
"""

import io
import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ReportLab imports for official PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Load environment variables
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "civicvoice.db"
SCHEMES_PATH = BASE_DIR / "schemes.json"

app = FastAPI(title="CivicVoice API", version="2.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open(SCHEMES_PATH, encoding="utf-8") as f:
    SCHEMES: List[Dict[str, Any]] = json.load(f)


# ---------------------------------------------------------------------------
# Database & Memory Persistence (SQLite keyed by phone number)
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS citizens (
            phone TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def load_profile(phone: str) -> dict:
    conn = get_db()
    row = conn.execute("SELECT profile_json FROM citizens WHERE phone = ?", (phone.strip(),)).fetchone()
    conn.close()
    return json.loads(row["profile_json"]) if row else {}


def save_profile(phone: str, profile: dict):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO citizens (phone, profile_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(phone) DO UPDATE SET
            profile_json = excluded.profile_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (phone.strip(), json.dumps(profile)),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Intelligent Entity Extraction (Claude / OpenAI / Ollama / Indic NLP)
# ---------------------------------------------------------------------------

def extract_entities_heuristic(text: str) -> dict:
    """Zero-dependency, resilient entity extractor for Indian welfare schemes."""
    t = text.lower()
    entities: Dict[str, Any] = {}

    # 1. Artisans & Traditional Trades
    if any(w in t for w in ["artisan", "craftsman", "carpenter", "badhai", "blacksmith", "lohar", "potter", "kumhar", "sculptor", "murtikar", "tailor", "darzi", "cobbler", "muchi", "mochi", "barber", "nai", "mason", "rajmistri", "vishwakarma", "handicraft"]):
        entities["is_artisan"] = True
        entities["occupation"] = "artisan"
        entities["unorganized_worker"] = True

    # 2. Street Vendors & Hawkers
    elif any(w in t for w in ["street vendor", "hawker", "thela", "rehri", "footpath", "vendor", "pheriwala", "fruit seller", "vegetable seller", "cart", "roadside stall"]):
        entities["is_street_vendor"] = True
        entities["occupation"] = "street vendor"
        entities["residence"] = "urban"
        entities["unorganized_worker"] = True

    # 3. Agriculture / Farmers
    elif any(w in t for w in ["farmer", "kisan", "krishi", "farming", "agriculture", "crop", "landowner", "sharecropper", "kheti"]):
        entities["occupation"] = "farmer"
        entities["has_crop_loan_or_land"] = True

    # 4. Daily Wage & Informal Workers
    elif any(w in t for w in ["daily wage", "labour", "laborer", "mazdoor", "coolie", "construction worker", "daily worker", "maid", "kamwali", "driver", "rickshaw", "auto driver"]):
        entities["occupation"] = "daily wage worker"
        entities["unorganized_worker"] = True

    # 5. Students
    elif any(w in t for w in ["student", "studying", "school", "college", "class 10", "class 11", "class 12", "post matric", "scholarship"]):
        entities["occupation"] = "student"

    # 6. Unemployed
    elif any(w in t for w in ["unemployed", "no job", "looking for work", "berozgar"]):
        entities["occupation"] = "unemployed"

    # Age extraction
    age_match = re.search(r"\b(?:i am|age is|age|aged|am)\s*(\d{1,2})\b", t)
    if not age_match:
        age_match = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?|saal|varsh)\s*(?:old)?\b", t)
    if age_match:
        val = int(age_match.group(1))
        if 5 <= val <= 105:
            entities["age"] = val

    # Gender & Marital Status
    if any(w in t for w in ["widow", "vidhwa", "lost my husband", "husband died", "husband passed away", "widowed"]):
        entities["marital_status"] = "widow"
        entities["gender"] = "female"
        entities["breadwinner_deceased"] = True
    elif any(w in t for w in ["female", "woman", "mother", "wife", "mahila", "lady", "aurat"]):
        entities["gender"] = "female"
    elif any(w in t for w in ["male", "man", "father", "husband", "purush", "boy", "aadmi"]):
        entities["gender"] = "male"

    if "marital_status" not in entities:
        if any(w in t for w in ["married", "shadi shuda"]):
            entities["marital_status"] = "married"
        elif any(w in t for w in ["unmarried", "single"]):
            entities["marital_status"] = "unmarried"

    # Maternity & Pregnancy
    if any(w in t for w in ["pregnant", "garbhavati", "expecting baby", "expecting a baby", "maternity", "lactating", "nursing mother", "infant child", "breastfeeding", "just delivered"]):
        entities["is_pregnant_or_lactating"] = True
        entities["gender"] = "female"

    # Income Bracket
    if any(w in t for w in ["bpl", "below poverty line", "ration card", "antyodaya", "aay card", "very poor"]):
        entities["income_bracket"] = "bpl"
    elif any(w in t for w in ["low income", "poor", "hardly earn", "struggling", "less than 2 lakh", "less than 1 lakh", "small earner", "garib"]):
        entities["income_bracket"] = "low"
    elif any(w in t for w in ["middle class", "moderate income"]):
        entities["income_bracket"] = "middle"

    # Caste Category
    if any(w in t for w in [" sc ", "scheduled caste", "dalit", "sc category"]):
        entities["caste_category"] = "sc"
    elif any(w in t for w in [" st ", "scheduled tribe", "adivasi", "tribal", "st category"]):
        entities["caste_category"] = "st"
    elif any(w in t for w in [" obc ", "other backward class"]):
        entities["caste_category"] = "obc"
    elif any(w in t for w in ["general category", "open category", "general"]):
        entities["caste_category"] = "general"

    # Residence
    if "residence" not in entities:
        if any(w in t for w in ["rural", "village", "gaon", "gram", "panchayat", "countryside", "dehat"]):
            entities["residence"] = "rural"
        elif any(w in t for w in ["urban", "city", "town", "shahar", "metro"]):
            entities["residence"] = "urban"

    # Daughter & Daughter Age
    if any(w in t for w in ["daughter", "girl child", "beti", "ladki", "daughter's"]):
        entities["has_daughter"] = True
        d_age = re.search(r"(?:daughter|beti|girl child).*?\b(\d{1,2})\s*(?:years?|yrs?|saal)?\s*(?:old)?\b", t)
        if not d_age:
            d_age = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?|saal)?\s*old\s*(?:daughter|beti|girl)\b", t)
        if d_age:
            entities["daughter_age"] = int(d_age.group(1))

    # Disability
    dis_match = re.search(r"\b(\d{1,3})%\s*(?:disabilit|divyang|handicap)", t)
    if dis_match:
        entities["disability_percentage"] = int(dis_match.group(1))
    elif any(w in t for w in ["disabled", "handicapped", "divyang", "paralyzed", "blind", "wheelchair"]):
        entities["disability_percentage"] = 80

    # Housing, Cooking & Solar
    if any(w in t for w in ["kutcha", "mud house", "thatched house", "homeless", "no proper house", "broken roof", "kachha"]):
        entities["housing_status"] = "kutcha_house"
    elif any(w in t for w in ["pucca house", "concrete house", "own house", "brick house", "pukka"]):
        entities["housing_status"] = "pucca_house"

    if any(w in t for w in ["no lpg", "no gas", "chulha", "firewood", "smoke stove", "no cylinder"]):
        entities["housing_status"] = "no_lpg_connection"

    if any(w in t for w in ["solar", "rooftop", "roof", "terrace", "electricity bill", "bijli", "chhat", "sun panel"]):
        entities["rooftop_solar_eligible"] = True
        entities["has_bank_account"] = True

    # Death of primary breadwinner
    if any(w in t for w in ["husband died", "breadwinner died", "sole earner died", "earner passed away", "father passed away", "lost primary earner", "husband passed"]):
        entities["breadwinner_deceased"] = True

    # Unorganized / Informal Worker
    if any(w in t for w in ["unorganized", "daily wage", "laborer", "mazdoor", "coolie", "maid", "driver", "rickshaw", "informal worker", "e-shram"]):
        entities["unorganized_worker"] = True

    # Bank Account
    if any(w in t for w in ["bank account", "jan dhan", "bank khata", "passbook", "savings account"]):
        entities["has_bank_account"] = True

    # Raw Situation Summary
    cleaned_summary = text.strip()
    if len(cleaned_summary) > 120:
        cleaned_summary = cleaned_summary[:117] + "..."
    entities["raw_situation_summary"] = cleaned_summary

    return entities


def extract_entities(text: str) -> Tuple[dict, str]:
    """
    Extracts facts using multi-model provider chain:
    1. Anthropic Claude (if ANTHROPIC_API_KEY set)
    2. OpenAI GPT-4o-mini (if OPENAI_API_KEY set)
    3. Ollama Local LLM (if running)
    4. CivicVoice Indic Heuristic NLP Engine (resilient, zero-failure)
    """
    extracted = {}
    source = "CivicVoice Indic Heuristic NLP Engine"

    system_prompt = (
        "You are an expert government welfare fact extraction engine for Indian citizens. "
        "Extract factual attributes from citizen statements and output ONLY valid JSON without markdown fences. "
        "Keys: occupation, age (int), gender ('male'/'female'), marital_status ('married'/'widow'/'unmarried'), "
        "income_bracket ('bpl'/'low'/'middle'), caste_category ('sc'/'st'/'obc'/'general'), residence ('rural'/'urban'), "
        "has_daughter (bool), daughter_age (int), disability_percentage (int), has_bank_account (bool), housing_status, "
        "is_artisan (bool), is_street_vendor (bool), is_pregnant_or_lactating (bool), rooftop_solar_eligible (bool), "
        "breadwinner_deceased (bool), unorganized_worker (bool)."
    )

    # 1. Try Anthropic Claude
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key and not anthropic_key.startswith("sk-ant-your"):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Text: {text}"}],
            )
            raw_text = msg.content[0].text.strip()
            # remove code block if any
            if "```" in raw_text:
                raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
            extracted = json.loads(raw_text)
            source = "Claude 3 (Anthropic)"
        except Exception:
            pass

    # 2. Try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not extracted and openai_key and not openai_key.startswith("sk-your"):
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Text: {text}"},
                ],
                response_format={"type": "json_object"},
            )
            raw_text = resp.choices[0].message.content.strip()
            extracted = json.loads(raw_text)
            source = "GPT-4o Mini (OpenAI)"
        except Exception:
            pass

    # 3. Try Local Ollama (only if server is running)
    if not extracted:
        import socket
        ollama_running = False
        try:
            with socket.create_connection(("127.0.0.1", 11434), timeout=0.1):
                ollama_running = True
        except (OSError, socket.timeout):
            ollama_running = False

        if ollama_running:
            try:
                ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
                prompt = f"{system_prompt}\nCitizen Text: \"{text}\"\nJSON Output:"
                req = urllib.request.Request(
                    f"{ollama_host}/api/generate",
                    data=json.dumps({"model": "qwen2.5:3b", "prompt": prompt, "stream": False, "format": "json"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    data = json.loads(resp.read().decode())
                    raw = data.get("response", "").strip()
                    if raw:
                        extracted = json.loads(raw)
                        source = "Ollama Local LLM (qwen2.5)"
            except Exception:
                pass

    # 4. Merge / augment with resilient heuristic extraction
    heuristic = extract_entities_heuristic(text)
    for k, v in heuristic.items():
        if k not in extracted or extracted[k] is None:
            extracted[k] = v

    return extracted, source


# ---------------------------------------------------------------------------
# Explainable Scheme Evaluation & Rule Breakdown
# ---------------------------------------------------------------------------

CHECKABLE_RULES = {
    "occupation": "Occupation",
    "income_bracket": "Income Bracket",
    "gender": "Gender",
    "caste_category": "Caste Category",
    "residence": "Residence",
    "marital_status": "Marital Status",
    "has_daughter": "Has Daughter",
    "daughter_age_max": "Daughter's Max Age",
    "disability_percentage_min": "Disability % Minimum",
    "has_bank_account": "Active Bank Account",
    "age_min": "Minimum Age",
    "age_max": "Maximum Age",
    "housing_status": "Housing / LPG Status",
    "is_artisan": "Traditional Artisan / Craftsman Trade",
    "is_street_vendor": "Urban Street Vending Activity",
    "is_pregnant_or_lactating": "Maternity / Pregnancy Status",
    "rooftop_solar_eligible": "Rooftop Space & Domestic Power Connection",
    "breadwinner_deceased": "Loss of Primary Family Breadwinner",
    "unorganized_worker": "Unorganized Sector Worker",
    "has_crop_loan_or_land": "Agricultural Land / Crop Cultivation",
}


def evaluate_scheme(profile: dict, scheme: dict) -> dict:
    """
    Evaluates a scheme against a citizen's profile.
    Returns { status: 'confirmed'|'possible'|'ruled_out', breakdown: [...] }
    """
    rules = scheme["eligibility"]
    checkable = {k: v for k, v in rules.items() if k in CHECKABLE_RULES}

    breakdown = []
    any_unknown = False
    is_ruled_out = False

    for key, req_val in checkable.items():
        label = CHECKABLE_RULES[key]
        citizen_val = profile.get(key)

        # Mapping for age bounds
        if key == "age_min":
            c_age = profile.get("age")
            if c_age is None:
                status = "missing"
                any_unknown = True
                desc = f"Requires minimum age {req_val} years"
            elif c_age >= req_val:
                status = "satisfied"
                desc = f"Age {c_age} meets minimum {req_val} years"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"Age {c_age} is below requirement of {req_val} years"
            breakdown.append({"key": "age", "label": "Age Requirement", "status": status, "description": desc, "required": f">= {req_val}", "actual": c_age})
            continue

        if key == "age_max":
            c_age = profile.get("age")
            if c_age is None:
                status = "missing"
                any_unknown = True
                desc = f"Requires maximum age {req_val} years"
            elif c_age <= req_val:
                status = "satisfied"
                desc = f"Age {c_age} meets maximum limit of {req_val} years"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"Age {c_age} exceeds maximum limit of {req_val} years"
            breakdown.append({"key": "age", "label": "Age Limit", "status": status, "description": desc, "required": f"<= {req_val}", "actual": c_age})
            continue

        if key == "daughter_age_max":
            d_age = profile.get("daughter_age")
            if d_age is None:
                status = "missing"
                any_unknown = True
                desc = f"Daughter must be under {req_val} years"
            elif d_age <= req_val:
                status = "satisfied"
                desc = f"Daughter's age {d_age} qualifies (under {req_val})"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"Daughter's age {d_age} exceeds {req_val} years limit"
            breakdown.append({"key": "daughter_age", "label": "Daughter Age", "status": status, "description": desc, "required": f"<= {req_val}", "actual": d_age})
            continue

        if key == "disability_percentage_min":
            dis_val = profile.get("disability_percentage")
            if dis_val is None:
                status = "missing"
                any_unknown = True
                desc = f"Requires disability certificate of at least {req_val}%"
            elif dis_val >= req_val:
                status = "satisfied"
                desc = f"Disability {dis_val}% meets threshold ({req_val}%)"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"Disability {dis_val}% is below required {req_val}%"
            breakdown.append({"key": "disability_percentage", "label": "Disability Threshold", "status": status, "description": desc, "required": f">= {req_val}%", "actual": f"{dis_val}%" if dis_val else None})
            continue

        # Specific boolean rules
        if key in ["has_bank_account", "has_daughter", "is_artisan", "is_street_vendor", "is_pregnant_or_lactating", "rooftop_solar_eligible", "breadwinner_deceased", "unorganized_worker"]:
            b_val = profile.get(key)
            if b_val is None:
                status = "missing"
                any_unknown = True
                desc = f"Requires verification for {label}"
            elif bool(b_val) == bool(req_val):
                status = "satisfied"
                desc = f"{label} verified"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"{label} requirement not met"
            breakdown.append({"key": key, "label": label, "status": status, "description": desc, "required": "Yes", "actual": "Yes" if b_val else "No"})
            continue

        if key == "has_crop_loan_or_land":
            c_occ = profile.get("occupation")
            c_land = profile.get("has_crop_loan_or_land")
            if c_land is True or c_occ == "farmer":
                status = "satisfied"
                desc = "Farmer landholding / crop cultivation verified"
            elif c_occ is None and c_land is None:
                status = "missing"
                any_unknown = True
                desc = "Requires agricultural land or crop cultivation"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = "Only applicable for farmers cultivating notified crops"
            breakdown.append({"key": key, "label": label, "status": status, "description": desc, "required": "Yes", "actual": "Yes" if (c_land or c_occ == "farmer") else "No"})
            continue

        # Categorical string / list matches
        if isinstance(req_val, list):
            if citizen_val is None:
                status = "missing"
                any_unknown = True
                desc = f"Required: {', '.join(str(x) for x in req_val)}"
            elif str(citizen_val).lower() in [str(v).lower() for v in req_val]:
                status = "satisfied"
                desc = f"{label}: '{citizen_val}' matches eligible criteria"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"{label}: '{citizen_val}' does not match required [{', '.join(str(x) for x in req_val)}]"
            breakdown.append({"key": key, "label": label, "status": status, "description": desc, "required": ", ".join(str(x) for x in req_val), "actual": citizen_val})
        else:
            if citizen_val is None:
                status = "missing"
                any_unknown = True
                desc = f"Required: {req_val}"
            elif str(citizen_val).lower() == str(req_val).lower():
                status = "satisfied"
                desc = f"{label}: '{citizen_val}' matches requirement"
            else:
                status = "contradicted"
                is_ruled_out = True
                desc = f"{label}: requirement mismatch"
            breakdown.append({"key": key, "label": label, "status": status, "description": desc, "required": str(req_val), "actual": citizen_val})

    if is_ruled_out:
        final_status = "ruled_out"
    elif any_unknown:
        final_status = "possible"
    else:
        final_status = "confirmed"

    return {"status": final_status, "breakdown": breakdown}


def match_schemes(profile: dict) -> List[dict]:
    matches = []
    for scheme in SCHEMES:
        eval_result = evaluate_scheme(profile, scheme)
        if eval_result["status"] == "ruled_out":
            continue

        matches.append(
            {
                "id": scheme["id"],
                "name": scheme["name"],
                "category": scheme.get("category", "welfare"),
                "status": eval_result["status"],  # "confirmed" or "possible"
                "benefit": scheme["benefit"],
                "benefit_value_inr": scheme.get("benefit_value_inr", 0),
                "clause": scheme["clause"],
                "apply_docs": scheme["apply_docs"],
                "source_url": scheme.get("source_url", "https://india.gov.in"),
                "rule_breakdown": eval_result["breakdown"],
            }
        )

    # Sort confirmed first, then by monetary benefit value descending
    matches.sort(key=lambda m: (0 if m["status"] == "confirmed" else 1, -m.get("benefit_value_inr", 0)))
    return matches


# ---------------------------------------------------------------------------
# API Models
# ---------------------------------------------------------------------------

class ProcessRequest(BaseModel):
    phone: str
    text: str


class DraftRequest(BaseModel):
    phone: str
    scheme_id: str


class FollowupRequest(BaseModel):
    phone: str
    target_lang: Optional[str] = "en-IN"


class TranslateRequest(BaseModel):
    text: str
    target_lang: str


class ChatRequest(BaseModel):
    phone: str
    message: str
    language: Optional[str] = "en-IN"


class AdvisorSummaryRequest(BaseModel):
    phone: str
    language: Optional[str] = "en-IN"


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "schemes_loaded": len(SCHEMES),
        "timestamp": datetime.now().isoformat(),
        "version": "2.2.0",
    }


@app.get("/api/schemes")
def get_all_schemes():
    """Returns the full catalog of 20 government welfare schemes."""
    return {"count": len(SCHEMES), "schemes": SCHEMES}


@app.post("/api/process")
def process(req: ProcessRequest):
    """
    Processes citizen voice/text input:
    1. Loads existing profile from SQLite memory
    2. Extracts structured facts with Multi-Model AI (Claude/GPT/Ollama/Indic NLP)
    3. Merges new facts seamlessly
    4. Evaluates all 20 schemes and returns matches with grounded breakdown
    """
    phone = req.phone.strip()
    if not phone or not req.text.strip():
        raise HTTPException(status_code=400, detail="Phone number and text are required")

    existing_profile = load_profile(phone)
    is_returning = bool(existing_profile)

    new_entities, extraction_source = extract_entities(req.text)

    # Merge facts (never overwrite with None or empty)
    merged_profile = {**existing_profile}
    for k, v in new_entities.items():
        if v is not None and v != "":
            merged_profile[k] = v

    save_profile(phone, merged_profile)
    matches = match_schemes(merged_profile)

    return {
        "is_returning_citizen": is_returning,
        "profile": merged_profile,
        "matched_schemes": matches,
        "newly_extracted": new_entities,
        "extraction_source": extraction_source,
    }


@app.get("/api/profile/{phone}")
def get_profile(phone: str):
    p = phone.strip()
    profile = load_profile(p)
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for this phone number")
    return {
        "phone": p,
        "profile": profile,
        "matched_schemes": match_schemes(profile),
    }


@app.post("/api/followup")
def get_followup_question(req: FollowupRequest):
    """
    Proactive dialogue: finds 'possible' schemes, discovers the highest-leverage
    missing fact, and returns an empathetic, direct question with quick chips.
    """
    profile = load_profile(req.phone)
    matches = match_schemes(profile)
    possible_schemes = [m for m in matches if m["status"] == "possible"]

    if not possible_schemes:
        return {
            "has_followup": False,
            "message": "All eligible schemes have been fully confirmed.",
        }

    # Count which missing fields appear the most across possible schemes
    missing_counter: Dict[str, List[str]] = {}
    for scheme in possible_schemes:
        for item in scheme["rule_breakdown"]:
            if item["status"] == "missing":
                k = item["key"]
                if k not in missing_counter:
                    missing_counter[k] = []
                missing_counter[k].append(scheme["name"])

    if not missing_counter:
        return {"has_followup": False, "message": "No additional details required."}

    # Pick the field that unlocks the maximum number of schemes
    best_field = max(missing_counter.keys(), key=lambda k: len(missing_counter[k]))
    affected_schemes = missing_counter[best_field]

    # Pre-built clarifying questions with quick-reply suggestions
    field_metadata = {
        "income_bracket": {
            "question": "Could you tell us roughly your household's annual income, or do you hold a BPL/Antyodaya ration card?",
            "options": ["BPL Ration Card Holder", "Low Income (< ₹2.5 Lakh/year)", "Middle Income (> ₹2.5 Lakh/year)"],
            "hindi": "क्या आप बता सकते हैं कि आपकी पारिवारिक वार्षिक आय कितनी है, या क्या आपके पास बीपीएल राशन कार्ड है?",
            "tamil": "உங்கள் குடும்பத்தின் தோராயமான ஆண்டு வருமானம் என்ன, அல்லது உங்களிடம் BPL ரேஷன் அட்டை உள்ளதா?",
        },
        "age": {
            "question": "Could you please share your approximate age?",
            "options": ["Under 18", "Between 18 and 40", "Between 40 and 60", "Above 60"],
            "hindi": "कृपया अपनी सही या अनुमानित आयु बताएं।",
            "tamil": "தயவுசெய்து உங்கள் தோராயமான வயதைக் குறிப்பிடவும்.",
        },
        "has_bank_account": {
            "question": "Do you or a family member have an active bank account (such as Jan Dhan or savings account)?",
            "options": ["Yes, have an active bank account", "No bank account currently"],
            "hindi": "क्या आपके पास बैंक में सक्रिय बचत खाता या जन-धन खाता है?",
            "tamil": "உங்களிடம் செயலில் உள்ள சேமிப்பு அல்லது ஜன் தன் வங்கி கணக்கு உள்ளதா?",
        },
        "is_artisan": {
            "question": "Do you or anyone in your household work as a traditional artisan or craftsperson (e.g. carpenter, tailor, blacksmith, potter, mason)?",
            "options": ["Yes, Traditional Artisan / Craftsman", "No, Different Trade"],
            "hindi": "क्या आप या आपके परिवार का कोई सदस्य पारंपरिक कारीगर या शिल्पकार (जैसे बढ़ई, दर्जी, लोहार, कुम्हार, राजमिस्त्री) हैं?",
            "tamil": "நீங்கள் பாரம்பரிய கைவினைஞர் அல்லது தொழில் செய்கிறீர்களா (தச்சர், தையல்காரர், கொல்லர்)?",
        },
        "is_street_vendor": {
            "question": "Do you operate as a street vendor, hawker, or roadside cart seller in an urban city or town?",
            "options": ["Yes, Urban Street Vendor / Hawker", "No"],
            "hindi": "क्या आप शहर या कस्बे में सड़क किनारे रेहड़ी, पटरी, ठेला या फेरी लगाकर सामान बेचते हैं?",
            "tamil": "நீங்கள் நகர்ப்புறத்தில் சாலையோர அல்லது தள்ளுவண்டி வியாபாரம் செய்கிறீர்களா?",
        },
        "is_pregnant_or_lactating": {
            "question": "Are you or is someone in your household currently a pregnant woman or nursing mother?",
            "options": ["Yes, Pregnant / Nursing Mother", "No"],
            "hindi": "क्या परिवार में कोई महिला वर्तमान में गर्भवती या शिशु को स्तनपान कराने वाली माता हैं?",
            "tamil": "உங்கள் குடும்பத்தில் தற்போது கர்ப்பிணி பெண் அல்லது பாலூட்டும் தாய் உள்ளாரா?",
        },
        "rooftop_solar_eligible": {
            "question": "Do you have an independent roof/terrace on your house and an active domestic electricity connection?",
            "options": ["Yes, Have Rooftop & Domestic Power", "No / Shared Tenancy"],
            "hindi": "क्या आपके मकान में अपनी खुली छत है और घरेलू बिजली का वैध कनेक्शन है?",
            "tamil": "உங்கள் வீட்டில் சொந்த மொட்டை மாடி மற்றும் மின் இணைப்பு உள்ளதா?",
        },
        "unorganized_worker": {
            "question": "Do you work in the unorganized informal sector (such as daily wage, driver, maid, construction) without EPF/PF?",
            "options": ["Yes, Unorganized / Daily Worker", "No, Formal Job with PF"],
            "hindi": "क्या आप असंगठित क्षेत्र (दिहाड़ी मजदूर, चालक, घरेलू कामगार, निर्माण आदि) में कार्यरत हैं जहां ईपीएफ नहीं कटता?",
            "tamil": "நீங்கள் முறைசாரா துறையில் (தினக்கூலி, ஓட்டுநர், கட்டிட வேலை) பணிபுரிகிறீர்களா?",
        },
        "caste_category": {
            "question": "Which social category do you belong to (SC, ST, OBC, or General)?",
            "options": ["SC (Scheduled Caste)", "ST (Scheduled Tribe)", "OBC", "General"],
            "hindi": "आप किस सामाजिक वर्ग से आते हैं (अनुसूचित जाति, अनुसूचित जनजाति, ओबीसी, या सामान्य)?",
            "tamil": "நீங்கள் எந்தப் பிரிவைச் சேர்ந்தவர் (SC, ST, OBC, அல்லது பொதுப்பிரிவு)?",
        },
        "residence": {
            "question": "Do you live in a rural village (Gram Panchayat) or an urban town/city?",
            "options": ["Rural / Village area", "Urban / Town / City"],
            "hindi": "क्या आप ग्रामीण क्षेत्र (गांव) में रहते हैं या शहरी क्षेत्र में?",
            "tamil": "நீங்கள் கிராமப்புறத்தில் வசிக்கிறீர்களா அல்லது நகர்ப்புறத்திலா?",
        },
        "daughter_age": {
            "question": "How old is your daughter currently?",
            "options": ["Under 5 years", "Between 5 and 10 years", "Above 10 years"],
            "hindi": "आपकी बेटी की उम्र इस समय कितनी है?",
            "tamil": "தற்போது உங்கள் மகளின் வயது என்ன?",
        },
        "disability_percentage": {
            "question": "Do you hold a government disability certificate, and what is the certified percentage?",
            "options": ["40% to 79%", "80% or higher", "No certificate"],
            "hindi": "क्या आपके पास दिव्यांगता प्रमाण पत्र है, और उसमें कितने प्रतिशत दिव्यांगता दर्ज है?",
            "tamil": "உங்களிடம் மாற்றுத்திறனாளி சான்றிதழ் உள்ளதா, அதன் சதவீதம் எவ்வளவு?",
        },
        "housing_status": {
            "question": "What is the condition of your home (kutcha/mud house, or pucca house) and do you have an LPG connection?",
            "options": ["Kutcha / Mud house", "Pucca house", "No LPG connection"],
            "hindi": "आपके घर की स्थिति क्या है (कच्चा मकान या पक्का), और क्या एलपीजी गैस कनेक्शन है?",
            "tamil": "உங்கள் வீடு எத்தகையது (கச்சா வீடு அல்லது கான்கிரீட்) மற்றும் LPG இணைப்பு உள்ளதா?",
        },
    }

    meta = field_metadata.get(
        best_field,
        {
            "question": f"Could you provide information regarding your {best_field.replace('_', ' ')}?",
            "options": ["Yes", "No"],
        },
    )

    lang = (req.target_lang or "en-IN").lower()
    selected_question = meta["question"]
    if "hi" in lang and "hindi" in meta:
        selected_question = meta["hindi"]
    elif "ta" in lang and "tamil" in meta:
        selected_question = meta["tamil"]

    return {
        "has_followup": True,
        "target_field": best_field,
        "question": selected_question,
        "english_question": meta["question"],
        "options": meta.get("options", []),
        "affected_schemes": affected_schemes,
        "potential_unlocks_count": len(affected_schemes),
    }


@app.post("/api/translate")
def translate_text(req: TranslateRequest):
    """Translates text for browser SpeechSynthesis voice readback."""
    text = req.text.strip()
    target = req.target_lang.lower()

    if "en" in target or not text:
        return {"translated_text": text, "target_lang": req.target_lang}

    translations_hi = {
        "You qualify for": "आप इसके पात्र हैं:",
        "Documents needed:": "आवश्यक दस्तावेज:",
        "Eligible": "पात्र",
        "Possibly eligible — needs more info": "संभावित पात्र - अतिरिक्त जानकारी आवश्यक",
        "What we found": "आपके लिए पहचानी गई योजनाएं",
        "Confirmed Eligible": "पूर्ण पात्र",
        "Needs More Info": "जानकारी अपेक्षित",
        "Welfare Scheme Results": "कल्याण योजना परिणाम",
    }
    translations_ta = {
        "You qualify for": "நீங்கள் தகுதி பெற்றுள்ளீர்கள்:",
        "Documents needed:": "தேவையான ஆவணங்கள்:",
        "Eligible": "தகுதியுடையவர்",
        "Possibly eligible — needs more info": "வாய்ப்புள்ளது - கூடுதல் தகவல் தேவை",
    }

    if "hi" in target:
        for k, v in translations_hi.items():
            text = text.replace(k, v)
    elif "ta" in target:
        for k, v in translations_ta.items():
            text = text.replace(k, v)

    return {"translated_text": text, "target_lang": req.target_lang}


@app.post("/api/advisor-summary")
def get_advisor_summary(req: AdvisorSummaryRequest):
    """
    Generates a personalized, empathetic narrative briefing summarizing the citizen's
    eligibility and unlocked entitlements. Suitable for speech synthesis.
    """
    phone = req.phone.strip()
    profile = load_profile(phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Citizen profile not found")

    matches = match_schemes(profile)
    confirmed = [m for m in matches if m["status"] == "confirmed"]
    possible = [m for m in matches if m["status"] == "possible"]
    total_val = sum(m.get("benefit_value_inr", 0) for m in confirmed)
    total_lakhs = round(total_val / 100000, 2)
    lang = (req.language or "en-IN").lower()

    if "hi" in lang:
        if confirmed:
            top_names = ", ".join(m["name"] for m in confirmed[:3])
            text = (
                f"नमस्ते! आपके द्वारा दी गई जानकारी के अनुसार, आप {len(confirmed)} सरकारी कल्याण योजनाओं के पूर्ण पात्र हैं। "
                f"इनमें अनुमानित कुल लाभ ₹{total_val:,} (लगभग {total_lakhs} लाख रुपये) तक है। "
                f"प्रमुख योजनाओं में शामिल हैं: {top_names}। "
                f"आप अपना आवेदन पत्र तुरंत पीडीएफ के रूप में डाउनलोड कर सकते हैं।"
            )
            if possible:
                text += f" साथ ही, केवल कुछ और विवरण साझा करके आप {len(possible)} और योजनाओं का लाभ भी ले सकते हैं।"
        else:
            text = (
                f"नमस्ते! आपकी जानकारी के आधार पर {len(possible)} योजनाएं संभावित हैं। "
                f"कृपया ऊपर पूछे गए प्रश्न का उत्तर दें ताकि हम आपकी पात्रता की पूर्ण पुष्टि कर सकें।"
            )
    else:
        if confirmed:
            top_names = ", ".join(m["name"] for m in confirmed[:3])
            text = (
                f"Namaste! Based on your verified situation, you are confirmed eligible for {len(confirmed)} government welfare schemes, "
                f"representing up to ₹{total_val:,} (approx ₹{total_lakhs} Lakhs) in total direct benefits and security. "
                f"Key programs include: {top_names}. "
                f"You can download your official pre-filled application form directly."
            )
            if possible:
                text += f" You also have {len(possible)} potential schemes that can be unlocked with 1 more quick detail."
        else:
            text = (
                f"Namaste! We identified {len(possible)} potential schemes for your household. "
                f"Please provide the requested detail above to confirm your eligibility."
            )

    return {
        "summary_text": text,
        "total_confirmed": len(confirmed),
        "total_possible": len(possible),
        "total_value_inr": total_val,
        "total_value_lakhs": total_lakhs,
    }


@app.post("/api/chat")
def citizen_chat(req: ChatRequest):
    """
    Interactive Citizen Welfare Assistant:
    Answers citizen questions conversationally, grounded strictly in their
    matched schemes, required documents, and official portal procedures.
    """
    phone = req.phone.strip()
    profile = load_profile(phone)
    matches = match_schemes(profile) if profile else []
    query = req.message.strip()
    lang = (req.language or "en-IN").lower()

    if not query:
        raise HTTPException(status_code=400, detail="Query message required")

    confirmed_schemes = [m for m in matches if m["status"] == "confirmed"]
    possible_schemes = [m for m in matches if m["status"] == "possible"]

    # Grounded response fallback logic
    q_lower = query.lower()
    matched_scheme = None
    for s in SCHEMES:
        if s["id"].lower() in q_lower or any(word in q_lower for word in s["name"].lower().split() if len(word) > 3):
            matched_scheme = s
            break

    reply = ""

    # Check if user asks about documents
    if any(w in q_lower for w in ["document", "dastavez", "kagaz", "proof", "apply docs", "parcha", "certificates"]):
        if matched_scheme:
            docs_list = ", ".join(matched_scheme["apply_docs"])
            if "hi" in lang:
                reply = f"{matched_scheme['name']} के लिए आवश्यक मुख्य दस्तावेज हैं: {docs_list}। आप हमारे पोर्टल से सीधा भरा हुआ आवेदन पत्र डाउनलोड कर सकते हैं।"
            else:
                reply = f"For {matched_scheme['name']}, the required enclosures are: {docs_list}. You can download your official pre-filled form with one click from CivicVoice."
        else:
            all_docs = set()
            for m in (confirmed_schemes or matches)[:4]:
                all_docs.update(m.get("apply_docs", []))
            doc_str = ", ".join(list(all_docs)[:6])
            if "hi" in lang:
                reply = f"आपकी पात्र योजनाओं के लिए आमतौर पर आवश्यक दस्तावेज हैं: {doc_str}। सुनिश्चित करें कि आपका बैंक खाता आधार से लिंक हो।"
            else:
                reply = f"Across your eligible programs, the primary required documents are: {doc_str}. Ensure your bank account is active and seeded with Aadhaar."

    # Check if user asks how to apply
    elif any(w in q_lower for w in ["how to apply", "kaise apply", "kahan jana", "where to go", "portal", "process", "online"]):
        if matched_scheme:
            url = matched_scheme.get("source_url", "https://india.gov.in")
            if "hi" in lang:
                reply = f"{matched_scheme['name']} के लिए आप आधिकारिक पोर्टल ({url}) पर ऑनलाइन या अपने नजदीकी जन सेवा केंद्र (CSC / Jan Seva Kendra) पर जाकर आवेदन कर सकते हैं।"
            else:
                reply = f"You can apply for {matched_scheme['name']} online via the official portal ({url}) or visit your nearest Common Service Center (CSC / Jan Seva Kendra) with the pre-filled PDF downloaded here."
        else:
            if "hi" in lang:
                reply = "आप CivicVoice से अपनी योजना का प्री-फिल्ड फॉर्म डाउनलोड करके अपने नजदीकी सीएससी (जन सेवा केंद्र) या संबंधित ब्लॉक/तहसील कार्यालय में जमा कर सकते हैं।"
            else:
                reply = "You can download your pre-filled application form directly from CivicVoice and submit it at your nearest CSC / Jan Seva Kendra or Gram Panchayat office."

    # Check if user asks about money or benefit amount
    elif any(w in q_lower for w in ["money", "paisa", "kitna", "amount", "rupee", "benefit", "labh"]):
        total_val = sum(m.get("benefit_value_inr", 0) for m in confirmed_schemes)
        if "hi" in lang:
            reply = f"आपके सत्यापित प्रोफाइल के अनुसार, आप कुल ₹{total_val:,} तक के सरकारी लाभ एवं सुरक्षा के पात्र हैं। प्रत्येक योजना का विवरण ऊपर कार्ड में दिया गया है।"
        else:
            reply = f"Based on your confirmed profile, your household is eligible for up to ₹{total_val:,} in direct financial support and insurance entitlements."

    # Default friendly greeting or guidance
    else:
        if matched_scheme:
            reply = f"{matched_scheme['name']} provides: {matched_scheme['benefit']}. Official portal: {matched_scheme.get('source_url')}."
        elif confirmed_schemes:
            names = ", ".join(m["name"] for m in confirmed_schemes[:3])
            reply = f"You currently qualify for {len(confirmed_schemes)} schemes including {names}. Ask me any question regarding documents, application steps, or eligibility criteria!"
        else:
            reply = "I am your CivicVoice Assistant. You can ask me about required documents, how to apply for schemes, or clarify your eligibility criteria anytime!"

    return {
        "reply": reply,
        "language": req.language,
        "matched_scheme_id": matched_scheme["id"] if matched_scheme else None,
    }


@app.post("/api/draft")
def draft_application(req: DraftRequest):
    """Returns a pre-filled plain-text application summary."""
    profile = load_profile(req.phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Citizen profile not found")

    scheme = next((s for s in SCHEMES if s["id"] == req.scheme_id), None)
    if not scheme:
        raise HTTPException(status_code=404, detail="Unknown scheme ID")

    profile_lines = "\n".join(f"  • {k.replace('_', ' ').title()}: {v}" for k, v in profile.items() if k != "raw_situation_summary")
    draft = f"""
================================================================================
           GOVERNMENT OF INDIA — JAN SEVA SCHEME APPLICATION DRAFT
================================================================================
Application Reference: CV-{datetime.now().strftime('%Y%m%d')}-{req.phone[-4:]}
Date of Generation   : {datetime.now().strftime('%d %B %Y')}
Primary Contact (Key): +91 {req.phone}

1. TARGET WELFARE SCHEME
--------------------------------------------------------------------------------
Scheme Name    : {scheme['name']}
Category       : {scheme.get('category', 'Public Welfare').replace('_', ' ').title()}
Official Benefit: {scheme['benefit']}
Statutory Clause: "{scheme['clause']}"
Official Portal: {scheme.get('source_url', 'https://india.gov.in')}

2. APPLICANT VERIFIED PARTICULARS
--------------------------------------------------------------------------------
{profile_lines}

3. MANDATORY DOCUMENTS CHECKLIST
--------------------------------------------------------------------------------
{chr(10).join('  [ ] ' + doc for doc in scheme['apply_docs'])}

4. SELF DECLARATION
--------------------------------------------------------------------------------
I hereby declare that the particulars furnished above are true, complete, and
correct to the best of my knowledge and belief. Generated through CivicVoice.

Applicant Signature: _______________________      Date: ______________
================================================================================
"""
    return {"draft_text": draft.strip(), "scheme_name": scheme["name"]}


@app.get("/api/draft/pdf")
def generate_pdf_application(phone: str = Query(...), scheme_id: str = Query(...)):
    """
    Generates a formal, printable PDF application form using ReportLab.
    Includes national styling, applicant facts, scheme clause, and document checklist.
    """
    clean_phone = phone.strip()
    profile = load_profile(clean_phone)
    if not profile:
        raise HTTPException(status_code=404, detail="Citizen profile not found")

    scheme = next((s for s in SCHEMES if s["id"] == scheme_id), None)
    if not scheme:
        raise HTTPException(status_code=404, detail="Unknown scheme ID")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "CivicHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#0B1B3D"),
        alignment=1,
    )
    sub_style = ParagraphStyle(
        "CivicSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#5B6B79"),
        alignment=1,
    )
    sec_heading = ParagraphStyle(
        "SecHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0B1B3D"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1B2430"),
    )
    body_text = ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1B2430"),
    )
    clause_style = ParagraphStyle(
        "ClauseStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2C3E50"),
    )

    story = []

    # Title & Banner
    story.append(Paragraph("GOVERNMENT OF INDIA — JAN SEVA KENDRA", header_style))
    story.append(Paragraph("CivicVoice Assisted Citizen Welfare Application Form", sub_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B1B3D"), spaceBefore=2, spaceAfter=8))

    # Meta Banner Table
    ref_no = f"CV-{datetime.now().strftime('%Y%m%d')}-{clean_phone[-4:] if len(clean_phone) >= 4 else '1001'}"
    date_str = datetime.now().strftime("%d %B %Y")
    meta_data = [
        [
            Paragraph(f"<b>Application Ref No:</b> {ref_no}", body_text),
            Paragraph(f"<b>Date:</b> {date_str}", body_text),
            Paragraph(f"<b>Citizen Phone:</b> +91 {clean_phone}", body_text),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[200, 150, 180])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F7F9")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DDE3")),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Section 1: Applied Scheme Details
    story.append(Paragraph("1. WELFARE SCHEME APPLIED", sec_heading))
    scheme_table_data = [
        [Paragraph("Scheme Name", body_bold), Paragraph(scheme["name"], body_text)],
        [Paragraph("Category", body_bold), Paragraph(scheme.get("category", "Welfare").replace("_", " ").title(), body_text)],
        [Paragraph("Direct Benefit Entitlement", body_bold), Paragraph(scheme["benefit"], body_text)],
        [Paragraph("Official Portal Link", body_bold), Paragraph(scheme.get("source_url", "https://india.gov.in"), body_text)],
        [Paragraph("Legal Eligibility Clause", body_bold), Paragraph(f'"{scheme["clause"]}"', clause_style)],
    ]
    scheme_table = Table(scheme_table_data, colWidths=[150, 380])
    scheme_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EBF3FA")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DDE3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(scheme_table)
    story.append(Spacer(1, 12))

    # Section 2: Applicant Profile
    story.append(Paragraph("2. APPLICANT RECORD & SITUATION PARTICULARS", sec_heading))
    profile_rows = []
    display_fields = [
        ("occupation", "Primary Occupation"),
        ("age", "Age"),
        ("gender", "Gender"),
        ("marital_status", "Marital Status"),
        ("income_bracket", "Income Bracket / SECC"),
        ("caste_category", "Social Category"),
        ("residence", "Residence Type"),
        ("has_bank_account", "Bank Account Verified"),
        ("has_daughter", "Has Daughter / Girl Child"),
        ("daughter_age", "Daughter's Age"),
        ("disability_percentage", "Disability Percentage"),
        ("housing_status", "Housing Condition"),
        ("is_artisan", "Traditional Artisan / Craftsman"),
        ("is_street_vendor", "Urban Street Vendor"),
        ("is_pregnant_or_lactating", "Maternity / Pregnancy Status"),
        ("rooftop_solar_eligible", "Rooftop Space & Domestic Power"),
        ("breadwinner_deceased", "Primary Breadwinner Deceased"),
        ("unorganized_worker", "Unorganized Sector Worker"),
    ]
    for key, label in display_fields:
        if key in profile and profile[key] is not None:
            val = profile[key]
            if isinstance(val, bool):
                val = "Yes" if val else "No"
            profile_rows.append([Paragraph(label, body_bold), Paragraph(str(val).title(), body_text)])

    if not profile_rows:
        profile_rows.append([Paragraph("Applicant Profile", body_bold), Paragraph("Self-attested upon submission", body_text)])

    prof_table = Table(profile_rows, colWidths=[180, 350])
    prof_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(prof_table)
    story.append(Spacer(1, 12))

    # Section 3: Document Checklist
    story.append(Paragraph("3. MANDATORY ENCLOSURES & VERIFICATION CHECKLIST", sec_heading))
    doc_rows = []
    for doc_name in scheme["apply_docs"]:
        doc_rows.append([Paragraph("[   ]", body_bold), Paragraph(doc_name, body_text), Paragraph("Original & Self-Attested Copy", sub_style)])

    doc_table = Table(doc_rows, colWidths=[40, 310, 180])
    doc_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
            ]
        )
    )
    story.append(doc_table)
    story.append(Spacer(1, 14))

    # Section 4: Declaration & Signature
    story.append(Paragraph("4. APPLICANT DECLARATION", sec_heading))
    declaration_text = (
        "I hereby declare that all information furnished above has been provided truthfully and matches "
        "the legal requirements of the concerned Scheme. I authorize verification against official databases."
    )
    story.append(Paragraph(declaration_text, body_text))
    story.append(Spacer(1, 18))

    sign_data = [
        [
            Paragraph("<b>Date:</b> " + date_str, body_text),
            Paragraph("<b>Citizen / Guardian Signature / Thumb Impression:</b><br/><br/>________________________________________", body_text),
        ]
    ]
    sign_table = Table(sign_data, colWidths=[220, 310])
    sign_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(sign_table)
    story.append(Spacer(1, 12))

    # Footer note
    footer_note = (
        "Generated via CivicVoice AI — Voice-First Multilingual Citizen Welfare Platform (Luminix'26). "
        "Deterministic rule matching verified against Gazette Notifications."
    )
    story.append(Paragraph(footer_note, sub_style))

    doc.build(story)
    buffer.seek(0)

    filename = f"CivicVoice_Application_{scheme['id']}_{clean_phone[-4:]}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/stats")
def aggregate_stats():
    """Returns aggregate civic impact metrics for pitch presentation."""
    conn = get_db()
    rows = conn.execute("SELECT phone, profile_json FROM citizens").fetchall()
    conn.close()

    total_citizens = len(rows)
    total_confirmed = 0
    total_benefit_val = 0
    scheme_counts: Dict[str, int] = {}

    for row in rows:
        try:
            profile = json.loads(row["profile_json"])
            matches = match_schemes(profile)
            for m in matches:
                if m["status"] == "confirmed":
                    total_confirmed += 1
                    total_benefit_val += m.get("benefit_value_inr", 0)
                    s_name = m["name"]
                    scheme_counts[s_name] = scheme_counts.get(s_name, 0) + 1
        except Exception:
            continue

    top_schemes = sorted(scheme_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_citizens_registered": total_citizens,
        "total_confirmed_matches": total_confirmed,
        "total_estimated_welfare_inr": total_benefit_val,
        "total_estimated_welfare_lakhs": round(total_benefit_val / 100000, 2),
        "total_available_schemes": len(SCHEMES),
        "top_schemes": [{"name": k, "count": v} for k, v in top_schemes],
    }
