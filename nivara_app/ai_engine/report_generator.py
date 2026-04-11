def generate_health_report(analysis, cycles):
    """Legacy: used by GET report/generate/. Kept for backward compatibility."""
    return "This is a dummy health report. Detailed analytics will be added later."


# =========================================================
# 🌸 PHASE 6: AI HEALTH REPORT GENERATOR
# Compiles: mood stats, cycle patterns, stress markers, lifestyle consistency
# LLM-ready: generates professional report, risk flags, suggestions, summary insights
# =========================================================

def generate_health_summary_report(compiled_data):
    """
    Generates a professional structured health summary report from compiled backend data.
    Designed for LLM enhancement: same inputs can later be sent to an LLM for richer narrative.
    
    Args:
        compiled_data: dict with
            - mood_statistics: dict (average_mood, dominant_emotion, trend, total_entries, etc.)
            - cycle_patterns: dict or None (cycle_phase, regularity, irregularity_analysis, etc.)
            - stress_markers: dict (stress_level, stress_percentage, markers list)
            - lifestyle_consistency: dict (sleep_consistency, mood_logging_consistency, etc.)
    
    Returns:
        dict with report_sections, risk_flags, suggestions, summary_insights, professional_summary
    """
    mood = (compiled_data.get("mood_statistics") or {})
    cycle = (compiled_data.get("cycle_patterns") or {}) if compiled_data.get("cycle_patterns") else {}
    stress = (compiled_data.get("stress_markers") or {})
    lifestyle = (compiled_data.get("lifestyle_consistency") or {})
    
    # --- Risk flags (rule-based; LLM can add nuance later) ---
    risk_flags = _compute_risk_flags(mood, cycle, stress, lifestyle)
    
    # --- Suggestions (actionable next steps) ---
    suggestions = _compute_suggestions(mood, cycle, stress, lifestyle, risk_flags)
    
    # --- Summary insights (narrative bullets) ---
    summary_insights = _compute_summary_insights(mood, cycle, stress, lifestyle)
    
    # --- Professional structured report sections ---
    report_sections = _build_report_sections(mood, cycle, stress, lifestyle)
    
    # --- Short professional summary paragraph ---
    professional_summary = _build_professional_summary(
        mood, cycle, stress, summary_insights, risk_flags
    )
    
    return {
        "report_sections": report_sections,
        "risk_flags": risk_flags,
        "suggestions": suggestions,
        "summary_insights": summary_insights,
        "professional_summary": professional_summary,
        "generated_at": None,  # Set by view with current timestamp
    }


def _compute_risk_flags(mood, cycle, stress, lifestyle):
    """Derive risk flags from compiled data."""
    flags = []
    
    stress_level = (stress.get("stress_level") or "").strip()
    if stress_level in ("High", "Very High"):
        flags.append({
            "id": "stress_elevated",
            "severity": "moderate" if stress_level == "High" else "high",
            "title": "Elevated stress",
            "description": "Stress markers are elevated. Consider stress-reduction practices and support.",
            "category": "mental_health",
        })
    
    avg_mood = mood.get("average_mood") or 5
    if avg_mood is not None and avg_mood < 4:
        flags.append({
            "id": "low_mood_pattern",
            "severity": "moderate",
            "title": "Low mood pattern",
            "description": "Average mood has been low. Gentle self-care and professional support can help.",
            "category": "mood",
        })
    
    trend = (mood.get("trend") or "Stable").lower()
    if trend == "declining":
        flags.append({
            "id": "mood_trend_declining",
            "severity": "low",
            "title": "Mood trend declining",
            "description": "Mood trend over the period is declining. Worth monitoring and reinforcing healthy habits.",
            "category": "mood",
        })
    
    irregularity = cycle.get("irregularity_analysis") or {}
    if irregularity.get("needs_attention"):
        flags.append({
            "id": "cycle_irregularity",
            "severity": "low",
            "title": "Cycle irregularity noted",
            "description": irregularity.get("regularity_message", "Cycle patterns show variation. Tracking helps; consult if concerned."),
            "category": "cycle",
        })
    
    consistency = lifestyle.get("mood_logging_consistency") or "unknown"
    if consistency == "low" and (mood.get("total_entries") or 0) < 5:
        flags.append({
            "id": "limited_data",
            "severity": "info",
            "title": "Limited tracking data",
            "description": "More consistent mood and cycle logging will improve report accuracy.",
            "category": "data_quality",
        })
    
    return flags


