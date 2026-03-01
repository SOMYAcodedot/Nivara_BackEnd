from datetime import datetime, timedelta

def predict_cycle(last_period_date, avg_cycle_length):
    try:
        last_date = datetime.strptime(last_period_date, "%Y-%m-%d")
        next_cycle = last_date + timedelta(days=int(avg_cycle_length))

        return {
            "next_cycle_date": next_cycle.strftime("%Y-%m-%d"),
            "ovulation_estimate": (next_cycle - timedelta(days=14)).strftime("%Y-%m-%d")
        }
    except:
        return {
            "error": "Invalid date format. Use YYYY-MM-DD"
        }