# 🐴 Homework-Horse
> An autonomous agent that fetches your Canvas assignments and intelligently schedules your life.

Homework-Horse is a **Reasoning Agent** designed to bridge the gap between "I have an assignment" and "When am I actually going to do it?" It respects your sleep, avoids burnout, and writes directly to your Canvas calendar.

## 🛠 Project Architecture
The agent is split into modular components to handle different stages of the cognitive loop:

* **`agents.py`**: The Controller (The "Body"). It handles environment interaction (Canvas API).
* **`tools.py`**: The Scheduler (The "Brain"). It contains the logic for time-blocking and sleep jumps.
* **`evaluation.py`**: The Critic (The "Conscience"). It checks the plan for safety and deadlines.

---

## 🔄 The Workflow Loop

```mermaid
    A[Start Agent] --> B[🔍 OBSERVE]
    B -->|Fetch Assignments| C[🧠 PLAN]
    C -->|Generate Schedule| D[⚖️ EVALUATE]
    D -->|Check Safety/Deadlines| E{User Approval}
    E -->|Approved| F[🚀 ACT]
    E -->|Rejected| G[🛑 STOP]
    F -->|Write to Canvas| H[✨ Finished]