

## new code :


"""
Nivara Women's Health AI System
================================
Module: Mood & Cycle Analysis Generator
LLM:    Azure OpenAI — GPT-4o mini

Key design: Python pre-processes raw data into enriched stats BEFORE
calling the LLM. The model receives labelled, computed context — not
raw numbers — which improves accuracy and reduces token usage.

Environment variables (.env):
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_CHAT_DEPLOYMENT
"""

import json
from typing import Optional
from statistics import mean, stdev
from collections import Counter
from openai import AzureOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")


# ─────────────────────────────────────────────
# SYSTEM PROMPT — Nivara AI Persona
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are Nivara's empathetic wellness AI, designed specifically for women's health.

You will receive a pre-processed wellness summary that already includes computed
statistics and labelled categories. Use these enriched stats directly — do not
re-compute or second-guess the labels provided.

ANALYSIS RULES
--------------
1. ALWAYS connect mood observations to the current cycle phase.
2. Reference actual numbers from the enriched_context (e.g. "your mood averaged 5.6").
3. Do NOT give generic advice — make it specific to the pre-processed data.
4. If data_quality_note says data is limited, acknowledge that upfront.
5. Use empathetic, warm language — like a knowledgeable friend, not a medical report.
6. Validate her feelings before offering suggestions.
7. Recommendations must be actionable for the next 1-3 days, not long-term plans.
8. Never present insights as medical diagnosis.
9. If journal entries suggest severe emotional distress, gently encourage speaking
   to a trusted person or professional.

CYCLE PHASE CONTEXT
-------------------
menstrual  -> low energy, low hormones; emotional sensitivity is natural and expected
follicular -> rising estrogen; mood typically lifts, motivation returns
ovulation  -> estrogen peak; often highest confidence and social energy
luteal     -> progesterone rise then drop; PMS window; mood may dip
pms_window -> irritability, anxiety, or sadness is hormonally driven — validate this

OUTPUT — strict JSON only. No markdown, no preamble, no code fences.

