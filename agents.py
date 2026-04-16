import os
import json
from dotenv import load_dotenv
import requests


# Load API key
load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"

headers = {
    "Authorization": f"Bearer {HF_API_KEY}"
}

# -----------------------------
# GLOBAL STATE
# -----------------------------
state = {
    "goal": "Generate and refine a study schedule that completes all assignments before deadlines.",
    "tasks": [],
    "schedule": [],
    "logs": []
}

# -----------------------------
# LOGGING FUNCTION
# -----------------------------
def log(message):
    state["logs"].append(message)
    print(message)

# -----------------------------
# TOOL: SCHEDULING FUNCTION
# -----------------------------
def generate_schedule(tasks):
    log("Tool: Generating schedule...")

    # Sort tasks by earliest deadline
    tasks_sorted = sorted(tasks, key=lambda x: x["due"])

    schedule = []
    current_day = 1

    for task in tasks_sorted:
        hours_left = task["estimated_hours"]

        while hours_left > 0:
            block = min(2, hours_left)  # max 2 hours per block

            schedule.append({
                "task": task["name"],
                "day": current_day,
                "hours": block
            })

            hours_left -= block
            current_day += 1

    return schedule

# -----------------------------
# TOOL: EVALUATE SCHEDULE
# -----------------------------
def evaluate_schedule(schedule, tasks):
    log("Tool: Evaluating schedule...")

    total_hours_per_day = {}

    for item in schedule:
        day = item["day"]
        total_hours_per_day[day] = total_hours_per_day.get(day, 0) + item["hours"]

    # Detect overload (>5 hours/day)
    overloaded_days = [day for day, hrs in total_hours_per_day.items() if hrs > 5]

    return {
        "overloaded_days": overloaded_days,
        "valid": len(overloaded_days) == 0
    }

# -----------------------------
# TOOL: REFINE SCHEDULE
# -----------------------------
def refine_schedule(schedule):
    log("Tool: Refining schedule...")

    # Push excess work to later days
    new_schedule = []
    day_load = {}

    for item in schedule:
        day = item["day"]
        hours = item["hours"]

        if day_load.get(day, 0) + hours > 5:
            # move to next day
            day += 1

        day_load[day] = day_load.get(day, 0) + hours

        new_schedule.append({
            "task": item["task"],
            "day": day,
            "hours": hours
        })

    return new_schedule

# -----------------------------
# LLM DECISION FUNCTION
# -----------------------------
def decide_action(step):
    log("Using Hugging Face to decide next action...")

    prompt = f"""
You are a planning agent.

Current state:
{json.dumps(state, indent=2)}

Choose ONE action from:
- generate_schedule
- evaluate_schedule
- refine_schedule
- stop

Respond with ONLY the action name.
"""

    if not HF_API_KEY:
        log("HF_API_KEY not set; using fallback decision")
    else:
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json={"inputs": prompt}
            )

            result = response.json()
            text = result[0].get("generated_text", "").lower()

            log(f"HF Raw Output: {text}")

            if "generate" in text:
                return "generate_schedule"
            elif "evaluate" in text:
                return "evaluate_schedule"
            elif "refine" in text:
                return "refine_schedule"
            elif "stop" in text:
                return "stop"

        except Exception as e:
            log(f"HF Error: {e}")

    # 🔁 FALLBACK (VERY IMPORTANT)
    log("Falling back to rule-based decision")

    actions = ["generate_schedule", "evaluate_schedule", "refine_schedule", "stop"]
    return actions[step % len(actions)]

# -----------------------------
# AGENT LOOP
# -----------------------------
def run_agent(tasks):
    state["tasks"] = tasks
    state["schedule"] = []
    state["logs"] = []

    log("Starting agent...")
    log(f"Goal: {state['goal']}")

    for step in range(5):  # multi-step loop
        log(f"\n--- Step {step+1} ---")

        action = decide_action(step)
        log(f"Decision: {action}")

        if action == "generate_schedule":
            state["schedule"] = generate_schedule(state["tasks"])

        elif action == "evaluate_schedule":
            result = evaluate_schedule(state["schedule"], state["tasks"])
            state["evaluation"] = result
            log(f"Evaluation Result: {result}")

        elif action == "refine_schedule":
            state["schedule"] = refine_schedule(state["schedule"])

        elif action == "stop":
            log("Agent decided to stop.")
            break

        else:
            log("Invalid decision, stopping.")
            break

        # --- Reactive behavior: simulate new task ---
        if step == 1:
            new_task = {
                "name": "Surprise Quiz Study",
                "due": 3,
                "estimated_hours": 2
            }
            log("New task detected! Adding to state...")
            state["tasks"].append(new_task)

    log("\nFinal Schedule:")
    for item in state["schedule"]:
        log(str(item))

    return state

# -----------------------------
# MAIN (TEST RUN)
# -----------------------------
if __name__ == "__main__":
    sample_tasks = [
        {"name": "Math Homework", "due": 2, "estimated_hours": 3},
        {"name": "History Essay", "due": 5, "estimated_hours": 4},
        {"name": "Biology Reading", "due": 3, "estimated_hours": 2}
    ]

    run_agent(sample_tasks)