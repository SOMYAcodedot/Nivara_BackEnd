from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List


# =========================================================
# 🌸 PHASE 3: CYCLE INTELLIGENCE LAYER
# Comprehensive Cycle Tracking & Prediction Engine
# =========================================================


def predict_cycle(last_period_date, avg_cycle_length):
    """
    Legacy function - kept for backward compatibility.
    Predicts next cycle date and ovulation estimate.
    """
    try:
        if isinstance(last_period_date, str):
            last_date = datetime.strptime(last_period_date, "%Y-%m-%d")
        else:
            last_date = last_period_date
            
        next_cycle = last_date + timedelta(days=int(avg_cycle_length))

        return {
            "next_cycle_date": next_cycle.strftime("%Y-%m-%d"),
            "ovulation_estimate": (next_cycle - timedelta(days=14)).strftime("%Y-%m-%d")
        }
    except:
        return {
            "error": "Invalid date format. Use YYYY-MM-DD"
        }


# =========================================================
# 🔮 CYCLE PHASE CALCULATIONS
# =========================================================

def calculate_cycle_day(last_period_start: date, current_date: date = None) -> int:
    """
    Calculate current day in the menstrual cycle.
    Day 1 = first day of period.
    """
    if current_date is None:
        current_date = date.today()
    
    if isinstance(last_period_start, str):
        last_period_start = datetime.strptime(last_period_start, "%Y-%m-%d").date()
    
    days_diff = (current_date - last_period_start).days
    return days_diff + 1  # Day 1 is the first day


def get_cycle_phase(cycle_day: int, cycle_length: int = 28, period_length: int = 5) -> Dict[str, Any]:
    """
    Determine current cycle phase based on cycle day.
    
    Phases:
    - Menstrual: Day 1 to period_length
    - Follicular: Day (period_length+1) to ~Day 13
    - Ovulation: ~Day 14 (adjusted for cycle length)
    - Luteal: Day 15 to cycle_length
    """
    # Adjust ovulation day based on cycle length (typically 14 days before next period)
    ovulation_day = cycle_length - 14
    
    if cycle_day <= period_length:
        return {
            "phase": "menstrual",
            "phase_display": "Menstrual Phase",
            "description": "Your body is shedding the uterine lining. Rest and gentle self-care are recommended.",
            "energy_level": "low",
            "hormone_status": "Low estrogen and progesterone",
            "tips": [
                "Stay hydrated and eat iron-rich foods",
                "Gentle exercise like yoga or walking",
                "Allow extra rest if needed",
                "Use heat therapy for cramps"
            ]
        }
    elif cycle_day <= ovulation_day - 3:
        return {
            "phase": "follicular",
            "phase_display": "Follicular Phase",
            "description": "Estrogen is rising, and you may feel more energetic and creative.",
            "energy_level": "increasing",
            "hormone_status": "Rising estrogen",
            "tips": [
                "Great time for challenging workouts",
                "Plan important meetings or creative projects",
                "Good time to try new things",
                "Skin may be clearer during this phase"
            ]
        }
    elif cycle_day <= ovulation_day + 2:
        return {
            "phase": "ovulation",
            "phase_display": "Ovulation Phase",
            "description": "Peak fertility window. Energy and confidence are typically highest.",
            "energy_level": "high",
            "hormone_status": "Peak estrogen, LH surge",
            "tips": [
                "Peak energy - great for intense workouts",
                "Social activities and networking",
                "You may feel more confident",
                "Fertile window if trying to conceive"
            ]
        }
    else:
        # Check if in PMS window (last 5-7 days before next period)
        days_until_period = cycle_length - cycle_day + 1
        is_pms_window = days_until_period <= 7
        
        return {
            "phase": "luteal",
            "phase_display": "Luteal Phase" + (" (PMS Window)" if is_pms_window else ""),
            "description": "Progesterone rises. You may experience PMS symptoms as hormones shift." if is_pms_window else "Progesterone is dominant. Energy may start to stabilize.",
            "energy_level": "decreasing" if is_pms_window else "moderate",
            "hormone_status": "High progesterone" + (", declining estrogen" if is_pms_window else ""),
            "tips": [
                "Focus on stress management",
                "Moderate exercise is beneficial",
                "Complex carbs can help with mood",
                "Practice self-compassion"
            ] if is_pms_window else [
                "Good time for organization and detail work",
                "Maintain regular sleep schedule",
                "Balanced nutrition supports hormone health",
                "Moderate intensity workouts"
            ]
        }