def _compute_suggestions(mood, cycle, stress, lifestyle, risk_flags):
    """Generate actionable suggestions."""
    suggestions = []
    
    stress_level = (stress.get("stress_level") or "").strip()
    if stress_level in ("High", "Very High"):
        suggestions.append({
            "priority": "high",
            "area": "stress",
            "title": "Prioritize stress management",
            "action": "Add short breathing exercises or walks; consider boundaries and sleep routine.",
        })
    
    avg_mood = mood.get("average_mood") or 5
    if avg_mood is not None and avg_mood < 5:
        suggestions.append({
            "priority": "medium",
            "area": "mood",
            "title": "Support mood and energy",
            "action": "Focus on sleep, light movement, and one small positive activity daily.",
        })
    
    phase = (cycle.get("cycle_phase") or cycle.get("current_phase")) or ""
    if phase == "luteal" and cycle.get("pms_window"):
        suggestions.append({
            "priority": "medium",
            "area": "cycle",
            "title": "PMS window self-care",
            "action": "Gentle exercise, magnesium-rich foods, and consistent sleep can ease symptoms.",
        })
    
    suggestions.append({
        "priority": "general",
        "area": "habits",
        "title": "Keep tracking",
        "action": "Regular mood and cycle logging improves personalization of insights and reports.",
    })
    
    return suggestions


def _compute_summary_insights(mood, cycle, stress, lifestyle):
    """Build summary insight bullets."""
    insights = []
    
    avg_mood = mood.get("average_mood")
    dominant_emotion = mood.get("dominant_emotion") or "your recorded mood"
    if avg_mood is not None:
        insights.append(f"Your average mood over the period is {avg_mood}/10, with {dominant_emotion} as the most common emotional tone.")
    
    stress_level = stress.get("stress_level") or "unknown"
    insights.append(f"Stress indicators suggest {stress_level.lower()} stress levels during this period.")
    
    if cycle and (cycle.get("cycle_phase") or cycle.get("phase_display")):
        phase_label = cycle.get("phase_display") or cycle.get("cycle_phase") or "current"
        insights.append(f"Your cycle phase is aligned with {phase_label}; recommendations are tailored to this phase.")
    
    irregularity = (cycle or {}).get("irregularity_analysis") or {}
    if irregularity.get("has_data") and not irregularity.get("needs_attention"):
        insights.append("Your cycle pattern appears regular; continued tracking helps maintain accuracy.")
    elif irregularity.get("needs_attention"):
        insights.append("Cycle variation was noted; tracking over more cycles will clarify patterns.")
    
    return insights


def _build_report_sections(mood, cycle, stress, lifestyle):
    """Professional report sections for UI display."""
    sections = []
    
    sections.append({
        "id": "mood_statistics",
        "title": "Mood statistics",
        "content": {
            "average_mood": mood.get("average_mood"),
            "dominant_emotion": mood.get("dominant_emotion"),
            "trend": mood.get("trend"),
            "total_entries": mood.get("total_entries"),
            "period_days": mood.get("period_days"),
            "mood_stability_index": mood.get("mood_stability_index"),
        },
        "summary": f"Average mood {mood.get('average_mood', '—')}/10, trend: {mood.get('trend', '—')}, dominant emotion: {mood.get('dominant_emotion', '—')}.",
    })
    
    sections.append({
        "id": "stress_markers",
        "title": "Stress markers",
        "content": {
            "stress_level": stress.get("stress_level"),
            "stress_percentage": stress.get("stress_percentage"),
            "markers": stress.get("markers", []),
        },
        "summary": f"Stress level: {stress.get('stress_level', '—')}. {stress.get('summary_note', '')}",
    })
    
    if cycle:
        sections.append({
            "id": "cycle_patterns",
            "title": "Cycle patterns",
            "content": {
                "cycle_phase": cycle.get("cycle_phase") or cycle.get("phase_display"),
                "cycle_day": cycle.get("cycle_day"),
                "regularity": cycle.get("regularity_message") or cycle.get("regularity_status"),
                "irregularity_analysis": cycle.get("irregularity_analysis"),
                "pms_window": cycle.get("pms_window"),
            },
            "summary": f"Phase: {cycle.get('phase_display') or cycle.get('cycle_phase') or '—'}; {cycle.get('regularity_message', '')}",
        })
    
    sections.append({
        "id": "lifestyle_consistency",
        "title": "Lifestyle consistency",
        "content": {
            "mood_logging_consistency": lifestyle.get("mood_logging_consistency"),
            "sleep_note": lifestyle.get("sleep_note"),
            "profile_complete": lifestyle.get("profile_complete"),
        },
        "summary": lifestyle.get("consistency_summary", "Tracking consistency supports better insights."),
    })
    
    return sections


def _build_professional_summary(mood, cycle, stress, summary_insights, risk_flags):
    """One short paragraph professional summary."""
    parts = []
    parts.append("This health summary is based on your logged mood, stress indicators, and cycle data.")
    if summary_insights:
        parts.append(" ".join(summary_insights[:2]))
    if risk_flags:
        high = [f for f in risk_flags if f.get("severity") in ("high", "moderate")]
        if high:
            parts.append("Some areas may benefit from extra attention or professional support; see risk flags and suggestions.")
    parts.append("Continue tracking for more personalized insights.")
    return " ".join(parts)