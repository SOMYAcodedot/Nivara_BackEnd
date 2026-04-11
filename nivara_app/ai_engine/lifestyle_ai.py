def generate_lifestyle_plan(analysis_data):
    """Legacy: used by GET lifestyle/plan/. Kept for backward compatibility."""
    return {
        "recommendation": "Maintain a balanced diet, sleep 7-8 hours, and practice meditation.",
        "exercise": "Light yoga or walking 30 minutes daily.",
        "mental_health_tip": "Practice journaling and gratitude."
    }


# =========================================================
# 🌿 PHASE 4: LIFESTYLE INTELLIGENCE ENGINE
# Inputs: mood_analysis_result, cycle_phase, stress_level
# Outputs: yoga_suggestions, diet_adjustments, sleep_guidance, emotional_regulation_tips
# =========================================================

def generate_lifestyle_recommendations(mood_analysis_result, cycle_phase_info, stress_level):
    """
    LLM-ready: Generates structured lifestyle recommendations from health context.
    Uses rule-based logic; can be extended with LLM for richer personalization.
    
    Args:
        mood_analysis_result: dict with average_mood, dominant_emotion, trend, etc.
        cycle_phase_info: dict with phase, phase_display, energy_level, tips, etc. (from get_cycle_phase/get_cycle_status)
        stress_level: str one of "Low", "Moderate", "High", "Very High", "Unknown"
    
    Returns:
        dict with yoga_suggestions, diet_adjustments, sleep_guidance, emotional_regulation_tips
    """
    phase = (cycle_phase_info or {}).get("phase") or (cycle_phase_info or {}).get("cycle_phase")
    phase_display = (cycle_phase_info or {}).get("phase_display") or (cycle_phase_info or {}).get("phase_display") or "Unknown"
    energy_level = (cycle_phase_info or {}).get("energy_level") or "moderate"
    
    mood = mood_analysis_result or {}
    avg_mood = mood.get("average_mood") or 5
    dominant_emotion = (mood.get("dominant_emotion") or "neutral").lower()
    trend = (mood.get("trend") or "Stable").lower()
    
    stress = (stress_level or "Unknown").strip()
    is_high_stress = stress in ("High", "Very High")
    is_low_stress = stress in ("Low", "Unknown") or not stress
    
    # --- Yoga suggestions (phase + stress aware) ---
    yoga_suggestions = _get_yoga_suggestions(phase, energy_level, is_high_stress, dominant_emotion)
    
    # --- Diet adjustments (phase + stress + mood) ---
    diet_adjustments = _get_diet_adjustments(phase, is_high_stress, dominant_emotion, phase_display)
    
    # --- Sleep guidance (stress + phase) ---
    sleep_guidance = _get_sleep_guidance(is_high_stress, phase, avg_mood)
    
    # --- Emotional regulation tips (mood + stress) ---
    emotional_regulation_tips = _get_emotional_regulation_tips(
        dominant_emotion, is_high_stress, trend, phase_display
    )
    
    return {
        "yoga_suggestions": yoga_suggestions,
        "diet_adjustments": diet_adjustments,
        "sleep_guidance": sleep_guidance,
        "emotional_regulation_tips": emotional_regulation_tips,
    }


def _get_yoga_suggestions(phase, energy_level, is_high_stress, dominant_emotion):
    """Generate yoga suggestions based on cycle phase, energy, and stress."""
    suggestions = []
    
    if phase == "menstrual":
        suggestions = [
            {"title": "Restorative yoga", "description": "Gentle poses to support low energy and comfort.", "duration_min": 15},
            {"title": "Child's pose & cat-cow", "description": "Ease cramps and lower back tension.", "duration_min": 10},
            {"title": "Legs up the wall", "description": "Promotes relaxation and circulation.", "duration_min": 5},
        ]
    elif phase == "follicular":
        suggestions = [
            {"title": "Vinyasa flow", "description": "Match your rising energy with dynamic movement.", "duration_min": 25},
            {"title": "Sun salutations", "description": "Build strength and focus.", "duration_min": 15},
            {"title": "Standing poses", "description": "Warrior series for stability and confidence.", "duration_min": 20},
        ]
    elif phase == "ovulation":
        suggestions = [
            {"title": "Power yoga", "description": "Peak energy phase—good for intensity.", "duration_min": 30},
            {"title": "Balance poses", "description": "Tree, half moon to harness focus.", "duration_min": 15},
            {"title": "Backbends", "description": "Open heart and boost mood.", "duration_min": 10},
        ]
    else:
        # luteal or unknown
        suggestions = [
            {"title": "Moderate flow", "description": "Steady movement without overexertion.", "duration_min": 20},
            {"title": "Hip openers", "description": "Ease tension and support mood.", "duration_min": 15},
            {"title": "Forward folds", "description": "Calm the nervous system.", "duration_min": 10},
        ]
    
    if is_high_stress:
        suggestions.insert(0, {
            "title": "Breathing focus (pranayama)",
            "description": "4-7-8 or alternate nostril breathing to reduce stress first.",
            "duration_min": 5
        })
    
    if dominant_emotion in ("anxious", "stressed", "overwhelmed"):
        suggestions.append({
            "title": "Grounding poses",
            "description": "Seated twists and gentle forward folds for grounding.",
            "duration_min": 10
        })
    
    return {"suggestions": suggestions, "summary": _yoga_summary(phase, is_high_stress)}


