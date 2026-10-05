"""TinyFish-powered search for Spring Week opportunities."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from tinyfish import TinyFish


def _as_text(response: Any) -> str:
    result = getattr(response, "result", response)
    if isinstance(result, (dict, list)):
        return json.dumps(result)
    return str(result or "")


def _json_from_text(text: str) -> Any:
    """Decode JSON returned directly or embedded in explanatory text."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise ValueError("TinyFish did not return a JSON array of opportunities.")


def search_spring_weeks(criteria: dict[str, str], api_key: str | None = None) -> list[dict[str, str]]:
    key = api_key or os.getenv("TINYFISH_API_KEY")
    if not key:
        raise RuntimeError("Set TINYFISH_API_KEY in your .env file or environment.")
    client = TinyFish(api_key=key)
    goal = f"""Search the public web and employer career portals for open or upcoming Spring Week,
Spring Insight, insight day and first-year internship programs matching these candidate criteria:
Sector: {criteria.get('sector', 'Any')}; course/major: {criteria.get('course', 'Any')};
year of study: {criteria.get('year', 'Any')}; degree: {criteria.get('degree', 'Any')};
target keywords/companies: {criteria.get('keywords', 'Any')}.
Prefer official employer career pages. Include only verifiable opportunities; do not invent fields.
Return ONLY a JSON array. Each item must have string fields company_name, program_title,
sector, application_deadline, location, direct_application_url. Use an empty string when
unknown. Include the source URL in direct_application_url and ensure it is a direct employer
application/program page where available."""
    response = client.agent.run(goal=goal, url="https://www.google.com/search?q=UK+spring+week+programmes+2026+careers")
    parsed = _json_from_text(_as_text(response))
    if isinstance(parsed, dict):
        parsed = parsed.get("opportunities", parsed.get("results", []))
    if not isinstance(parsed, list):
        raise ValueError("TinyFish response was not a list of opportunities.")
    fields = ("company_name", "program_title", "sector", "application_deadline", "location", "direct_application_url")
    output = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        row = {field: str(item.get(field) or "").strip() for field in fields}
        if row["company_name"] or row["program_title"]:
            output.append(row)
    return output
