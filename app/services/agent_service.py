
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from app.services.resume_service import get_llm
from app.services import store


def _make_tools():
    """Tools are built per-invocation so closures can't leak state across
    concurrent requests; the store functions themselves are the shared state."""

    @tool
    def get_full_resume_text(candidate_name: str) -> str:
        """Fetch the candidate's complete extracted resume text (not the
        truncated summary used for ranking). Use this when the ranking's
        stated reasoning seems thin, contradictory, or you need to verify a
        specific claim (e.g. a skill or years of experience) against the
        source document."""
        cid = store.get_candidate_id_by_name(candidate_name)
        if not cid:
            return f"No stored candidate found matching '{candidate_name}'."
        text = store.get_full_resume_text(cid)
        if not text:
            return "No full resume text was stored for this candidate."
        return text[:8000]

    @tool
    def flag_for_manual_review(candidate_name: str, reason: str) -> str:
        """Flag a candidate's ranking for manual human review instead of
        letting it pass automatically. Use this when the automated score,
        recommendation, and underlying resume data don't line up — e.g. a
        'Strong Hire' recommendation despite missing required skills, or an
        experience_level that doesn't match the stated years of experience.
        Do not use this for candidates that look consistent; only flag real
        discrepancies."""
        cid = store.get_candidate_id_by_name(candidate_name) or "unknown"
        store.add_review_flag(cid, candidate_name, reason)
        return f"Flagged {candidate_name} for manual review: {reason}"

    return [get_full_resume_text, flag_for_manual_review]


AGENT_SYSTEM_PROMPT = """You are a hiring QA agent. You are given one candidate's
automated ranking result (score, matched/missing skills, recommendation, and the
ranking model's reasoning). Your job is to sanity-check that single result.

Check for internal inconsistency, such as:
- A "Strong Hire" or "Hire" recommendation despite several missing required skills.
- An overall_score that doesn't roughly match skill_match_score and experience_score.
- A recommendation of "Reject" for a candidate with a very strong skill match and
  sufficient experience (possible false negative).

If the reasoning given seems too thin to judge, call get_full_resume_text to check
the claim against the source resume before deciding.

If you find a real inconsistency, call flag_for_manual_review with a specific,
concrete reason. If the result looks internally consistent, do NOT call any tool —
just reply with a one-line confirmation that no action was needed.

Be conservative: only flag genuine discrepancies, not stylistic nitpicks."""


async def qa_review_ranking(candidate_score: dict) -> str:
    """Run the QA agent on a single candidate's ranking result.

    Returns the agent's final text response (its own summary of what it did).
    Any flag it decided to raise has already been written to the review queue
    as a side effect of the tool call, independent of what this function returns.
    """
    llm = get_llm()
    agent = create_react_agent(llm, tools=_make_tools())

    user_message = (
        f"Ranking result to review:\n"
        f"candidate_name: {candidate_score.get('candidate_name')}\n"
        f"overall_score: {candidate_score.get('overall_score')}\n"
        f"skill_match_score: {candidate_score.get('skill_match_score')}\n"
        f"experience_score: {candidate_score.get('experience_score')}\n"
        f"matched_skills: {candidate_score.get('matched_skills')}\n"
        f"missing_skills: {candidate_score.get('missing_skills')}\n"
        f"bonus_skills: {candidate_score.get('bonus_skills')}\n"
        f"recommendation: {candidate_score.get('recommendation')}\n"
        f"reasoning: {candidate_score.get('reasoning')}\n"
    )

    result = await agent.ainvoke({
        "messages": [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
    })

    final_message = result["messages"][-1]
    return final_message.content if hasattr(final_message, "content") else str(final_message)


async def qa_review_all(candidate_scores: list[dict]) -> dict[str, str]:
    """Run the QA agent over every ranked candidate. Returns a map of
    candidate_name -> agent's summary text, for surfacing in the API response."""
    results = {}
    for score in candidate_scores:
        name = score.get("candidate_name", "unknown")
        try:
            results[name] = await qa_review_ranking(score)
        except Exception as e:
            # A QA-layer failure should never take down the whole ranking
            # response — log it as inconclusive rather than raising.
            results[name] = f"QA review failed to complete: {e}"
    return results