def _yoga_summary(phase, is_high_stress):
    if is_high_stress:
        return "Prioritize calming, breath-focused practice before longer flows."
    if phase == "menstrual":
        return "Focus on gentle, restorative poses; avoid inversions and intense core work."
    if phase == "ovulation":
        return "Good time for stronger flows; listen to your body and hydrate."
    return "Moderate intensity supports your current phase; rest when needed."


def _get_diet_adjustments(phase, is_high_stress, dominant_emotion, phase_display):
    """Diet recommendations by phase and stress."""
    adjustments = []
    
    if phase == "menstrual":
        adjustments = [
            {"category": "Iron & nutrients", "tip": "Include iron-rich foods (leafy greens, legumes) and vitamin C to support absorption."},
            {"category": "Hydration", "tip": "Stay well hydrated; warm fluids can ease cramping."},
            {"category": "Anti-inflammatory", "tip": "Omega-3 and magnesium (nuts, seeds, dark chocolate) may ease discomfort."},
        ]
    elif phase in ("follicular", "ovulation"):
        adjustments = [
            {"category": "Energy support", "tip": "Balanced meals with complex carbs and protein to sustain energy."},
            {"category": "Hydration", "tip": "Adequate water supports metabolism and temperature regulation."},
            {"category": "Variety", "tip": "Good time to include a wide range of vegetables and whole grains."},
        ]
    else:
        adjustments = [
            {"category": "Blood sugar", "tip": "Regular meals with complex carbs can help stabilize mood and energy."},
            {"category": "Magnesium", "tip": "Leafy greens, nuts, and seeds may ease PMS-related tension."},
            {"category": "Caffeine", "tip": "Consider reducing caffeine in the second half of the day if it affects sleep or anxiety."},
        ]
    
    if is_high_stress:
        adjustments.append({
            "category": "Stress support",
            "tip": "Limit excess caffeine and sugar; prioritize protein and fiber for steady energy."
        })
    
    return {"adjustments": adjustments, "phase_note": f"Recommendations aligned with {phase_display}."}


def _get_sleep_guidance(is_high_stress, phase, avg_mood):
    """Sleep guidance from stress and phase."""
    tips = []
    target_hours = "7–8"
    
    if is_high_stress:
        tips = [
            "Keep a consistent sleep and wake time, even on weekends.",
            "Wind down 30–60 minutes before bed (no screens).",
            "Try a short breathing exercise or body scan if you can't fall asleep.",
            "Avoid heavy meals and caffeine close to bedtime.",
        ]
        target_hours = "7–9"
    elif phase == "luteal":
        tips = [
            "Hormonal shifts can affect sleep; consistency helps.",
            "Cool, dark room and a regular bedtime support better rest.",
            "Light stretching or reading (not screens) before bed.",
        ]
    else:
        tips = [
            "Aim for a consistent bedtime to support your cycle rhythm.",
            "Limit screens 1 hour before bed.",
            "Light activity earlier in the day can improve sleep quality.",
        ]
    
    if avg_mood and avg_mood < 5:
        tips.append("If low mood affects sleep, gentle evening routine and limiting late-day stressors can help.")
    
    return {
        "target_hours": target_hours,
        "tips": tips,
        "summary": "Prioritize consistency and a calming routine; adjust for stress and cycle phase."
    }


def _get_emotional_regulation_tips(dominant_emotion, is_high_stress, trend, phase_display):
    """Emotional regulation tips from mood and stress."""
    tips = []
    
    emotion_tips = {
        "anxious": "Practice 4-7-8 breathing or grounding (5-4-3-2-1 senses) when anxiety rises.",
        "stressed": "Break tasks into small steps; take short breaks and move your body.",
        "sad": "Allow yourself to feel; small acts of self-care and connection can help.",
        "irritated": "Step away briefly if possible; name the feeling to create space.",
        "overwhelmed": "List 1–3 priorities; defer the rest; ask for help if needed.",
        "tired": "Honor rest; gentle movement or a short walk can sometimes boost energy.",
        "neutral": "Use this stable window for habits that support future resilience.",
        "happy": "Savor the moment; gentle routines help maintain balance.",
        "calm": "Good time for reflection or planning ahead.",
        "excited": "Channel energy into something meaningful; balance with rest.",
        "hopeful": "Note what’s going well; small steps sustain hope.",
        "content": "Maintain routines that support this sense of balance.",
    }
    
    tips.append(emotion_tips.get(dominant_emotion, "Check in with yourself; small, kind actions support emotional balance."))
    
    if is_high_stress:
        tips.extend([
            "Set boundaries: say no to non-essentials when stress is high.",
            "Short mindfulness or body-scan can lower stress reactivity.",
        ])
    
    if trend == "declining":
        tips.append("Mood dips are normal; focus on basics: sleep, food, movement, and one small pleasure.")
    
    return {
        "tips": tips,
        "context_note": f"Tailored to your current emotional state and {phase_display}."
    }