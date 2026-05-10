"""Claude-powered AI features: scoring, insights, NL search parsing."""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage


EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]
MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"


def _new_chat(session_id: str, system_message: str) -> LlmChat:
    return LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message,
    ).with_model(MODEL_PROVIDER, MODEL_NAME)


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of an LLM response."""
    # Strip code fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # First JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in LLM response: {text[:200]}")
    return json.loads(match.group(0))


async def generate_property_insights(property_dict: dict) -> dict:
    """Generate investment analysis: score (0-100), grade (A-F), summary, pros, cons."""
    system = (
        "You are an expert Texas real-estate investment analyst specializing in "
        "tax-delinquent and HOA-lien properties. You output ONLY a single JSON object, "
        "no prose, no markdown fences."
    )
    payload = {
        "address": property_dict.get("address"),
        "city": property_dict.get("city"),
        "county": property_dict.get("county"),
        "property_type": property_dict.get("property_type"),
        "legal_description": property_dict.get("legal_description"),
        "acres": property_dict.get("acres"),
        "year_built": property_dict.get("year_built"),
        "tax_owed": property_dict.get("tax_owed"),
        "minimum_bid": property_dict.get("minimum_bid"),
        "adjudged_value": property_dict.get("adjudged_value"),
        "has_hoa_lien": property_dict.get("has_hoa_lien"),
        "hoa_lien_amount": property_dict.get("hoa_lien_amount"),
        "tax_status": property_dict.get("tax_status"),
    }
    user_prompt = (
        "Analyze this distressed Texas property for investment potential. "
        "Consider: discount vs. value, county economic outlook, redemption risk, "
        "lien-stacking risk, property condition signals from description. "
        "Return strict JSON with keys:\n"
        '  "score": integer 0-100,\n'
        '  "grade": one of "A","B","C","D","F",\n'
        '  "summary": one sentence (max 220 chars),\n'
        '  "pros": array of 2-4 short strings,\n'
        '  "cons": array of 2-4 short strings.\n\n'
        f"Property: {json.dumps(payload)}"
    )
    chat = _new_chat(session_id=f"insight-{property_dict.get('id', 'x')}", system_message=system)
    response = await chat.send_message(UserMessage(text=user_prompt))
    data = _extract_json(response)
    return {
        "score": int(data.get("score", 50)),
        "grade": str(data.get("grade", "C"))[:1].upper(),
        "summary": str(data.get("summary", ""))[:300],
        "pros": [str(p)[:160] for p in (data.get("pros") or [])][:4],
        "cons": [str(c)[:160] for c in (data.get("cons") or [])][:4],
    }


async def parse_natural_language_query(query: str) -> dict:
    """Convert natural language into structured search filters."""
    system = (
        "You convert natural-language property-search queries into JSON filters. "
        "Output ONLY a single JSON object. Supported counties: McLennan, Hill, Bosque. "
        "Supported property_type values: residential, commercial, land, manufactured_home, "
        "mixed_use, unknown."
    )
    schema = (
        '{\n'
        '  "counties": ["..."] or null,\n'
        '  "cities": ["..."] or null,\n'
        '  "zip_code": "..." or null,\n'
        '  "property_type": "..." or null,\n'
        '  "min_amount": number or null,\n'
        '  "max_amount": number or null,\n'
        '  "has_hoa_lien": true/false or null,\n'
        '  "tax_status": "..." or null,\n'
        '  "min_acres": number or null,\n'
        '  "query": "free-text remainder" or null,\n'
        '  "interpreted": "one sentence restating the query"\n'
        '}'
    )
    user_prompt = (
        f'Schema:\n{schema}\n\n'
        f'Convert this query: "{query}"\n'
        "Use null for unspecified fields. min/max_amount refers to delinquent tax / minimum bid in USD."
    )
    chat = _new_chat(session_id=f"nl-{abs(hash(query))}", system_message=system)
    response = await chat.send_message(UserMessage(text=user_prompt))
    data = _extract_json(response)
    interpreted = str(data.pop("interpreted", "Searching properties..."))
    filters = {k: v for k, v in data.items() if v is not None and v != ""}
    return {"interpreted": interpreted, "filters": filters}
