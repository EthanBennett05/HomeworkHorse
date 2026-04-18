import json
import pytz
import os
from datetime import datetime, timedelta

# -- TOOL SCHEMAS --
TOOL_SCHEMAS = [
    {
        "name": "fetch_canvas_tasks",
        "description": "Fetches active assignments from Canvas for the next 7 days.",
        "parameters": {
            "type": "object",
            "properties": {
                "lookahead_days": {"type": "integer", "default": 7}
            }
        }
    },
    {
        "name": "generate_smart_schedule",
        "description": "Builds a study plan. Respects sleep and skips blackout dates.",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array", 
                    "items": {
                        "type": "object", 
                        "properties": {
                            "name": {"type": "string"}, 
                            "due": {"type": "string"}, 
                            "estimated_hours": {"type": "number"}
                        }, 
                        "required": ["name", "due"]
                    }
                },
                "sleep_start": {"type": "integer", "default": 22},
                "sleep_end": {"type": "integer", "default": 8},
                "blackout_dates": {"type": "array", "items": {"type": "string"}},
                "max_daily_hours": {
                    "type": "integer", 
                    "default": 6, 
                    "description": "The maximum amount of study hours allowed per day to prevent burnout."
                }
            },
            "required": ["tasks"]
        }
    },
    {
        "name": "evaluate_schedule",
        "description": "The Critic tool. Checks for burnout (>6h/day) and sessions past deadlines.",
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
        "description": "Surgically syncs the plan to Canvas. Deletes obsolete blocks, adds new ones, keeps identical ones.",
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

# -- IMPLEMENTATIONS --

def _fetch_canvas_tasks(canvas, user, lookahead_days=7):
    courses = user.get_courses(enrollment_state="active")
    codes = [f"course_{c.id}" for c in courses] + [f"user_{user.id}"]
    now = datetime.now(pytz.utc)
    horizon = now + timedelta(days=lookahead_days)
    
    events = canvas.get_calendar_events(type="assignment", context_codes=codes, all_events=True)
    tasks = []
    for e in events:
        if hasattr(e, "end_at") and e.end_at:
            due = datetime.strptime(e.end_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
            if now <= due <= horizon:
                tasks.append({"name": e.title, "due": e.end_at})
    return tasks

def _generate_smart_schedule(tasks, sleep_start=22, sleep_end=8, blackout_dates=None, max_daily_hours=6):
    tasks_sorted = sorted(tasks, key=lambda x: x.get("due") or "9999-12-31")
    blackout_dates = blackout_dates or []
    schedule = []
    current_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    # Track hours per day to enforce the limit
    daily_tracker = {}

    for task in tasks_sorted:
        name = task["name"]
        hours = task.get("estimated_hours", 2)
        while hours > 0:
            d_str = current_time.strftime("%Y-%m-%d")
            
            # Check for: Blackout, Sleep, OR Max Daily Hours reached
            day_hours = daily_tracker.get(d_str, 0)
            if d_str in blackout_dates or current_time.hour >= sleep_start or current_time.hour < sleep_end or day_hours >= max_daily_hours:
                current_time = (current_time + timedelta(days=1)).replace(hour=sleep_end, minute=0)
                continue
            
            session = min(2, hours, max_daily_hours - day_hours)
            if session <= 0: # Safety break
                current_time = (current_time + timedelta(days=1)).replace(hour=sleep_end, minute=0)
                continue

            end = current_time + timedelta(hours=session)
            schedule.append({"task": name, "start": current_time.isoformat(), "end": end.isoformat()})
            
            daily_tracker[d_str] = day_hours + session
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
    start_search = datetime.now().isoformat()
    end_search = (datetime.now() + timedelta(days=14)).isoformat()
    
    existing_events = canvas.get_calendar_events(
        type="event", context_codes=[f"user_{user_id}"],
        start_date=start_search, end_date=end_search, all_events=True
    )
    horse_events = [e for e in existing_events if "📚 HW-HORSE:" in getattr(e, 'title', '')]

    def get_fp(obj):
        if hasattr(obj, 'start_at'):
            start, end, title = obj.start_at, obj.end_at, obj.title
        else:
            start, end, title = obj.get('start'), obj.get('end'), f"📚 HW-HORSE: {obj.get('task')}"
        return (title, start.replace('Z', '').split('+')[0], end.replace('Z', '').split('+')[0])

    existing_fps = {get_fp(e): e for e in horse_events}
    proposed_fps = {get_fp(b): b for b in proposed_blocks}

    deleted = 0
    for fp, event_obj in existing_fps.items():
        if fp not in proposed_fps:
            event_obj.delete()
            deleted += 1

    added = 0
    for fp, block in proposed_fps.items():
        if fp not in existing_fps:
            canvas.create_calendar_event(calendar_event={
                "context_code": f"user_{user_id}", "title": fp[0],
                "start_at": block['start'], "end_at": block['end']
            })
            added += 1

    return {"status": "success", "added": added, "deleted": deleted, "kept_intact": len(existing_fps) - deleted}

def run_tool(name, inputs, context):
    inputs = inputs or {}
    if name == "fetch_canvas_tasks": return _fetch_canvas_tasks(context["canvas"], context["user"], **inputs)
    if name == "generate_smart_schedule": return _generate_smart_schedule(**inputs)
    if name == "evaluate_schedule": return _evaluate_schedule(**inputs)
    if name == "sync_study_blocks": return _sync_study_blocks(inputs["proposed_blocks"], context["canvas"], context["user_id"])
    return {"error": "Tool not found"}