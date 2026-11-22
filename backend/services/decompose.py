"""Task decomposition: free built-in rules by default, optional OpenAI-compatible LLM when LLM_API_KEY is set.

Both paths return the same shape, validated the same way:
    {"subtasks": [{"title", "type", "description", "depends_on": [index...], "estimate_low", "estimate_high",
                   "provider_id", "tool_reason"}], "method": "rules" | "ai", "category": str, "notice": str | None,
     "usage": {...} | None}
"""
import json
import logging
import re
import httpx
from core.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from services.validation import field_error

log = logging.getLogger("decompose")

TYPES = ("planning", "research", "code", "writing", "design", "analysis", "review")
MAX_SUBTASKS = 12

# Which tool suits which kind of work. Editable here; every recommendation carries its reason.
TOOL_RULES = {
    "planning": ("chatgpt", "General reasoning for scoping and planning"),
    "research": ("perplexity", "Search with cited sources"),
    "code": ("copilot", "In-editor code generation and tests"),
    "writing": ("claude", "Long-form drafting and editing"),
    "design": ("chatgpt", "Image generation and visual ideation"),
    "analysis": ("gemini", "Working with data and long documents"),
    "review": ("claude", "Long-context review and critique"),
}

# (title template, type, depends_on indexes, base low credits, base high credits)
TEMPLATES = {
    "software": [
        ("Clarify requirements and acceptance criteria", "planning", [], 40, 90),
        ("Design the technical approach", "planning", [0], 80, 160),
        ("Implement the core changes", "code", [1], 250, 500),
        ("Write automated tests", "code", [1], 120, 260),
        ("Review, fix and verify the changes", "review", [2, 3], 90, 180),
        ("Document and hand off", "writing", [4], 50, 110),
    ],
    "research": [
        ("Define the research questions and scope", "planning", [], 40, 80),
        ("Gather and summarise sources", "research", [0], 150, 300),
        ("Analyse data and comparisons", "analysis", [0], 150, 320),
        ("Synthesise findings", "writing", [1, 2], 120, 240),
        ("Review conclusions and prepare the presentation", "review", [3], 60, 130),
    ],
    "content": [
        ("Outline the structure and key messages", "planning", [], 40, 80),
        ("Research supporting facts", "research", [0], 100, 200),
        ("Write the first draft", "writing", [0, 1], 200, 380),
        ("Create visuals", "design", [0], 100, 220),
        ("Edit and proofread", "review", [2], 70, 140),
        ("Final review and publish", "review", [3, 4], 40, 90),
    ],
    "design": [
        ("Gather requirements and constraints", "planning", [], 40, 90),
        ("Collect references and user insights", "research", [0], 100, 200),
        ("Sketch wireframes", "design", [1], 120, 240),
        ("Produce high-fidelity mockups", "design", [2], 200, 400),
        ("Run a usability review", "review", [3], 80, 160),
        ("Prepare handoff specs", "writing", [4], 60, 120),
    ],
    "data": [
        ("Define the metrics and questions", "planning", [], 40, 90),
        ("Collect and clean the data", "analysis", [0], 150, 300),
        ("Explore the data", "analysis", [1], 150, 280),
        ("Build the model or dashboard", "code", [2], 220, 450),
        ("Validate the results", "review", [3], 90, 180),
        ("Write up the findings", "writing", [4], 80, 160),
    ],
    "launch": [
        ("Define goals and target audience", "planning", [], 40, 90),
        ("Research channels and competitors", "research", [0], 120, 240),
        ("Write the launch content", "writing", [0], 150, 300),
        ("Design the launch assets", "design", [0], 150, 300),
        ("Set up the campaign", "planning", [2, 3], 80, 160),
        ("Final review and launch", "review", [1, 4], 50, 110),
    ],
    "general": [
        ("Clarify scope and success criteria", "planning", [], 40, 90),
        ("Research what's needed", "research", [0], 100, 220),
        ("Do the main work", "writing", [1], 200, 400),
        ("Review the result", "review", [2], 70, 150),
        ("Wrap up and share", "writing", [3], 40, 90),
    ],
}

KEYWORDS = {
    "software": ("build", "implement", "api", "bug", "refactor", "migrat", "feature", "code", "deploy", "backend",
                 "frontend", "endpoint", "integration", "app", "service", "fix", "release", "test"),
    "data": ("data", "dashboard", "metric", "dataset", "pipeline", "etl", "model", "forecast", "analytics", "sql", "kpi"),
    "research": ("research", "analys", "compare", "study", "market", "survey", "investigat", "evaluate", "benchmark"),
    "design": ("design", "ui", "ux", "mockup", "wireframe", "prototype", "figma", "screen", "redesign"),
    "content": ("write", "blog", "article", "documentation", "docs", "copy", "newsletter", "report", "proposal",
                "presentation", "deck", "whitepaper", "guide"),
    "launch": ("launch", "campaign", "marketing", "go-to-market", "gtm", "social", "seo", "promotion", "event"),
}

PRIORITY_FACTOR = {"low": 0.9, "medium": 1.0, "high": 1.1, "urgent": 1.2}


def detect_category(text: str) -> str:
    t = text.lower()
    scores = {cat: sum(1 for k in words if re.search(rf"\b{re.escape(k)}", t)) for cat, words in KEYWORDS.items()}
    best = max(scores, key=lambda c: scores[c])
    return best if scores[best] > 0 else "general"


