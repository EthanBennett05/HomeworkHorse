import os
import json
from datetime import datetime
from dotenv import load_dotenv
from canvasapi import Canvas
from huggingface_hub import InferenceClient
from tools import TOOL_SCHEMAS, run_tool

load_dotenv()

SYSTEM_PROMPT = """
You are HomeworkHorse, a sophisticated autonomous study agent. 

## YOUR CORE WORKFLOW
1. OBSERVE: Use 'fetch_canvas_tasks' to see what assignments are due.
2. PLAN/EVALUATE: Call 'generate_smart_schedule' then 'evaluate_schedule'. 
   - If evaluation returns valid: false, adjust parameters and retry (max 2 times).
3. PROPOSE: Present the final plan in a Friendly Calendar format.
   - Use day names: "- **Tuesday, April 21st:**"
   - Use 12-hour AM/PM: "02:00 PM - 04:00 PM".
4. SYNC: Ask "Shall I sync this plan to your Canvas calendar? (y/n)".
   - Only call 'sync_study_blocks' if user confirms with 'y'.

## TOOL RULES
- 'sync_study_blocks' is state-aware. It handles deletions and additions automatically. 
- Do not call sync until the user confirms.
"""

class HomeworkHorse:
    def __init__(self):
        # Validate Env
        url = os.getenv("CANVAS_API_URL")
        key = os.getenv("CANVAS_API_KEY")
        hf_key = os.getenv("HF_API_KEY")
        
        if not all([url, key, hf_key]):
            raise ValueError("Missing environment variables in .env file.")

        self.canvas = Canvas(url, key)
        self.user = self.canvas.get_current_user()
        self.client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=hf_key)

    def run(self):
        print("\n🐴 HOMEWORK-HORSE")
        current_time_str = datetime.now().strftime("%A, %B %d, %Y")
        
        # Start the conversation
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Today is {current_time_str}. Please fetch my tasks for the next 7 days and plan my schedule."}
        ]
        
        context = {"canvas": self.canvas, "user": self.user, "user_id": self.user.id}

        while True:
            response = self.client.chat_completion(
                messages=messages,
                tools=[{"type": "function", "function": s} for s in TOOL_SCHEMAS],
                max_tokens=1500
            )

            msg = response.choices[0].message
            messages.append(msg)

            # Handle Text Response
            if msg.content:
                print(f"\n🤖 {msg.content}")
                if "sync this plan" in msg.content.lower() or "y/n" in msg.content.lower() or "?" in msg.content:
                    user_feedback = input("\n[USER] (y = Sync / n = Stop / or provide feedback to regenerate): ").strip()
                    if user_feedback == 'y':
                        messages.append({"role": "user", "content": "Confirmed. Please sync the blocks now."})
                        continue
                    elif user_feedback.lower() == 'n':
                        print("🐴 Session ended by user.")
                        break
                    else:
                        # This is the "Force New Schedule" path
                        print(f"🔄 Feedback received: '{user_feedback}'. Regenerating...")
                        messages.append({
                            "role": "user", 
                            "content": f"I don't like that plan. Please create a new one with this feedback: {user_feedback}"
                        })
                        continue

            # Handle Tool Calls
            if not msg.tool_calls:
                break

            for tc in msg.tool_calls:
                t_name = tc.function.name
                t_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                
                print(f"[ACTION] AI calling {t_name}...")
                result = run_tool(t_name, t_args, context)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)
                })

if __name__ == "__main__":
    HomeworkHorse().run()