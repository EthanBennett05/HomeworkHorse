# crew.py
from crewai import Agent, Task, Crew, Process, LLM
import os
qwen = LLM(
    model="huggingface/Qwen/Qwen2.5-72B-Instruct",
    api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
)
from tools_crew import (
    fetch_canvas_tasks, generate_smart_schedule,
    evaluate_schedule, sync_study_blocks
)
from datetime import datetime

# ── AGENTS ──────────────────────────────────────────────────────────────────

scout = Agent(
    role="Canvas Scout",
    llm = qwen,
    goal="Retrieve all upcoming assignments from Canvas and hand them off accurately.",
    backstory=(
        "You are a meticulous academic assistant. You specialize in reading "
        "Canvas calendars and surfacing what deadlines are approaching."
    ),
    tools=[fetch_canvas_tasks],
    verbose=True,
    tracing=True,
    allow_delegation=False,
)

planner = Agent(
    role="Study Planner",
    llm = qwen,
    goal=(
        "Generate a valid study schedule that avoids burnout and never misses a "
        "deadline. Re-plan if the critic flags issues (max 2 retries)."
    ),
    backstory=(
        "You are a productivity strategist who transforms raw task lists into "
        "achievable, hour-by-hour study blocks. You respect sleep, daily limits, "
        "and deadlines. When the critic rejects your plan, you adjust parameters "
        "— tighter max_daily_hours, different sleep windows — and try again."
    ),
    tools=[generate_smart_schedule, evaluate_schedule],
    verbose=True,
    tracing=True,
    allow_delegation=False,
)

syncer = Agent(
    role="Calendar Syncer",
    llm = qwen,
    goal="Write the approved schedule to Canvas cleanly and report what changed.",
    backstory=(
        "You are a precise integration agent. You take an approved JSON schedule "
        "and push it to Canvas using a surgical, fingerprint-based sync that "
        "never creates duplicates."
    ),
    tools=[sync_study_blocks],
    verbose=True,
    tracing=True,
    allow_delegation=False,
)

# ── TASKS ────────────────────────────────────────────────────────────────────

today = datetime.now().strftime("%A, %B %d, %Y")

task_fetch = Task(
    description=f"Today is {today}. Fetch all Canvas assignments due in the next 7 days.",
    expected_output=(
        "A JSON array of task objects, each with 'name', 'due', and optionally "
        "'estimated_hours'. Example: [{\"name\": \"Essay\", \"due\": \"2026-05-01T23:59:00Z\"}]"
    ),
    agent=scout,
)

task_plan = Task(
    description=(
        "Using the task list from the scout, generate a study schedule. "
        "Then evaluate it. If 'valid' is false, adjust max_daily_hours or "
        "sleep parameters and regenerate — up to 2 retries. "
        "Present the final approved schedule as a friendly calendar: "
        "use day names (e.g. 'Tuesday, April 21st') and 12-hour AM/PM times. "
        "Ask the user: 'Shall I sync this plan to your Canvas calendar? (y/n)'"
    ),
    expected_output=(
        "A human-readable study calendar AND the raw approved schedule as a "
        "JSON array of blocks (task, start, end) appended at the bottom "
        "for downstream use."
    ),
    agent=planner,
    context=[task_fetch],          # planner sees the scout's output
)

task_sync = Task(
    description=(
        "The user has confirmed the schedule. Extract the JSON block array "
        "from the planner's output and call sync_study_blocks with it. "
        "Report how many events were added, deleted, and kept intact."
    ),
    expected_output=(
        "A plain-English sync summary: e.g. '✅ Synced: 5 added, 2 deleted, "
        "3 kept intact.'"
    ),
    agent=syncer,
    context=[task_plan],
)

# ── CREW ─────────────────────────────────────────────────────────────────────

homework_horse_crew = Crew(
    agents=[scout, planner, syncer],
    tasks=[task_fetch, task_plan, task_sync],
    process=Process.sequential,   # scout → planner → syncer
    verbose=True,
    tracing=True,
)