{
  "current_status": {
    "emotional_overview": "",
    "stability_insight": "",
    "stress_reflection": "",
    "cycle_mood_connection": "",
    "overall_interpretation": ""
  },
  "recommendations": {
    "emotional_support": [],
    "lifestyle_suggestions": [],
    "stress_management": [],
    "cycle_phase_tips": [],
    "gentle_advice": ""
  },
  "highlights": {
    "positive_pattern": "",
    "watch_out_for": "",
    "energy_note": ""
  }
}
"""


# ─────────────────────────────────────────────
# STEP 1 — Label helpers (mirrors employee code's get_strength)
# ─────────────────────────────────────────────

def label_mood_score(score: float) -> str:
    if score >= 7:   return "Positive"
    if score >= 4:   return "Mixed"
    return "Difficult"

def label_stability(index: float) -> str:
    if index > 70:  return "Emotionally stable"
    if index >= 40: return "Moderate fluctuations"
    return "Emotionally volatile"

def label_stress(pct: float) -> str:
    if pct < 20:  return "Low stress"
    if pct < 40:  return "Moderate stress"
    return "Elevated stress"

def label_variance(var: float) -> str:
    if var < 1:  return "Very steady"
    if var <= 2: return "Normal fluctuations"
    return "Notable mood swings"

def label_cycle_phase(phase: str, pms: bool) -> str:
    if pms:
        return "PMS window — hormonal mood sensitivity expected"
    labels = {
        "menstrual":  "Menstrual — low energy, emotional sensitivity natural",
        "follicular": "Follicular — energy rising, mood lifting",
        "ovulation":  "Ovulation — peak energy and confidence",
        "luteal":     "Luteal — progesterone phase, watch for mood dips",
    }
    return labels.get(phase, phase)


# ─────────────────────────────────────────────
# STEP 2 — Pre-processing (the key borrowed pattern)
# Computes enriched stats in Python so the LLM doesn't have to
# ─────────────────────────────────────────────

def preprocess_wellness_data(payload: dict) -> dict:
    """
    Enriches the raw aggregated payload with computed statistics
    and human-readable labels before sending to the LLM.

    This mirrors the employee survey code's approach of doing
    the heavy computation in Python, not in the prompt.
    """

    summary   = payload["mood_summary"]
    trend     = payload["mood_trend"]
    emotions  = payload["emotion_distribution"]
    stress    = payload["stress_analysis"]
    entries   = payload["recent_mood_entries"]["entries"]
    cycle     = payload["cycle_status"]

    # ── Mood score stats from raw entries ──
    scores = [e["mood_score"] for e in entries if e.get("mood_score") is not None]
    mood_std = round(stdev(scores), 2) if len(scores) > 1 else 0.0

    best_day_entry  = max(entries, key=lambda e: e["mood_score"]) if entries else {}
    worst_day_entry = min(entries, key=lambda e: e["mood_score"]) if entries else {}

    # ── Emotion breakdown ──
    emotion_counts = Counter(e["emotion_type"] for e in entries)
    dominant_emotion   = emotion_counts.most_common(1)[0][0] if emotion_counts else "unknown"
    least_seen_emotion = emotion_counts.most_common()[-1][0] if emotion_counts else "unknown"

    # ── Trend direction ──
    trend_points = trend.get("trend_data", [])
    if len(trend_points) >= 2:
        first_score = trend_points[0]["mood_score"]
        last_score  = trend_points[-1]["mood_score"]
        delta       = round(last_score - first_score, 2)
        trend_direction = (
            f"Improving (+{delta} from {trend_points[0]['date']} to {trend_points[-1]['date']})"
            if delta > 0 else
            f"Declining ({delta} from {trend_points[0]['date']} to {trend_points[-1]['date']})"
            if delta < 0 else
            "Stable across logged days"
        )
    else:
        trend_direction = "Only one date logged — trend not yet determinable"

    # ── Cycle context ──
    cycle_label = label_cycle_phase(
        cycle.get("cycle_phase", ""),
        cycle.get("pms_window", False)
    )

    fertile_note = (
        "Currently in fertile window"
        if cycle.get("is_fertile_today") else
        f"Fertile window starts {cycle['fertile_window']['fertile_window_start']}"
        if cycle.get("fertile_window") else
        "Fertility window not available"
    )

    # ── Data quality flag (mirrors employee code's total_drivers check) ──
    total_entries = summary.get("total_entries", 0)
    data_quality_note = (
        "Limited data — only {} entries logged. Insights are preliminary.".format(total_entries)
        if total_entries < 5 else
        "Sufficient data for meaningful analysis ({} entries).".format(total_entries)
    )

    # ── Build enriched context dict ──
    enriched = {
        "data_quality_note": data_quality_note,

        "mood_overview": {
            "average_mood":          summary["average_mood"],
            "mood_label":            label_mood_score(summary["average_mood"]),
            "mood_std_dev":          mood_std,
            "dominant_emotion":      dominant_emotion,
            "least_seen_emotion":    least_seen_emotion,
            "positive_ratio":        emotions["category_breakdown"]["positive"],
            "negative_ratio":        emotions["category_breakdown"]["negative"],
            "neutral_ratio":         emotions["category_breakdown"]["neutral"],
        },

        "stability_stress": {
            "stability_index":       summary["mood_stability_index"],
            "stability_label":       label_stability(summary["mood_stability_index"]),
            "stress_percentage":     summary["stress_percentage"],
            "stress_label":          label_stress(summary["stress_percentage"]),
            "weekly_variation":      summary["weekly_variation"],
            "variance_label":        label_variance(summary["emotional_variance"]),
        },

        "trend": {
            "direction":             trend_direction,
            "data_points":           trend["data_points"],
            "raw_trend":             trend_points,
        },

        "notable_entries": {
            "best_moment":  {
                "score":   best_day_entry.get("mood_score"),
                "emotion": best_day_entry.get("emotion_type"),
                "note":    best_day_entry.get("journal_text", ""),
                "date":    best_day_entry.get("entry_date"),
            },
            "hardest_moment": {
                "score":   worst_day_entry.get("mood_score"),
                "emotion": worst_day_entry.get("emotion_type"),
                "note":    worst_day_entry.get("journal_text", ""),
                "date":    worst_day_entry.get("entry_date"),
            },
        },

        "cycle_context": {
            "phase":                 cycle.get("cycle_phase"),
            "cycle_day":             cycle.get("cycle_day"),
            "cycle_label":           cycle_label,
            "energy_level":          cycle.get("energy_level"),
            "hormone_status":        cycle.get("hormone_status"),
            "pms_window":            cycle.get("pms_window"),
            "fertile_note":          fertile_note,
            "days_until_next_period": cycle.get("days_until_next_period"),
        },
    }

    return enriched


# ─────────────────────────────────────────────
# STEP 3 — Build user prompt from enriched context
# ─────────────────────────────────────────────

BASE_USER_PROMPT = {
    "task": "Analyze the enriched wellness context and return a JSON analysis.",
    "instruction": (
        "The enriched_context contains pre-computed statistics and labels. "
        "Use them directly. Connect mood patterns to the cycle phase. "
        "Be warm, specific, and genuinely helpful."
    ),
    "analysis_tasks": [
        "Explain what the mood label and average score mean emotionally",
        "Interpret the stability label in human terms",
        "Connect stress level to her current experience",
        "Tie mood trend direction to cycle phase",
        "Surface the best and hardest moment from notable_entries",
        "Give cycle-specific tips for the next 1-3 days",
        "End with a single piece of gentle, personalised advice",
    ],
    # enriched_context is merged in at call time
}


# ─────────────────────────────────────────────
# STEP 4 — LLM call
# ─────────────────────────────────────────────

def generate_nivara_analysis(enriched_context: dict) -> dict:
    """
    Sends the pre-processed enriched context to GPT-4o mini
    and returns the structured analysis JSON.
    """

    user_prompt = {
        **BASE_USER_PROMPT,
        "enriched_context": enriched_context,
    }

    raw_output = ""

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            temperature=0.3,
            max_tokens=900,
            timeout=25,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": json.dumps(user_prompt)}
            ]
        )

        raw_output = response.choices[0].message.content.strip()
        return json.loads(raw_output)

    except json.JSONDecodeError:
        return {"error": "Invalid JSON from model", "raw_output": raw_output}
    except Exception as e:
        return {"error": "Azure OpenAI call failed", "details": str(e)}


# ─────────────────────────────────────────────
# STEP 5 — Public API wrapper
# ─────────────────────────────────────────────

def validate_payload(payload: dict) -> Optional[str]:
    """Returns an error message string if validation fails, else None."""

    required_top = [
        "mood_summary", "mood_trend", "emotion_distribution",
        "stress_analysis", "recent_mood_entries", "cycle_status"
    ]
    missing = [k for k in required_top if k not in payload]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"

    mood_summary = payload.get("mood_summary", {})
    cycle_status = payload.get("cycle_status", {})
    mood_trend   = payload.get("mood_trend", {})

    if mood_summary.get("average_mood") is None:
        return "Invalid payload: 'average_mood' missing in mood_summary"
    if mood_summary.get("total_entries") is None:
        return "Invalid payload: 'total_entries' missing in mood_summary"
    if cycle_status.get("cycle_phase") is None:
        return "Invalid payload: 'cycle_phase' missing in cycle_status"
    if mood_trend.get("trend_data") is None:
        return "Invalid payload: 'trend_data' missing in mood_trend"

    return None


def analyze_user_wellness(payload: dict) -> dict:
    """
    Main entry point for Nivara's mood analysis feature.

    Flow: validate → preprocess → LLM call → return

    Returns
    -------
    dict
        { "status": "success", "analysis": { ... } }
        { "status": "error",   "message": "...", "details": "..." }
    """

    error = validate_payload(payload)
    if error:
        return {"status": "error", "message": error}

    enriched = preprocess_wellness_data(payload)
    result   = generate_nivara_analysis(enriched)

    if "error" in result:
        return {
            "status":  "error",
            "message": result["error"],
            "details": result.get("details") or result.get("raw_output", "")
        }

    return {"status": "success", "analysis": result}


# ─────────────────────────────────────────────
# Lifestyle Intelligence + Health Report (single LLM call)
# ─────────────────────────────────────────────

LIFESTYLE_REPORT_BUNDLE_SYSTEM_PROMPT = """
You are Nivara's empathetic women's wellness AI. You receive pre-computed wellness stats
(enriched_wellness) and compact report facts (compiled_report_facts). Use them as ground
truth — do not invent numbers or phases not present.

