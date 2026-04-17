import json
from datetime import datetime, timedelta

# ── TOOL SCHEMAS (The AI's Menu) ──
TOOL_SCHEMAS = [
    {
        "name": "generate_smart_schedule",
        "description": "Builds a study plan. Respects sleep and skips blackout dates. Returns ISO start/end times.",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "due": {"type": "string"}, "estimated_hours": {"type": "number"}}, "required": ["name", "due"]}},
                "sleep_start": {"type": "integer", "default": 22},
                "sleep_end": {"type": "integer", "default": 8},
                "blackout_dates": {"type": "array", "items": {"type": "string"}, "description": "Dates to skip (YYYY-MM-DD)"}
            },
            "required": ["tasks"]
        }
    },
    {
        "name": "evaluate_schedule",
        "description": "Checks for burnout (>6h/day) and sessions past deadlines.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule": {"type": "array", "items": {"type": "object"}},
                "tasks": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["schedule", "tasks"]
        }
    },
    {
       "name": "sync_study_blocks",
    "description": "Synchronizes the proposed schedule with Canvas. Deletes old HW-HORSE blocks that aren't in the new plan and adds missing ones. Prevents duplicates.",
    "parameters": {
        "type": "object",
        "properties": {
            "proposed_blocks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "start": {"type": "string"},
                        "end": {"type": "string"}
                    }
                }
            }
        },
        "required": ["proposed_blocks"]
    }
    }
]

# ── TOOL IMPLEMENTATIONS ──

def _generate_smart_schedule(tasks, sleep_start=22, sleep_end=8, blackout_dates=None):
    tasks_sorted = sorted(tasks, key=lambda x: x.get("due") or "9999-12-31")
    blackout_dates = blackout_dates or []
    schedule = []
    current_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    for task in tasks_sorted:
        name = task["name"]
        hours = task.get("estimated_hours", 2)
        while hours > 0:
            d_str = current_time.strftime("%Y-%m-%d")
            if d_str in blackout_dates or current_time.hour >= sleep_start or current_time.hour < sleep_end:
                current_time = (current_time + timedelta(days=1)).replace(hour=sleep_end, minute=0)
                continue
            
            session = min(2, hours)
            end = current_time + timedelta(hours=session)
            schedule.append({"task": name, "start": current_time.isoformat(), "end": end.isoformat()})
            hours -= session
            current_time = end + timedelta(minutes=30)
    return schedule

def _evaluate_schedule(schedule, tasks):
    report = {"valid": True, "warnings": [], "daily_load": {}}
    due_map = {t["name"]: t.get("due") for t in tasks}
    
    for b in schedule:
        day = b["start"][:10]
        dur = (datetime.fromisoformat(b["end"]) - datetime.fromisoformat(b["start"])).total_seconds() / 3600
        report["daily_load"][day] = report["daily_load"].get(day, 0) + dur
        
        due_str = due_map.get(b["task"])
        if due_str and datetime.fromisoformat(b["end"]) > datetime.strptime(due_str, "%Y-%m-%dT%H:%M:%SZ"):
            report["valid"] = False
            report["warnings"].append(f"🚨 Deadline Miss: {b['task']}")

    for d, h in report["daily_load"].items():
        if h > 6:
            report["valid"] = False
            report["warnings"].append(f"🔥 Overload: {d} ({h}h)")
    return report

def _sync_study_blocks(proposed_blocks, canvas, user_id):
    # 1. Fetch current Horse events
    start_search = datetime.now().isoformat()
    end_search = (datetime.now() + timedelta(days=14)).isoformat()
    
    existing_events = canvas.get_calendar_events(
        type="event",
        context_codes=[f"user_{user_id}"],
        start_date=start_search,
        end_date=end_search,
        all_events=True
    )
    
    horse_events = [e for e in existing_events if "📚 HW-HORSE:" in getattr(e, 'title', '')]

    # Create "Fingerprints" for comparison: (Title, Start_ISO, End_ISO)
    def get_fp(obj):
        # 1. Handle Canvas Objects
        if hasattr(obj, 'start_at'):
            start = obj.start_at
            end = obj.end_at
            title = obj.title
        # 2. Handle AI-generated Dictionaries
        else:
            start = obj.get('start')
            end = obj.get('end')
            task_name = obj.get('task')
            title = f"📚 HW-HORSE: {task_name}"

        # Clean strings for comparison (remove 'Z' and ensure consistency)
        start = start.replace('Z', '').split('+')[0]
        end = end.replace('Z', '').split('+')[0]
        
        return (title, start, end)

    existing_fps = {get_fp(e): e for e in horse_events}
    proposed_fps = {get_fp(b): b for b in proposed_blocks}

    # 2. DELETE: If it's on Canvas but NOT in the new plan
    deleted_count = 0
    for fp, event_obj in existing_fps.items():
        if fp not in proposed_fps:
            event_obj.delete()
            deleted_count += 1

    # 3. ADD: If it's in the plan but NOT on Canvas
    added_count = 0
    for fp, block_dict in proposed_fps.items():
        if fp not in existing_fps:
            canvas.create_calendar_event(calendar_event={
                "context_code": f"user_{user_id}",
                "title": f"📚 HW-HORSE: {block_dict['task']}",
                "start_at": block_dict['start'],
                "end_at": block_dict['end'],
            })
            added_count += 1

    # 4. KEPT: The ones that were in both (no action taken)
    kept_count = len(existing_fps) - deleted_count

    return {
        "status": "success",
        "added": added_count,
        "deleted": deleted_count,
        "kept_intact": kept_count
    }


# ── DISPATCHER ──

def run_tool(name, inputs, context):
    if inputs is None:
        inputs = {}
    if name == "generate_smart_schedule": return _generate_smart_schedule(**inputs)
    if name == "evaluate_schedule": return _evaluate_schedule(**inputs)
    if name == "sync_study_blocks":
        return _sync_study_blocks(inputs["proposed_blocks"], context["canvas"], context["user_id"])
    return {"error": "Tool not found"}