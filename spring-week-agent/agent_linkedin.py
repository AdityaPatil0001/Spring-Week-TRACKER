"""Publicly accessible networking and skills research via TinyFish."""
from __future__ import annotations

import os
from urllib.parse import quote_plus
from typing import Any

from tinyfish import TinyFish
from agent_spring import _as_text, _json_from_text


def find_networking_insights(company_name: str, program_title: str, api_key: str | None = None) -> list[dict[str, Any]]:
    key = api_key or os.getenv("TINYFISH_API_KEY")
    if not key:
        raise RuntimeError("Set TINYFISH_API_KEY in your .env file or environment.")
    client = TinyFish(api_key=key)
    goal = f"""Research publicly indexed LinkedIn profile pages and other public professional bios
for people who mention the {program_title} at {company_name}, or early-career/graduate roles
there. Do not sign in, interact with accounts, or attempt to access private information.
Return ONLY a JSON array with objects containing person_name, current_or_past_role,
education (string), technical_skills (array of strings), soft_skills (array of strings),
profile_url, evidence_note. Include only public URLs and evidence actually visible on pages;
use empty strings/lists for unavailable fields. If no useful public profiles are found, return []."""
    query = quote_plus(f"{company_name} {program_title} LinkedIn")
    response = client.agent.run(goal=goal, url=f"https://www.google.com/search?q={query}")
    parsed = _json_from_text(_as_text(response))
    if isinstance(parsed, dict):
        parsed = parsed.get("profiles", parsed.get("results", []))
    if not isinstance(parsed, list):
        raise ValueError("TinyFish response was not a list of profiles.")
    result = []
    for item in parsed:
        if isinstance(item, dict):
            result.append({
                "person_name": str(item.get("person_name") or ""),
                "current_or_past_role": str(item.get("current_or_past_role") or ""),
                "education": str(item.get("education") or ""),
                "technical_skills": item.get("technical_skills") if isinstance(item.get("technical_skills"), list) else [],
                "soft_skills": item.get("soft_skills") if isinstance(item.get("soft_skills"), list) else [],
                "profile_url": str(item.get("profile_url") or ""),
                "evidence_note": str(item.get("evidence_note") or ""),
            })
    return result