Rules: warm, non-clinical tone; actionable for 1–7 days; never diagnose; encourage
professional help if distress is severe.

OUTPUT — strict JSON only. No markdown, preamble, or code fences.

{
  "lifestyle": {
    "yoga_suggestions": {
      "summary": "",
      "suggestions": [
        {"title": "", "description": "", "duration_min": 15}
      ]
    },
    "diet_adjustments": {
      "phase_note": "",
      "adjustments": [
        {"category": "", "tip": ""}
      ]
    },
    "sleep_guidance": {
      "target_hours": "",
      "tips": [""],
      "summary": ""
    },
    "emotional_regulation_tips": {
      "context_note": "",
      "tips": [""]
    }
  },
  "report_narrative": {
    "professional_summary": "",
    "insight_bullets": [""],
    "highlights": "",
    "supportive_note": ""
  }
}

Use 3–5 yoga suggestions, 3–4 diet adjustments, 3–5 sleep tips, 3–5 emotional tips.
insight_bullets: 4–6 short strings. professional_summary: 2–4 sentences.
"""


def _validate_lifestyle_bundle(lifestyle: dict) -> bool:
    if not isinstance(lifestyle, dict):
        return False
    y = lifestyle.get("yoga_suggestions") or {}
    d = lifestyle.get("diet_adjustments") or {}
    s = lifestyle.get("sleep_guidance") or {}
    e = lifestyle.get("emotional_regulation_tips") or {}
    if not isinstance(y.get("suggestions"), list) or not isinstance(y.get("summary"), str):
        return False
    if not isinstance(d.get("adjustments"), list) or not isinstance(d.get("phase_note"), str):
        return False
    if not isinstance(s.get("tips"), list) or not isinstance(s.get("summary"), str):
        return False
    if not isinstance(e.get("tips"), list) or not isinstance(e.get("context_note"), str):
        return False
    return True


def _validate_report_narrative(rn: dict) -> bool:
    if not isinstance(rn, dict):
        return False
    ps = rn.get("professional_summary")
    if not isinstance(ps, str) or not ps.strip():
        return False
    ib = rn.get("insight_bullets")
    if ib is not None and not isinstance(ib, list):
        return False
    return True


def generate_lifestyle_report_bundle_llm(
    enriched_context: dict, report_context: dict
) -> dict:
    user_prompt = {
        "task": (
            "Produce personalized lifestyle recommendations and a concise health-report "
            "narrative from the given context."
        ),
        "enriched_wellness": enriched_context,
        "compiled_report_facts": report_context or {},
    }
    raw_output = ""
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            temperature=0.35,
            max_tokens=1000,
            timeout=45,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": LIFESTYLE_REPORT_BUNDLE_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
        )
        raw_output = response.choices[0].message.content.strip()
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from model", "raw_output": raw_output}
    except Exception as e:
        return {"error": "Azure OpenAI call failed", "details": str(e)}


def analyze_lifestyle_report_bundle(
    payload: dict, report_context: Optional[dict] = None
) -> dict:
    """
    Single LLM call → lifestyle card shape (matches lifestyle_ai) + report narrative text.
    """
    error = validate_payload(payload)
    if error:
        return {"status": "error", "message": error}

    enriched = preprocess_wellness_data(payload)
    result = generate_lifestyle_report_bundle_llm(enriched, report_context or {})

    if "error" in result:
        return {
            "status": "error",
            "message": result["error"],
            "details": result.get("details") or result.get("raw_output", ""),
        }

    lifestyle = result.get("lifestyle")
    rn = result.get("report_narrative")

    if not _validate_lifestyle_bundle(lifestyle):
        return {
            "status": "error",
            "message": "Invalid lifestyle shape from model",
            "details": json.dumps(result)[:2000],
        }

    report_ai = None
    if rn and _validate_report_narrative(rn):
        report_ai = rn

    return {
        "status": "success",
        "lifestyle": lifestyle,
        "report_ai": report_ai,
    }


# ─────────────────────────────────────────────
# Run directly to test
# python nivara_mood_analysis.py
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    sample_payload = {
        "mood_summary": {
            "period_days": 30, "total_entries": 7, "average_mood": 5.6,
            "dominant_emotion": "hopeful", "stress_level": "Low",
            "stress_percentage": 14.3, "weekly_variation": 1.8,
            "mood_stability_index": 60, "emotional_variance": 1.8
        },
        "mood_trend": {
            "period_days": 30, "data_points": 2,
            "trend_data": [
                {"date": "2026-03-02", "mood_score": 4.7, "entries": 3},
                {"date": "2026-03-03", "mood_score": 6.2, "entries": 4}
            ]
        },
        "emotion_distribution": {
            "period_days": 30, "total_entries": 7,
            "distribution": [
                {"emotion": "hopeful",  "count": 2, "percentage": 28.6},
                {"emotion": "stressed", "count": 1, "percentage": 14.3},
                {"emotion": "neutral",  "count": 1, "percentage": 14.3},
                {"emotion": "excited",  "count": 1, "percentage": 14.3},
                {"emotion": "content",  "count": 1, "percentage": 14.3},
                {"emotion": "calm",     "count": 1, "percentage": 14.3}
            ],
            "category_breakdown": {"positive": 71.4, "negative": 14.3, "neutral": 14.3}
        },
        "stress_analysis": {
            "period_days": 30,
            "weekly_stress_data": [{"week_start": "2026-03-02", "total_entries": 7,
                "stress_emotion_count": 1, "stress_percentage": 14.3,
                "journal_stress_score": 0, "avg_mood": 5.6}],
            "top_stress_keywords": []
        },
        "recent_mood_entries": {
            "period_days": 30, "count": 9,
            "entries": [
                {"mood_score": 7, "emotion_type": "calm",    "journal_text": "Feeling Calm",   "entry_date": "2026-03-03"},
                {"mood_score": 7, "emotion_type": "calm",    "journal_text": "Feeling Calm",   "entry_date": "2026-03-03"},
                {"mood_score": 3, "emotion_type": "neutral", "journal_text": "Neutral",         "entry_date": "2026-03-03"},
                {"mood_score": 9, "emotion_type": "hopeful", "journal_text": "Very Excited",    "entry_date": "2026-03-03"},
                {"mood_score": 6, "emotion_type": "excited", "journal_text": "Feeling excited", "entry_date": "2026-03-03"},
                {"mood_score": 7, "emotion_type": "calm",    "journal_text": "",                "entry_date": "2026-03-03"},
                {"mood_score": 5, "emotion_type": "content", "journal_text": "",                "entry_date": "2026-03-02"},
                {"mood_score": 5, "emotion_type": "hopeful", "journal_text": "",                "entry_date": "2026-03-02"},
                {"mood_score": 4, "emotion_type": "stressed","journal_text": "",                "entry_date": "2026-03-02"}
            ]
        },
        "cycle_status": {
            "cycle_day": 4, "cycle_phase": "menstrual",
            "phase_display": "Menstrual Phase",
            "phase_description": "Your body is shedding the uterine lining.",
            "energy_level": "low", "hormone_status": "Low estrogen and progesterone",
            "days_until_next_period": 25, "predicted_next_period": "2026-03-29",
            "pms_window": False,
            "fertile_window": {
                "fertile_window_start": "2026-03-09", "fertile_window_end": "2026-03-15",
                "ovulation_date": "2026-03-14", "ovulation_day_in_cycle": 14
            },
            "is_fertile_today": False
        }
    }

    if len(sys.argv) > 1 and sys.argv[1] == "bundle":
        report_ctx = {
            "average_mood": 5.6,
            "stress_level": "Low",
            "cycle_phase": "menstrual",
            "trend": "Stable",
            "total_entries": 7,
        }
        print("Nivara — lifestyle + report bundle (max_tokens=1000)...\n")
        out = analyze_lifestyle_report_bundle(sample_payload, report_context=report_ctx)
        print(json.dumps(out, indent=2))
    else:
        print("Nivara — Generating wellness analysis...\n")
        output = analyze_user_wellness(sample_payload)
        print(json.dumps(output, indent=2))
        print(
            '\nTip: run `python nivara_app/ai_engine/analysis.py bundle` '
            "to test lifestyle + report in one call."
        )