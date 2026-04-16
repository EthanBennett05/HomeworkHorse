import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from canvasapi import Canvas
import pytz # Standard for handling timezones

# --- IMPORT WORKFLOW TOOLS ---
from tools import generate_smart_schedule 
from evaluation import evaluate_schedule

load_dotenv()

class HomeworkHorse:
    def __init__(self):
        self.url = os.getenv("CANVAS_API_URL")
        self.key = os.getenv("CANVAS_API_KEY")
        self.lookahead_days = 7  # 📅 Hard limit for the agent
        
        if not self.url or not self.key:
            raise ValueError("Environment variables not found.")

        self.canvas = Canvas(self.url, self.key)
        self.user = self.canvas.get_current_user()

    def log(self, stage, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🐴 {stage.upper()}: {message}")

    def run(self):
        print("\n" + "="*50 + "\n   HOMEWORK-HORSE AGENT: HARD-FILTER MODE\n" + "="*50)

        # STEP 1: OBSERVE
        self.log("Observe", "Fetching course contexts...")
        courses = self.user.get_courses(enrollment_state='active')
        context_codes = [f"course_{c.id}" for c in courses]
        context_codes.append(f"user_{self.user.id}")

        now = datetime.now(pytz.utc)
        horizon = now + timedelta(days=self.lookahead_days)

        self.log("Observe", f"Scanning for assignments due by {horizon.strftime('%m/%d')}...")
        
        raw_items = self.canvas.get_calendar_events(
            type="assignment", 
            context_codes=context_codes,
            all_events=True
        )
        
        tasks = []
        for i in raw_items:
            if hasattr(i, 'end_at') and i.end_at:
                # Parse the Canvas date string into a Python datetime object
                due_dt = datetime.strptime(i.end_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                
                # 🛡️ THE HARD FILTER: Only keep if due date is between NOW and HORIZON
                if now <= due_dt <= horizon:
                    tasks.append({"name": i.title, "due": i.end_at})
                else:
                    # Optional: uncomment to see what's being ignored
                    # print(f"DEBUG: Ignoring {i.title} (Due {due_dt.strftime('%m/%d')})")
                    pass

        if not tasks:
            self.log("End", f"Filtered out all distant tasks. Nothing due in the next {self.lookahead_days} days!")
            return

        self.log("Observe", f"Gathered {len(tasks)} tasks after applying the 7-day filter.")

        # --- REST OF THE WORKFLOW (Same as before) ---
        self.log("Tool Call", "Generating Smart Schedule...")
        final_schedule = generate_smart_schedule(tasks)

        self.log("Evaluate", "Checking plan quality...")
        report = evaluate_schedule(final_schedule, tasks)
        if not report["valid"]:
            for w in report["warnings"]: print(f"   ⚠️  {w}")

        print("\nPROPOSED STUDY BLOCKS:")
        for block in final_schedule:
            print(f"  - {block['start'].strftime('%a %I:%M %p')}: {block['task']}")
        
        confirm = input("\n[?] Push these to your Canvas Calendar? (y/n): ")
        if confirm.lower() == 'y':
            for block in final_schedule:
                self.deploy(block)
            self.log("End", "Success!")

    def deploy(self, block):
        self.canvas.create_calendar_event(calendar_event={
            "context_code": f"user_{self.user.id}",
            "title": f"📚 HW-HORSE: {block['task']}",
            "start_at": block['start'].isoformat(),
            "end_at": block['end'].isoformat()
        })

if __name__ == "__main__":
    agent = HomeworkHorse()
    agent.run()