def _subject(title: str) -> str:
    s = re.sub(r"\s+", " ", title.strip()).rstrip(".")
    s = s[0].lower() + s[1:] if len(s) > 1 and not s[:2].isupper() else s
    return s[:70] + ("…" if len(s) > 70 else "")


def _round10(n: float) -> int:
    return max(10, int(round(n / 10.0)) * 10)


def rules_decompose(title: str, description: str, priority: str) -> dict:
    category = detect_category(f"{title} {description}")
    size = 1.0 + min(len(description.strip()) / 600.0, 1.0)  # longer briefs → bigger estimates, up to 2x
    factor = size * PRIORITY_FACTOR.get(priority, 1.0)
    subject = _subject(title)
    subtasks = []
    for tpl, typ, deps, low, high in TEMPLATES[category]:
        provider_id, reason = TOOL_RULES[typ]
        subtasks.append({"title": tpl, "type": typ, "description": f"Part of: {subject}", "depends_on": list(deps),
                         "estimate_low": _round10(low * factor), "estimate_high": _round10(high * factor),
                         "provider_id": provider_id, "tool_reason": reason})
    return {"subtasks": subtasks, "method": "rules", "category": category, "usage": None,
            "notice": f"Built-in {category} template. Estimates are rough ranges in credits; edit anything before saving."}


SYSTEM_PROMPT = (
    "You break a work goal into 3 to 10 concrete sub-tasks for a small team that uses AI tools. "
    "Reply with JSON only: {\"subtasks\": [{\"title\": str, \"type\": one of " + ", ".join(TYPES) +
    ", \"description\": str (one sentence), \"depends_on\": [indexes of earlier sub-tasks], "
    "\"estimate_low\": int credits, \"estimate_high\": int credits}]}. Credits: 1 credit is roughly one short AI request; "
    "typical sub-tasks need 40 to 500 credits. Dependencies may only point to earlier indexes. "
    "Sub-tasks without dependencies between them can run in parallel."
)


async def llm_decompose(title: str, description: str, priority: str) -> dict:
    payload = {"model": LLM_MODEL, "temperature": 0.2, "response_format": {"type": "json_object"},
               "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": f"Goal: {title}\nPriority: {priority}\nDetails: {description or '(none)'}"}]}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{LLM_BASE_URL}/chat/completions", json=payload,
                              headers={"Authorization": f"Bearer {LLM_API_KEY}"})
    r.raise_for_status()
    body = r.json()
    raw = json.loads(body["choices"][0]["message"]["content"])
    subtasks = []
    for item in (raw.get("subtasks") or [])[:MAX_SUBTASKS]:
        typ = item.get("type") if item.get("type") in TYPES else "planning"
        provider_id, reason = TOOL_RULES[typ]
        low = int(item.get("estimate_low") or 50)
        high = max(low, int(item.get("estimate_high") or low * 2))
        subtasks.append({"title": str(item.get("title") or "").strip()[:160], "type": typ,
                         "description": str(item.get("description") or "").strip()[:500],
                         "depends_on": [d for d in item.get("depends_on") or [] if isinstance(d, int)],
                         "estimate_low": _round10(low), "estimate_high": _round10(high),
                         "provider_id": provider_id, "tool_reason": reason})
    validate_graph(subtasks)
    usage = body.get("usage") or {}
    return {"subtasks": subtasks, "method": "ai", "category": "ai", "usage": {
        "model": LLM_MODEL, "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")},
        "notice": "Generated by your own LLM key. Only the goal title, priority and details you typed were sent."}


def validate_graph(subtasks: list[dict]) -> list[int]:
    """Checks titles, dependency references and cycles. Returns the wave (0-based level) of each sub-task."""
    if not subtasks:
        raise field_error(422, {"subtasks": "Add at least one sub-task"})
    if len(subtasks) > MAX_SUBTASKS:
        raise field_error(422, {"subtasks": f"Use at most {MAX_SUBTASKS} sub-tasks"})
    n = len(subtasks)
    for i, s in enumerate(subtasks):
        if not (s.get("title") or "").strip():
            raise field_error(422, {"subtasks": f"Sub-task {i + 1} needs a title"})
        deps = s.get("depends_on") or []
        if any((not isinstance(d, int)) or d < 0 or d >= n or d == i for d in deps):
            raise field_error(422, {"subtasks": f"Sub-task {i + 1} has an invalid dependency"})
    waves = [-1] * n
    state = [0] * n  # 0 new, 1 visiting, 2 done

    def visit(i: int) -> int:
        if state[i] == 1:
            raise field_error(422, {"subtasks": "Dependencies form a loop. Remove one so the work can start somewhere."})
        if state[i] == 2:
            return waves[i]
        state[i] = 1
        waves[i] = 1 + max((visit(d) for d in subtasks[i].get("depends_on") or []), default=-1)
        state[i] = 2
        return waves[i]

    for i in range(n):
        visit(i)
    return waves


async def decompose(title: str, description: str, priority: str) -> dict:
    title = (title or "").strip()
    if not title:
        raise field_error(422, {"title": "Describe the goal first"})
    if LLM_API_KEY:
        try:
            return await llm_decompose(title, description or "", priority)
        except Exception as exc:  # any LLM/network/format failure falls back to the free rules
            log.warning("LLM decomposition failed, using rules: %s", exc)
            out = rules_decompose(title, description or "", priority)
            out["notice"] = "Your LLM didn't respond as expected, so the built-in rules were used. " + out["notice"]
            return out
    return rules_decompose(title, description or "", priority)
