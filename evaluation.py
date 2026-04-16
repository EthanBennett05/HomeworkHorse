from datetime import datetime

def evaluate_schedule(schedule, tasks):
    """
    WORKFLOW STEP: EVALUATION
    Checks for over-scheduling (burnout) and deadline violations.
    """
    report = {"valid": True, "warnings": [], "daily_load": {}}

    for block in schedule:
        day = block['start'].strftime('%Y-%m-%d')
        duration = (block['end'] - block['start']).total_seconds() / 3600
        report["daily_load"][day] = report["daily_load"].get(day, 0) + duration

    # 1. Burnout Check
    for day, hours in report["daily_load"].items():
        if hours > 6:
            report["valid"] = False
            report["warnings"].append(f"🔥 Burnout Risk: {day} has {hours}hrs of study.")

    # 2. Deadline Check
    for block in schedule:
        # Find the original task to check its deadline
        for t in tasks:
            if t['name'] == block['task'] and t['due']:
                try:
                    due_dt = datetime.strptime(t['due'], "%Y-%m-%dT%H:%M:%SZ")
                    if block['end'] > due_dt:
                        report["valid"] = False
                        report["warnings"].append(f"🚨 Deadline: '{block['task']}' block ends after it's due!")
                except:
                    continue # Skip if date format is weird

    return report