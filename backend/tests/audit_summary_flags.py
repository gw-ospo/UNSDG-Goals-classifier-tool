"""
audit_summary_flags.py — manual-review worksheet for LLM-summary flags.

Implements recommendation #6 from docs/EVAL_DPGA_150_RESULTS.md §8:

    "Manually audit the 7 numeric-claim summaries and any with word-overlap
     < 0.6 (recorded in report['flags']) before trusting summaries for
     downstream claims."

Reads a report JSON produced by eval_dpga_150.py (default: the newest
backend/.eval_cache/report_*.json) and emits a Markdown worksheet listing every
flagged summary in full — project, URL, issue, numeric claims present in the
summary vs. found in the source, word-overlap, and the complete summary text —
so a maintainer can review each one and record a pass/fail verdict without
needing network access or a live model.

Usage:
    python audit_summary_flags.py [path/to/report.json] [--out OUTPUT.md]

Examples:
    python audit_summary_flags.py                              # newest cached report
    python audit_summary_flags.py backend/.eval_cache/report_20260814_195637.json
    python audit_summary_flags.py report.json --out docs/SUMMARY_AUDIT.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
CACHE_DEFAULT = BACKEND_DIR / ".eval_cache"

ISSUE_LABELS = {
    "low word-overlap (possible hallucination)": "low word-overlap",
    "SDG number leaked into summary": "SDG leak",
    "numeric claims not in source (possible hallucination)": "numeric claims",
}


def find_newest_report(cache_dir: Path) -> Path:
    reports = sorted(cache_dir.glob("report_*.json"), key=lambda p: p.stat().st_mtime)
    if not reports:
        raise SystemExit(f"no report_*.json found in {cache_dir}")
    return reports[-1]


def enrich_from_llm_section(flags: list[dict], report: dict) -> list[dict]:
    """
    Older reports (pre-audit) don't embed the summary inside each flag.
    Back-fill project/summary from report["llm_summary"]["*"]["per_project"].
    """
    by_url: dict[str, dict] = {}
    for section in ("labeled", "aux"):
        per_project = report.get("llm_summary", {}).get(section, {}).get("per_project") or []
        for c in per_project:
            if c.get("url"):
                by_url[c["url"]] = c
    enriched = []
    for f in flags:
        f = dict(f)
        c = by_url.get(f.get("url"))
        if c:
            f.setdefault("project", c.get("project"))
            f.setdefault("summary", c.get("summary"))
        enriched.append(f)
    return enriched


def render(report: dict, src_path: Path) -> str:
    flags = enrich_from_llm_section(report.get("flags") or [], report)
    if not flags:
        return (
            "# LLM Summary Audit Worksheet\n\n"
            "No flagged summaries in this report — no manual audit required.\n"
        )

    from collections import Counter
    by_issue = Counter(f.get("issue", "unknown") for f in flags)

    lines = [
        "# LLM Summary Audit Worksheet",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source report: `{src_path}`",
        "",
        "> Recommended by `docs/EVAL_DPGA_150_RESULTS.md` §8 rec #6: manually audit the",
        "> flagged summaries before trusting them for downstream claims.",
        "",
        "## Overview",
        "",
        f"- Total flags: **{len(flags)}**",
        *[f"- {ISSUE_LABELS.get(issue, issue)}: {count}" for issue, count in by_issue.items()],
        "",
        "## Flagged summaries",
        "",
    ]

    for i, f in enumerate(flags, 1):
        summary = (f.get("summary") or "").strip()
        lines += [
            f"### {i}. {f.get('project') or '(unknown project)'}",
            "",
            f"- **URL:** {f.get('url') or 'n/a'}",
            f"- **Issue:** {f.get('issue')}",
            f"- **Detail:** {f.get('detail') or 'n/a'}",
            "",
            "**Summary text:**",
            "",
            "> " + summary.replace("\n", "\n> ") if summary else "_(summary not recorded in report)_",
            "",
            "**Verdict:** `[ ] PASS (faithful)`   `[ ] FAIL (hallucinated/unsupported)`",
            "",
            "Notes: ",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Emit a manual-review worksheet for flagged LLM summaries.")
    ap.add_argument("report", nargs="?", default="", help="path to a report JSON (default: newest in .eval_cache)")
    ap.add_argument("--out", default="", help="write the worksheet to this Markdown file")
    ap.add_argument("--print", action="store_true", help="also print the worksheet to stdout")
    args = ap.parse_args()

    src = Path(args.report) if args.report else find_newest_report(CACHE_DEFAULT)
    if not src.exists():
        raise SystemExit(f"report not found: {src}")

    report = json.loads(src.read_text(encoding="utf-8-sig"))
    markdown = render(report, src)

    if args.out:
        out = Path(args.out)
        out.write_text(markdown, encoding="utf-8")
        print(f"[audit] worksheet -> {out}")
    else:
        print(markdown)

    if not args.print and not args.out:
        sys.stdout.flush()


if __name__ == "__main__":
    main()