def calculate_fertile_window(last_period_start: date, cycle_length: int = 28) -> Dict[str, Any]:
    """
    Calculate the fertile window (typically 5 days before ovulation + ovulation day).
    """
    if isinstance(last_period_start, str):
        last_period_start = datetime.strptime(last_period_start, "%Y-%m-%d").date()
    
    # Ovulation typically occurs 14 days before next period
    ovulation_day_in_cycle = cycle_length - 14
    ovulation_date = last_period_start + timedelta(days=ovulation_day_in_cycle - 1)
    
    # Fertile window: 5 days before ovulation + ovulation day
    fertile_start = ovulation_date - timedelta(days=5)
    fertile_end = ovulation_date + timedelta(days=1)
    
    return {
        "fertile_window_start": fertile_start.strftime("%Y-%m-%d"),
        "fertile_window_end": fertile_end.strftime("%Y-%m-%d"),
        "ovulation_date": ovulation_date.strftime("%Y-%m-%d"),
        "ovulation_day_in_cycle": ovulation_day_in_cycle
    }


def predict_next_period(last_period_start: date, cycle_length: int = 28) -> Dict[str, Any]:
    """
    Predict the next period start date and provide countdown.
    """
    if isinstance(last_period_start, str):
        last_period_start = datetime.strptime(last_period_start, "%Y-%m-%d").date()
    
    today = date.today()
    next_period = last_period_start + timedelta(days=cycle_length)
    
    # If predicted date has passed, calculate next cycle
    while next_period < today:
        next_period += timedelta(days=cycle_length)
    
    days_until = (next_period - today).days
    
    return {
        "predicted_next_period": next_period.strftime("%Y-%m-%d"),
        "days_until_next_period": days_until,
        "countdown_message": get_countdown_message(days_until)
    }


def get_countdown_message(days: int) -> str:
    """Generate friendly countdown message."""
    if days == 0:
        return "Your period may start today"
    elif days == 1:
        return "Your period may start tomorrow"
    elif days <= 3:
        return f"Your period is expected in {days} days"
    elif days <= 7:
        return f"About a week until your period ({days} days)"
    else:
        return f"{days} days until your expected period"


# =========================================================
# 📊 CYCLE STATUS DASHBOARD
# =========================================================

def get_cycle_status(
    last_period_start: date,
    cycle_length: int = 28,
    period_length: int = 5,
    current_date: date = None
) -> Dict[str, Any]:
    """
    Get comprehensive current cycle status for dashboard display.
    Returns the JSON structure required by frontend.
    """
    if current_date is None:
        current_date = date.today()
    
    if isinstance(last_period_start, str):
        last_period_start = datetime.strptime(last_period_start, "%Y-%m-%d").date()
    
    # Calculate cycle day
    cycle_day = calculate_cycle_day(last_period_start, current_date)
    
    # Handle if cycle_day exceeds cycle_length (new cycle started)
    if cycle_day > cycle_length:
        # Calculate how many cycles have passed
        cycles_passed = cycle_day // cycle_length
        adjusted_last_period = last_period_start + timedelta(days=cycles_passed * cycle_length)
        cycle_day = calculate_cycle_day(adjusted_last_period, current_date)
        last_period_start = adjusted_last_period
    
    # Get phase info
    phase_info = get_cycle_phase(cycle_day, cycle_length, period_length)
    
    # Predict next period
    next_period_info = predict_next_period(last_period_start, cycle_length)
    
    # Get fertile window
    fertile_info = calculate_fertile_window(last_period_start, cycle_length)
    
    # Determine if in PMS window (last 7 days before period)
    pms_window = next_period_info["days_until_next_period"] <= 7 and phase_info["phase"] == "luteal"
    
    return {
        "cycle_day": cycle_day,
        "cycle_phase": phase_info["phase"],
        "phase_display": phase_info["phase_display"],
        "phase_description": phase_info["description"],
        "energy_level": phase_info["energy_level"],
        "hormone_status": phase_info["hormone_status"],
        "phase_tips": phase_info["tips"],
        "days_until_next_period": next_period_info["days_until_next_period"],
        "predicted_next_period": next_period_info["predicted_next_period"],
        "countdown_message": next_period_info["countdown_message"],
        "pms_window": pms_window,
        "fertile_window": fertile_info,
        "is_fertile_today": is_in_fertile_window(last_period_start, cycle_length, current_date)
    }


