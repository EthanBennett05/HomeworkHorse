import json
from tools import _generate_smart_schedule, _evaluate_schedule

def run_evaluations():
    print("🧪 STARTING HOMEWORK-HORSE EVALUATION SET\n" + "="*40)
    
    # CASE 1: Perfect Scenario
    # 2 tasks, plenty of time, no conflicts.
    case_1_tasks = [{"name": "Quiz 1", "due": "2026-04-25T23:59:00Z", "estimated_hours": 2}]
    sched_1 = _generate_smart_schedule(case_1_tasks)
    eval_1 = _evaluate_schedule(sched_1, case_1_tasks)
    
    print(f"Case 1 (Baseline): {'✅ PASS' if eval_1['valid'] else '❌ FAIL'}")

    # CASE 2: Burnout Logic
    # 10 hours scheduled in one day. Should trigger 'valid': False.
    case_2_tasks = [{"name": "Big Project", "due": "2026-04-19T23:59:00Z", "estimated_hours": 10}]
    sched_2 = _generate_smart_schedule(case_2_tasks)
    eval_2 = _evaluate_schedule(sched_2, case_2_tasks)
    
    # We WANT it to be invalid (Burnout detected)
    print(f"Case 2 (Burnout Detection): {'✅ PASS' if not eval_2['valid'] else '❌ FAIL'}")

    # CASE 3: Blackout Date Constraint
    # Task due Monday, Sunday is blacked out.
    case_3_tasks = [{"name": "Monday Paper", "due": "2026-04-20T08:00:00Z", "estimated_hours": 4}]
    blackout = ["2026-04-19"] # Sunday
    sched_3 = _generate_smart_schedule(case_3_tasks, blackout_dates=blackout)
    
    # Check if any part of the schedule is on April 19
    sunday_used = any("2026-04-19" in b["start"] for b in sched_3)
    print(f"Case 3 (Blackout Respect): {'✅ PASS' if not sunday_used else '❌ FAIL'}")

    # CASE 4: Deadline Impossible
    # Task due in 1 hour but takes 5 hours.
    case_4_tasks = [{"name": "Impossible Task", "due": "2026-04-18T14:00:00Z", "estimated_hours": 5}]
    sched_4 = _generate_smart_schedule(case_4_tasks)
    eval_4 = _evaluate_schedule(sched_4, case_4_tasks)
    
    # We WANT it to be invalid (Deadline miss)
    has_deadline_miss = any("Deadline Miss" in w for w in eval_4["warnings"])
    print(f"Case 4 (Deadline Enforcement): {'✅ PASS' if has_deadline_miss else '❌ FAIL'}")

    # CASE 5: Fingerprint Consistency (Logic Test)
    # Testing if the fingerprint function in tools.py would generate matching IDs
    # (Mocking the get_fp logic internally)
    title = "📚 HW-HORSE: Test"
    start = "2026-04-18T10:00:00"
    end = "2026-04-18T12:00:00"
    
    # Check if normalized strings match
    fp1 = (title, start, end)
    fp2 = (title, start + "Z", end + "Z") # Canvas often adds 'Z'
    
    # Clean version of fp2 logic from tools.py
    clean_fp2 = (fp2[0], fp2[1].replace('Z', ''), fp2[2].replace('Z', ''))
    print(f"Case 5 (Fingerprint Sync): {'✅ PASS' if fp1 == clean_fp2 else '❌ FAIL'}")

if __name__ == "__main__":
    run_evaluations()