from datetime import datetime, timedelta

def generate_smart_schedule(tasks, sleep_start=22, sleep_end=8, end_scheduling_at=None, blackout_dates=None):
    """
    WORKFLOW STEP: PLANNING
    Now with Date Disregard: Won't schedule past end_scheduling_at or on blackout_dates.
    """
    # 1. Prioritize
    tasks_sorted = sorted(tasks, key=lambda x: x.get('due') if x.get('due') else '9999-12-31')
    
    schedule = []
    current_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    # Ensure blackout_dates is a list of strings like ["2026-04-18"]
    if blackout_dates is None:
        blackout_dates = []

    for task in tasks_sorted:
        name = task['name']
        hours_remaining = task.get('estimated_hours', 2)
        
        while hours_remaining > 0:
            # --- DATE DISREGARD LOGIC ---
            current_date_str = current_time.strftime('%Y-%m-%d')
            
            # 1. Stop if we've passed the global "End Date"
            if end_scheduling_at and current_time > end_scheduling_at:
                print(f"[PLAN] 🛑 Global cutoff reached. Stopping at {current_time.strftime('%m/%d')}")
                return schedule

            # 2. Jump if the day is a Blackout Date (e.g., Saturday)
            if current_date_str in blackout_dates:
                print(f"[PLAN] 🕶️ Blackout Date detected ({current_date_str}). Skipping to next day.")
                current_time = (current_time + timedelta(days=1)).replace(hour=sleep_end, minute=0)
                continue

            # 3. Sleep jump logic (24h format)
            if current_time.hour >= sleep_start or current_time.hour < sleep_end:
                if current_time.hour >= sleep_start:
                    current_time = (current_time + timedelta(days=1)).replace(hour=sleep_end, minute=0)
                else:
                    current_time = current_time.replace(hour=sleep_end, minute=0)
                continue

            # Create Block
            session_time = min(2, hours_remaining)
            schedule.append({
                "task": name,
                "start": current_time,
                "end": current_time + timedelta(hours=session_time)
            })

            hours_remaining -= session_time
            current_time += timedelta(hours=session_time, minutes=30)
            
    return schedule