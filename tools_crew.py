# tools_crew.py
from crewai.tools import tool
from tools import (
    _fetch_canvas_tasks, _generate_smart_schedule,
    _evaluate_schedule, _sync_study_blocks
)
from canvasapi import Canvas
import os, json

# Instantiate Canvas once at module level (or inject via closure)
_canvas = Canvas(os.getenv("CANVAS_API_URL"), os.getenv("CANVAS_API_KEY"))
_user   = _canvas.get_current_user()

@tool("Fetch Canvas Tasks")
def fetch_canvas_tasks(lookahead_days: int = 7) -> str:
    """Fetches active assignments from Canvas due in the next N days."""
    tasks = _fetch_canvas_tasks(_canvas, _user, lookahead_days)
    return json.dumps(tasks)

@tool("Generate Smart Schedule")
def generate_smart_schedule(
    tasks: str,                  # JSON string — CrewAI passes strings between agents
    sleep_start: int = 22,
    sleep_end: int = 8,
    blackout_dates: str = "[]",  # JSON string list
    max_daily_hours: int = 6
) -> str:
    """Builds a burnout-aware study schedule respecting sleep windows."""
    schedule = _generate_smart_schedule(
        tasks=json.loads(tasks),
        sleep_start=sleep_start,
        sleep_end=sleep_end,
        blackout_dates=json.loads(blackout_dates),
        max_daily_hours=max_daily_hours
    )
    return json.dumps(schedule)

@tool("Evaluate Schedule")
def evaluate_schedule(schedule: str, tasks: str) -> str:
    """
    Critic tool. Checks for burnout (>6h/day) and deadline violations.
    Returns a report with 'valid' boolean and list of warnings.
    """
    report = _evaluate_schedule(json.loads(schedule), json.loads(tasks))
    return json.dumps(report)

@tool("Sync Study Blocks")
def sync_study_blocks(proposed_blocks: str) -> str:
    """
    Surgically syncs the approved plan to Canvas.
    Only call this AFTER the user has confirmed the schedule.
    """
    result = _sync_study_blocks(json.loads(proposed_blocks), _canvas, _user.id)
    return json.dumps(result)