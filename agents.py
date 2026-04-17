import os
import json
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from canvasapi import Canvas
from huggingface_hub import InferenceClient
from tools import TOOL_SCHEMAS, run_tool

load_dotenv()

SYSTEM_PROMPT = """
You are HomeworkHorse, a sophisticated autonomous study agent for a university student. Your goal is to manage a dynamic, burnout-proof study schedule using the Canvas API.

## YOUR CORE WORKFLOW
1.  OBSERVE: Analyze the task list provided by the user. Note deadlines and estimated effort.
2.  PLAN: Call 'generate_smart_schedule' to create an initial timeline.
3.  EVALUATE: Call 'evaluate_schedule' on your plan. 
    - If 'valid' is false (Burnout or Deadline Miss), RE-REASON. Adjust parameters like 'blackout_dates' or 'sleep_start' and call 'generate_smart_schedule' again. 
    - You may attempt to fix the schedule up to 2 times.
4.  PROPOSE: Present the final, best-possible schedule to the user. Clearly highlight any unavoidable tradeoffs (e.g., "I had to schedule 7 hours today because the assignment is due tomorrow").
5.  SYNC: Ask the user: "Shall I sync this plan to your Canvas calendar? (y/n)". 
    - ONLY if the user says 'y', call 'sync_study_blocks'.

## TOOL RULES
- 'sync_study_blocks': This is your primary deployment tool. It is "State-Aware"—it automatically deletes old '📚 HW-HORSE' blocks and adds only new ones.
- **Atomic Planning:** Always generate before evaluating.
- **No Ghost Blocks:** Never deploy a schedule that misses a deadline without explicit user acknowledgment of the failure.
- **Batching:** Always pass the full array of blocks to the sync tool.

## PERSONALITY & ETHICS
- You are a helpful, grounded peer. 
- Prioritize sleep and mental health unless a deadline makes it impossible. 
- If a student is objectively overloaded, tell them honestly.

## FORMATTING RULES
- When presenting the schedule to the user, use a "Friendly Calendar" format.
- Dates MUST include the day of the week, like this: "- **Wednesday, April 19th:**"
- Times MUST use 12-hour AM/PM format, like this: "08:00 AM - 10:00 AM" or "01:30 PM - 03:30 PM".
- Ensure there is a 30-minute gap displayed between sessions as a "Break".
"""

class HomeworkHorse:
    def __init__(self):
        load_dotenv() # Ensure env is loaded first
        self.url = os.getenv("CANVAS_API_URL")
        self.key = os.getenv("CANVAS_API_KEY")
        self.hf_token = os.getenv("HF_API_KEY") # Get the token

        if not self.url or not self.key or not self.hf_token:
            raise ValueError("Missing CANVAS_API_URL, CANVAS_API_KEY, or HF_API_KEY in .env")

        self.canvas = Canvas(self.url, self.key)
        self.user = self.canvas.get_current_user()
        
        # Pass the token explicitly here
        self.client = InferenceClient(
            model="Qwen/Qwen2.5-72B-Instruct",
            token=self.hf_token 
        )

    def fetch_tasks(self):
        courses = self.user.get_courses(enrollment_state="active")
        codes = [f"course_{c.id}" for c in courses] + [f"user_{self.user.id}"]
        now = datetime.now(pytz.utc)
        horizon = now + timedelta(days=7)
        
        events = self.canvas.get_calendar_events(type="assignment", context_codes=codes, all_events=True)
        tasks = []
        for e in events:
            if hasattr(e, "end_at") and e.end_at:
                due = datetime.strptime(e.end_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                if now <= due <= horizon:
                    tasks.append({"name": e.title, "due": e.end_at})
        return tasks

    def run(self):
        print("\n🐴 HOMEWORK-HORSE")

        current_day_info = datetime.now().strftime("%A, %B %d, %Y")
        tasks = self.fetch_tasks()
        if not tasks:
            print("No tasks found!")
            return


        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Today is {current_day_info}. Tasks: {json.dumps(tasks)}. Plan my week."}
        ]
        
        context = {"canvas": self.canvas, "user_id": self.user.id}

        while True:
            # AI Inference
            response = self.client.chat_completion(
                messages=messages,
                tools=[{"type": "function", "function": s} for s in TOOL_SCHEMAS],
                max_tokens=1500
            )

            msg = response.choices[0].message
            messages.append(msg)

            if msg.content:
                print(f"\n🤖 {msg.content}")

                if "Would you like to procede" in msg.content or "?" in msg.content:
                    user_final = input("\n[USER]: ").strip().lower()
                    if user_final == 'y':
                        # This tells the AI the user said yes so it can call 'deploy_to_canvas'
                        messages.append({"role": "user", "content": "Yes, please deploy the schedule now."})
                        continue # Go back to the loop so the AI can call the deploy tool
                    else:
                        print("🐴 End: Deployment cancelled.")
                        break

            if not msg.tool_calls:
                break

            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = tool_call.function.arguments

                if isinstance(args, str):
                    args = json.loads(args)
                else:
                    args = args
                
                print(f"[ACTION] AI calling {name}...")

                if name == "deploy_to_canvas":
                    ans = input(f"   Confirm {args.get('task')}? (y/n): ")
                    result = run_tool(name, args, context) if ans == 'y' else {"status": "denied"}
                else:
                    result = run_tool(name, args, context)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

if __name__ == "__main__":
    HomeworkHorse().run()