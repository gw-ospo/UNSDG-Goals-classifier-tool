"""
services/llm_summarizer.py

Uses Groq's OpenAI-compatible /v1/chat/completions endpoint to convert
a raw README into a non-technical, SDG-classification-ready English
summary.

When to call this:
  - After gh_cleaner has run — always pass partially-cleaned text, not raw markdown
  - Before the MiniLM/GE-Lab classifiers — this is the preprocessing step
  - For ANY language — the prompt instructs the model to output English regardless

This is NOT a general summarizer. It is a targeted extraction prompt
that knows about the SDG classification task downstream and extracts
only the signals that task needs.
"""

from __future__ import annotations

import re
import requests

import os
from dotenv import load_dotenv

from services.text_cleaner import clean_text


load_dotenv()

k = os.getenv("GROQ_API_KEY")


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"

# import hashlib
# import diskcache
# try:
#     _CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".summarizer_cache")
#     _cache = diskcache.Cache(_CACHE_DIR)
# except ImportError:
#     _cache = None

_THINKING_CAPABLE_MODEL_PREFIXES = ("Qwen/Qwen3", "qwen/qwen3")

def _supports_enable_thinking(model_id: str) -> bool:
    return model_id.startswith(_THINKING_CAPABLE_MODEL_PREFIXES)


# ─────────────────────────── prompt design ────────────────────────────────────

SYSTEM_PROMPT = """\
You are a development effectiveness analyst working for the Digital Public Goods Alliance (DPGA).
Your job is to read a software repository's README and produce a concise English paragraph that \
captures ONLY the information needed to classify the project against the 17 UN Sustainable \
Development Goals (SDGs).

A classifier model will read your output — not a human. Your output must be dense with \
domain-relevant signals and free of technical implementation noise. SMELL FOR SIGNALS VERY ACCURATELY DO NOT OUTPUT GIBERISH

EXTRACT (these signals matter for SDG classification):
- What real-world problem does this project solve?
- Who are the beneficiaries? (communities, patients, farmers, students, governments, etc.)
- In which geographic or socioeconomic context does it operate? (low-income countries, \
  rural areas, conflict zones, etc.)
- What is the project's impact or stated goal in non-technical terms?
- Which sectors or domains does it address? (health, education, water, energy, agriculture, \
  governance, environment, etc.)
- Any **explicit SDG mentions**, **SHOULD NOT BE** included verbatim, but can be used to infer the above signals.

IGNORE completely — do not let any of these appear in your output:
- Programming languages, frameworks, libraries, databases (Python, React, PostgreSQL, etc.)
- Installation instructions, build steps, Docker, CLI commands
- API endpoint documentation or code examples
- License text, contributor guidelines, changelog entries
- Navigation links, table of contents entries, badge descriptions
- Performance benchmarks, version numbers, dependency lists
- GitHub Actions, CI/CD, DevOps tooling

LANGUAGE RULE:
- Always write your output in English, regardless of the language of the input README.
- If the README is in a non-English language, translate the relevant content as you extract it.
- If the README contains English keywords mixed into a non-English document \
  (common for technical repos), use those English keywords to anchor your extraction.

FORMAT:
- Write exactly 4 to 6 sentences.
- Each sentence must be no longer than 35 words.
- Total output must be between 80 and 160 words.
- Plain prose only — no bullet points, no headings, no markdown, no lists.
- Do not begin with phrases like "This project", "The repository", "This README", \
  "This tool", or "Here is". Start directly with the domain or the problem.
- Do not include any preamble, meta-commentary, or closing remarks.

CRITICAL — DO NOT SPECULATE SECTOR RELEVANCE:
General-purpose technical infrastructure (databases, caches, message brokers,
programming frameworks, build tools, code formatters, container orchestration,
web servers) has NO domain-specific relevance, even though marketing material
often claims use across "many industries including healthcare, education,
finance." Naming industries a general tool COULD theoretically serve is NOT
a real domain signal — do not extract or repeat such claims. If the README's
own domain claim amounts to "used across many sectors" with no SPECIFIC
population, problem, or context named, treat this as having NO domain signal.

NEVER name or reference specific SDG numbers, SDG names, or the phrase
"Sustainable Development Goals" anywhere in your output, under any
circumstance, even to say a project "contributes to" or "achieves" them.

EDGE CASES:
- If the README is empty or under 20 words: write "Insufficient documentation
  to assess SDG relevance. Project name: [name if available]."
- If the README, project name, description, and topics do not contain enough
  information to determine relevance to any UN Sustainable Development Goal
  — including generic technical tools with only speculative multi-sector
  claims — respond with EXACTLY this text and nothing else:

NO_SDG_SIGNAL

Do not include the project name, description, or any other text in this case.
"""

USER_PROMPT_TEMPLATE = """\
PROJECT NAME: {name}
PROJECT DESCRIPTION (from repository metadata): {description}
TOPICS/TAGS: {topics}

README CONTENT:
{readme}

Write the SDG-classification paragraph now.\
"""
# def _cache_key(name: str, description: str, readme: str) -> str:
#     raw = f"{name.strip()}|{description.strip()}|{readme[:2000]}"
#     return hashlib.sha256(raw.encode()).hexdigest()

# ─────────────────────────── cleaner for LLM input ───────────────────────────

def _prepare_for_llm(raw_readme: str, max_chars: int = 12_000) -> str:
    """
    Light pre-cleaning before sending to the LLM.
    """
    text = clean_text(raw_readme)

    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'~~~[\s\S]*?~~~', '', text)

    text = re.sub(r'!\[.*?\]\(https?://[^\)]*(?:badge|shield|travis|'
                  r'circleci|codecov|github\.com[^\)]*(?:actions|workflow))'
                  r'[^\)]*\)', '', text, flags=re.IGNORECASE)

    text = re.sub(r'!\[([^\]]*)\]\([^\)]*\)', r'\1', text)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text[:max_chars].strip()