def is_in_fertile_window(last_period_start: date, cycle_length: int, current_date: date = None) -> bool:
    """Check if current date is within fertile window."""
    if current_date is None:
        current_date = date.today()
    
    fertile_info = calculate_fertile_window(last_period_start, cycle_length)
    fertile_start = datetime.strptime(fertile_info["fertile_window_start"], "%Y-%m-%d").date()
    fertile_end = datetime.strptime(fertile_info["fertile_window_end"], "%Y-%m-%d").date()
    
    return fertile_start <= current_date <= fertile_end


# =========================================================
# 🔍 CYCLE IRREGULARITY DETECTION
# =========================================================

def detect_irregularity(period_logs: List[Dict], baseline_cycle_length: int = 28) -> Dict[str, Any]:
    """
    Analyze period logs to detect cycle irregularities.
    """
    if not period_logs or len(period_logs) < 2:
        return {
            "has_data": False,
            "message": "Need at least 2 period records for irregularity analysis"
        }
    
    # Calculate cycle lengths from logs
    cycle_lengths = [log.get("cycle_length_from_previous") for log in period_logs if log.get("cycle_length_from_previous")]
    
    if not cycle_lengths:
        return {
            "has_data": False,
            "message": "Insufficient cycle data for analysis"
        }
    
    avg_length = sum(cycle_lengths) / len(cycle_lengths)
    
    # Calculate variance
    variance = sum((x - avg_length) ** 2 for x in cycle_lengths) / len(cycle_lengths)
    std_dev = variance ** 0.5
    
    # Detect irregularities
    irregularities = []
    
    # High variation (>7 days std dev is considered irregular)
    if std_dev > 7:
        irregularities.append({
            "type": "high_variation",
            "severity": "moderate" if std_dev < 10 else "significant",
            "message": f"Your cycles vary significantly (±{round(std_dev, 1)} days)"
        })
    
    # Very short cycles (<21 days)
    short_cycles = [l for l in cycle_lengths if l < 21]
    if short_cycles:
        irregularities.append({
            "type": "short_cycles",
            "severity": "attention",
            "message": f"You've had {len(short_cycles)} cycle(s) shorter than 21 days",
            "recommendation": "Short cycles may indicate hormonal imbalances. Consider consulting a healthcare provider."
        })
    
    # Very long cycles (>35 days)
    long_cycles = [l for l in cycle_lengths if l > 35]
    if long_cycles:
        irregularities.append({
            "type": "long_cycles",
            "severity": "attention",
            "message": f"You've had {len(long_cycles)} cycle(s) longer than 35 days",
            "recommendation": "Long cycles can be normal but may also indicate conditions like PCOS. Consider tracking symptoms."
        })
    
    # Determine regularity status
    if std_dev <= 3:
        regularity_status = "very_regular"
        regularity_message = "Your cycles are very consistent"
    elif std_dev <= 7:
        regularity_status = "mostly_regular"
        regularity_message = "Your cycles are fairly regular with minor variation"
    else:
        regularity_status = "irregular"
        regularity_message = "Your cycles show significant variation"
    
    return {
        "has_data": True,
        "cycles_analyzed": len(cycle_lengths),
        "average_cycle_length": round(avg_length, 1),
        "cycle_variation_days": round(std_dev, 1),
        "shortest_cycle": min(cycle_lengths),
        "longest_cycle": max(cycle_lengths),
        "regularity_status": regularity_status,
        "regularity_message": regularity_message,
        "irregularities": irregularities,
        "needs_attention": len(irregularities) > 0
    }


# =========================================================
# 🧠 LLM ENHANCEMENT: PERSONALIZED INSIGHTS
# =========================================================

