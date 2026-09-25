from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv(os.path.join("config", ".env"))
load_dotenv(".env", override=True)


def _anthropic_key() -> str:
    return (os.environ.get("ANTHROPIC_API_KEY", "")).strip()

def _google_api_key() -> str:
    return (
        os.environ.get("GOOGLE_API_KEY", "")
        or os.environ.get("GEMINI_API_KEY", "")
    ).strip()

def default_chat_model() -> str:
    explicit = (os.environ.get("TRIP_PLANNER_MODEL") or os.environ.get("TRIP_CHAT_MODEL") or "").strip()
    if explicit:
        return explicit
    if _anthropic_key():
        return "anthropic:claude-sonnet-4-6"
    if _google_api_key():
        return os.environ.get("TRIP_GOOGLE_MODEL", "google_genai:gemini-2.5-flash").strip()
    raise RuntimeError("No LLM key found.")

def default_router_model() -> str:
    explicit = os.environ.get("TRIP_ROUTER_MODEL", "").strip()
    if explicit:
        return explicit
    if _anthropic_key():
        return "anthropic:claude-haiku-4-5-20251001"
    if _google_api_key():
        return os.environ.get("TRIP_GOOGLE_MODEL", "google_genai:gemini-2.0-flash").strip()
    return default_chat_model()


def _llm_max_tokens() -> int:
    return int(os.environ.get("TRIP_LLM_MAX_TOKENS", "16000"))


def _make_llm(model_id: str):
    max_tok = _llm_max_tokens()
    try:
        return init_chat_model(model_id, timeout=_llm_timeout_seconds(), max_tokens=max_tok)
    except TypeError:
        return init_chat_model(model_id, max_tokens=max_tok)

def _make_llm_with_fallback(primary_id: str, fallback_id: str | None):
    primary = _make_llm(primary_id)
    if fallback_id and fallback_id != primary_id and _gk:
        try:
            _log(f"LLM fallback configured: {primary_id} → {fallback_id}")
            return primary.with_fallbacks([_make_llm(fallback_id)])
        except Exception as e:
            _log(f"Could not configure fallback LLM ({fallback_id}): {e}")
    return primary


def _ctx_json(ctx: dict[str, Any]) -> str:
    full = json.dumps(ctx, ensure_ascii=False)
    limit = _context_json_max_chars()
    _log(f"CONTEXT SIZE     {len(full)} chars (limit {limit}{', TRUNCATED' if len(full) > limit else ', ok'})")
    return full[:limit]


def _llm_timeout_seconds() -> float:
    return float(os.environ.get("TRIP_LLM_TIMEOUT_SEC", "180"))

def _context_json_max_chars() -> int:
    return int(os.environ.get("TRIP_CONTEXT_JSON_MAX", "16000"))


def _extract_text(content) -> str:
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return str(content) if content else ""

def _log(msg: str) -> None:
    if os.environ.get("TRIP_QUIET", "").strip().lower() in ("1", "true", "yes"):
        return
    print(f"[trip_planner] {msg}", flush=True)

def _now_ms() -> float:
    return time.perf_counter() * 1000.0

def _bump_timing(state, node: str, started: float) -> dict[str, float]:
    timings = dict(state.get("node_timings_ms") or {})
    timings[node] = round(_now_ms() - started, 2)
    return timings

_ak = _anthropic_key()
_gk = _google_api_key()
if _ak:
    os.environ.setdefault("ANTHROPIC_API_KEY", _ak)
if _gk:
    os.environ.setdefault("GOOGLE_API_KEY", _gk)
if not _ak and not _gk:
    raise RuntimeError(
        "No LLM key found. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY."
    )

_model_id = default_chat_model()
_router_model_id = default_router_model()
_fallback_smart = "google_genai:gemini-2.5-flash" if _ak and _gk else None
_fallback_fast = "google_genai:gemini-2.5-flash" if _ak and _gk else None

llm = _make_llm_with_fallback(_model_id, _fallback_smart)
llm_fast = _make_llm_with_fallback(_router_model_id, _fallback_fast)

_CRO_DIACRITICS = set("čćžšđČĆŽŠĐ")

_CRO_WORDS = {
    "hej", "bok", "molim", "hvala", "zelim", "želim", "htio", "htjela", "bih",
    "hocu", "hoću", "putovati", "putujem", "putovanje", "idem", "ici", "ići",
    "trebam", "treba", "mogu", "mozes", "možeš", "napravi", "daj", "gdje",
    "kako", "sto", "što", "koji", "koje", "koliko", "kada", "kad", "zasto",
    "zašto", "smjestaj", "smještaj", "autobus", "autobusom", "busom",
    "vlak", "vlakom", "avion", "avionom", "noci", "noći", "noc", "noć", "dana",
    "dan", "grad", "grada", "povratna", "povratnu", "povratno", "jednosmjerna",
    "jednosmjernu", "cijena", "jeftino", "najjeftinije", "putnika", "osoba",
    "osobe", "nije", "nema", "nisam", "jesam", "ovaj", "ova", "ovo", "oni",
    "ona", "takoder", "također", "prema", "iz", "ali",
}

_ENG_WORDS = {
    "the", "you", "your", "want", "from", "how", "what", "where", "when",
    "hotel", "train", "flight", "flights", "trip", "round", "way", "please",
    "thanks", "thank", "could", "would", "need", "hello", "hey", "hi", "with",
    "there", "here", "find", "looking", "travel", "cheapest", "price", "night",
    "nights", "days", "city", "return", "oneway", "roundtrip", "going",
}


def detect_language(text: str) -> str | None:
    if not text:
        return None
    if any(ch in _CRO_DIACRITICS for ch in text):
        return "hr"
    tokens = re.findall(r"[a-zA-Zà-ÿ]+", text.lower())
    if any(t in _CRO_WORDS for t in tokens):
        return "hr"
    if any(t in _ENG_WORDS for t in tokens):
        return "en"
    return None


def resolve_language(state: dict[str, Any] | None, text: str) -> str:
    detected = detect_language(text)
    if detected:
        return detected
    return (state or {}).get("user_language") or "en"


def lang_directive(lang: str) -> str:
    if lang == "hr":
        return (
            "\n\nVAŽNO: Korisnik piše na hrvatskom jeziku. "
            "Napiši cijeli svoj odgovor na hrvatskom jeziku, prirodno i tečno."
        )
    return ""


def L(lang: str, en: str, hr: str) -> str:
    return hr if lang == "hr" else en