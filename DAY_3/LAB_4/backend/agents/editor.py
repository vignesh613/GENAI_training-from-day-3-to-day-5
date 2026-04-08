import re
from langchain_openai import ChatOpenAI
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_REVISIONS = 2

_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    return _llm


async def editor_node(state: dict) -> dict:
    topic = state["topic"]
    draft_report = state["draft_report"]
    revision_count = state.get("revision_count", 0)

    logger.info(f"[EDITOR] Reviewing draft (revision {revision_count})...")

    llm = get_llm()

    # ── Step 1: Edit and improve the report ──────────────────────────────────
    edit_prompt = f"""You are a senior editor. Improve this report for clarity, flow, accuracy, and professional tone.

Topic: {topic}

Draft:
{draft_report}

Tasks:
- Fix grammatical issues and awkward phrasing
- Improve transitions between sections
- Strengthen vague statements with specificity
- Ensure all sections are well-developed and balanced
- Tighten the executive summary and conclusion

Return ONLY the improved full report in Markdown. Do not add commentary or meta-text."""

    edit_response = llm.invoke(edit_prompt)
    edited_report = edit_response.content.strip()

    # ── Step 2: Score the quality ─────────────────────────────────────────────
    score_prompt = f"""Rate the quality of this report on a scale of 1–10.

Scoring criteria:
- 8–10: Comprehensive, well-structured, publication-ready
- 5–7: Good coverage but minor gaps or clarity issues
- 1–4: Significant deficiencies — needs major revision

Report excerpt (first 800 chars):
{edited_report[:800]}

Reply with ONLY a single integer (1–10), nothing else."""

    try:
        score_response = llm.invoke(score_prompt)
        quality_score = int(re.search(r"\d+", score_response.content).group())
        quality_score = max(1, min(10, quality_score))
    except Exception as e:
        logger.warning(f"[EDITOR] Score parse error: {e}. Defaulting to 7.")
        quality_score = 7

    logger.info(f"[EDITOR] Quality score: {quality_score}/10")

    return {
        **state,
        "final_report": edited_report,
        "quality_score": quality_score,
        "status": "edited",
    }


def should_revise(state: dict) -> str:
    quality_score = state.get("quality_score", 7)
    revision_count = state.get("revision_count", 0)

    if quality_score < 5 and revision_count < MAX_REVISIONS:
        logger.info(
            f"[EDITOR] Score {quality_score}/10 below threshold — requesting revision #{revision_count + 1}"
        )
        return "revise"

    logger.info(f"[EDITOR] Report accepted with score {quality_score}/10")
    return "complete"