# ─────────────────────────── main function ────────────────────────────────────

def summarize_for_sdg(
    readme:      str,
    name:        str = "",
    description: str = "",
    topics:      list[str] | None = None,
    *,
    api_key:     str | None = None,
    temperature: float = 0.1,
    timeout:     int = 30,
) -> str:
    """
    Call the Groq API to produce an SDG-classification-ready summary.

    On any failure, returns a best-effort fallback built from the
    API-provided fields so the pipeline never blocks. Every failure path
    now prints the raw response body it saw, so you can see *why* it
    failed instead of just getting a generic "unexpected shape" message.
    """
    key = api_key or k
    if not key:
        return _fallback_summary(name, description, topics,
                                 reason="No GROQ_API_KEY found in environment")

    topics = topics or []
    #if _cache is not None:
    #     ck = _cache_key(name, description, readme)
    #     cached = _cache.get(ck)
    # if cached is not None:
    #     print("[summarizer] cache hit — skipping API call")
    #     return cached
    cleaned_readme = _prepare_for_llm(readme)

    user_message = USER_PROMPT_TEMPLATE.format(
        name        = name.strip() or "(not provided)",
        description = description.strip() or "(not provided)",
        topics      = ", ".join(topics) if topics else "(none)",
        readme      = cleaned_readme or "(README is empty)",
    )

    response = None
    data = None

    try:
        payload = {
            "model":       GROQ_MODEL,
            "temperature": temperature,
            "max_tokens":  600,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
        }

        if _supports_enable_thinking(GROQ_MODEL):
            payload["chat_template_kwargs"] = {"enable_thinking": False}

        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=timeout,
        )

        # Some OpenAI-compatible routers can return HTTP 200 with an
        # error payload instead of a 4xx/5xx status. raise_for_status()
        # alone will NOT catch that, so we check the body for an "error"
        # key before trusting the "choices" shape.
        data = response.json()

        if isinstance(data, dict) and "error" in data:
            print("\n--- GROQ API RETURNED AN ERROR PAYLOAD (HTTP 200) ---")
            print(f"status_code: {response.status_code}")
            print(data)
            print("--------------------------------------------------------\n")
            return _fallback_summary(
                name, description, topics,
                reason=f"Groq API error: {data['error']}",
            )

        response.raise_for_status()

        choices = data.get("choices") or []
        if not choices:
            print("\n--- RAW API RESPONSE (no choices returned) ---")
            print(f"status_code: {response.status_code}")
            print(data)
            print("------------------------------------------------\n")
            return _fallback_summary(name, description, topics,
                                     reason="Response had no choices")

        message = choices[0]["message"]
        summary = (message.get("content") or "").strip()

        if len(summary.split()) < 10:
            # Surface exactly what came back — e.g. if a model still
            # leaks reasoning into a separate field, or content is empty,
            # this tells you immediately instead of guessing.
            print("\n--- SHORT/EMPTY CONTENT FROM MODEL ---")
            print(f"finish_reason: {choices[0].get('finish_reason')}")
            print(f"content: {summary!r}")
            if "reasoning_content" in message:
                print(f"reasoning_content (truncated): "
                      f"{str(message['reasoning_content'])[:300]!r}")
            print("----------------------------------------\n")

        return _validate_output(summary, name, description, topics)

    except requests.exceptions.Timeout:
        return _fallback_summary(name, description, topics,
                                 reason="Groq API request timed out")

    except requests.exceptions.HTTPError as e:
        # Print the actual error body Groq sent back with the bad status code
        print("\n--- HTTP ERROR RESPONSE BODY ---")
        print(f"status_code: {response.status_code if response is not None else 'n/a'}")
        print(response.text[:2000] if response is not None else "(no response object)")
        print("--------------------------------\n")
        return _fallback_summary(name, description, topics,
                                 reason=f"Groq API HTTP error: {e}")

    except requests.exceptions.RequestException as e:
        return _fallback_summary(name, description, topics,
                                 reason=f"Groq API request error: {e}")

    except (KeyError, IndexError) as e:
        print("\n--- RAW API RESPONSE (unexpected shape) ---")
        print(f"status_code: {response.status_code if response is not None else 'n/a'}")
        print(data)
        print(f"exception: {e!r}")
        print("---------------------------------------------\n")
        return _fallback_summary(name, description, topics,
                                 reason="Unexpected Groq API response shape")


def _validate_output(text: str, name: str, description: str,
                     topics: list[str]) -> str:
    if not text or len(text.split()) < 10:
        return _fallback_summary(name, description, topics,
                                 reason="LLM returned too-short output")

    bad_starts = ("here is", "this project", "the repository",
                  "this readme", "this tool", "certainly", "sure,")
    first_words = text[:40].lower()
    if any(first_words.startswith(b) for b in bad_starts):
        lines = text.strip().splitlines()
        if len(lines) > 1:
            text = " ".join(lines[1:]).strip()

    words = text.split()
    if len(words) > 200:
        truncated = " ".join(words[:175])
        last_period = max(truncated.rfind("."), truncated.rfind("!"),
                          truncated.rfind("?"))
        if last_period > len(truncated) // 2:
            text = truncated[:last_period + 1]
        else:
            text = truncated

    return text


def _fallback_summary(name: str, description: str,
                      topics: list[str] | None,
                      reason: str = "") -> str:
    parts = [p for p in [name, description] if p and p.strip()]
    if topics:
        parts.append("Topics: " + ", ".join(topics))
    if reason:
        parts.append(f"(LLM summarization unavailable: {reason})")
    return " . ".join(parts) if parts else ""