def generate_personalized_insights(
    cycle_status: Dict[str, Any],
    mood_data: Optional[Dict] = None,
    checkin_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Generate personalized advice connecting hormonal state with emotional patterns.
    """
    insights = []
    recommendations = []
    
    phase = cycle_status.get("cycle_phase")
    pms_window = cycle_status.get("pms_window", False)
    
    # Phase-specific insights
    if phase == "menstrual":
        insights.append("During menstruation, it's normal to feel lower energy. Your body is doing important work.")
        recommendations.extend([
            "Prioritize rest and avoid overcommitting",
            "Iron-rich foods can help replenish what you lose",
            "Gentle movement can actually help with cramps"
        ])
    
    elif phase == "follicular":
        insights.append("Rising estrogen during the follicular phase often brings increased energy and optimism.")
        recommendations.extend([
            "Great time for new projects or challenging tasks",
            "Your body is primed for high-intensity exercise",
            "Social activities may feel more appealing"
        ])
    
    elif phase == "ovulation":
        insights.append("Peak fertility and often peak energy! You may feel more confident and social.")
        recommendations.extend([
            "Schedule important presentations or conversations",
            "Your metabolism is slightly higher - honor your appetite",
            "Stay hydrated as body temperature rises slightly"
        ])
    
    elif phase == "luteal":
        if pms_window:
            insights.append("You're in the PMS window where hormones are shifting. Mood changes are normal.")
            recommendations.extend([
                "Be extra gentle with yourself",
                "Complex carbs can help stabilize mood",
                "Reduce caffeine and alcohol if sensitive",
                "Magnesium-rich foods may ease symptoms"
            ])
        else:
            insights.append("The luteal phase is a time of consolidation. Your body is preparing for the next cycle.")
            recommendations.extend([
                "Focus on routine tasks rather than new initiatives",
                "Maintain consistent sleep schedule",
                "Moderate exercise is beneficial"
            ])
    
    # Integrate mood data if available
    if mood_data:
        stress_level = mood_data.get("stress_level")
        if stress_level in ["High", "Very High"]:
            insights.append("Your stress levels appear elevated. This can affect your cycle and hormonal balance.")
            recommendations.append("Consider stress-reduction practices like deep breathing or meditation")
    
    # Integrate recent checkin data
    if checkin_data:
        energy = checkin_data.get("energy_level")
        symptoms = checkin_data.get("physical_symptoms", [])
        
        if energy in ["very_low", "low"]:
            insights.append("Your reported low energy aligns with your cycle phase. This is temporary.")
        
        if "cramps" in symptoms:
            recommendations.append("For cramp relief: heat therapy, gentle stretching, and staying hydrated help")
        
        if "headache" in symptoms:
            recommendations.append("Hormonal headaches are common. Ensure adequate hydration and consider magnesium")
    
    return {
        "insights": insights,
        "recommendations": recommendations,
        "phase_summary": f"You're on Day {cycle_status['cycle_day']} ({cycle_status['phase_display']})",
        "hormone_connection": cycle_status.get("hormone_status", "")
    }


# =========================================================
# 📱 FULL CYCLE DASHBOARD DATA
# =========================================================

def get_full_cycle_dashboard(
    cycle_profile: Dict[str, Any],
    recent_checkin: Optional[Dict] = None,
    mood_summary: Optional[Dict] = None,
    period_logs: Optional[List] = None
) -> Dict[str, Any]:
    """
    Generate the complete cycle dashboard JSON as specified in requirements.
    """
    # Extract profile data
    last_period_start = cycle_profile.get("last_period_start_date")
    cycle_length = cycle_profile.get("average_cycle_length_days", 28)
    period_length = cycle_profile.get("average_period_length_days", 5)
    
    # Get current cycle status
    status = get_cycle_status(last_period_start, cycle_length, period_length)
    
    # Get personalized insights
    insights = generate_personalized_insights(status, mood_summary, recent_checkin)
    
    # Get irregularity analysis if we have period logs
    irregularity = None
    if period_logs:
        irregularity = detect_irregularity(period_logs, cycle_length)
    
    return {
        "cycle_profile": {
            "last_period_start_date": last_period_start.strftime("%Y-%m-%d") if isinstance(last_period_start, date) else last_period_start,
            "average_cycle_length": cycle_length,
            "average_period_length": period_length,
            "cycle_regular": cycle_profile.get("cycle_regularity", "mostly_regular"),
            "flow_intensity_last_period": cycle_profile.get("flow_intensity_last_period", "moderate"),
            "spotting_between_periods": cycle_profile.get("spotting_between_periods", "never"),
            "typical_pms_symptoms": cycle_profile.get("typical_pms_symptoms", []),
            "birth_control_status": cycle_profile.get("birth_control_status", "no"),
            "reproductive_status": cycle_profile.get("reproductive_status", "none")
        },
        "current_cycle_status": {
            "cycle_day": status["cycle_day"],
            "cycle_phase": status["cycle_phase"],
            "phase_display": status["phase_display"],
            "days_until_next_period": status["days_until_next_period"],
            "pms_window": status["pms_window"],
            "predicted_next_period": status["predicted_next_period"],
            "countdown_message": status["countdown_message"],
            "is_fertile_today": status["is_fertile_today"],
            "fertile_window": status["fertile_window"],
            "phase_description": status["phase_description"],
            "energy_level": status["energy_level"],
            "hormone_status": status["hormone_status"],
            "phase_tips": status["phase_tips"]
        },
        "recent_checkin": recent_checkin or {
            "mood": [],
            "energy_level": None,
            "physical_symptoms": [],
            "user_notes": None
        },
        "personalized_insights": insights,
        "irregularity_analysis": irregularity
    }