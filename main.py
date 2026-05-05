# main.py
from crewai import Crew, Process
from crew import scout, planner, syncer, task_fetch, task_plan, task_sync

def run():
    print("\n🐴 HOMEWORK-HORSE (CrewAI)\n")

    # Phase 1: Scout + Plan (no sync yet)
    planning_crew = Crew(
        agents=[scout, planner],
        tasks=[task_fetch, task_plan],
        process=Process.sequential,
        verbose=True,
        tracing=True,
    )
    plan_result = planning_crew.kickoff()
    print(f"\n📋 Proposed Plan:\n{plan_result}")

    # Gate: human confirmation
    confirm = input("\n[YOU] Sync to Canvas? (y/n or feedback to regenerate): ").strip().lower()

    if confirm == "y":
        # Phase 2: Sync only
        sync_crew = Crew(
            agents=[syncer],
            tasks=[task_sync],
            process=Process.sequential,
            verbose=True,
            tracing=True,
        )
        # Inject the plan output as context
        task_sync.context = [task_plan]
        sync_result = sync_crew.kickoff()
        print(f"\n✅ {sync_result}")

    elif confirm == "n":
        print("🐴 Session ended. No changes made to your calendar.")

    else:
        # Re-plan with feedback — restart with amended task description
        task_plan.description += f"\n\nUser feedback on prior plan: {confirm}. Adjust accordingly."
        run()  # Recurse with updated context

if __name__ == "__main__":
    run()