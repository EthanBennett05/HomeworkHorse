# 🐴 Homework-Horse
> An autonomous agent that fetches your Canvas assignments and intelligently schedules your life.

Homework-Horse is a **Reasoning Agent** designed to bridge the gap between "I have an assignment" and "When am I actually going to do it?" It respects your sleep, avoids burnout, and writes directly to your Canvas calendar.

## Prerequisites
 
### Canvas Setup
1. Log in to Canvas and go to **Account → Settings**
2. Scroll to **Approved Integrations** and generate a new access token
3. Fill in the required fields and save the token
### VS Code Setup
Ensure Python is installed, then run the following in your terminal:
```bash
pip install canvasapi python-dotenv huggingface_hub
```
 
---
 
## Running the App
 
Execute the agent with:
```bash
python3 agents.py
```
 
Once complete, check your **Canvas Calendar** to review the changes.




## 🛠 Project Architecture
The agent is split into modular components to handle different stages of the cognitive loop:

* **`agents.py`**: The Controller (The "Body"). It handles environment interaction (Canvas API).
* **`tools.py`**: The Scheduler (The "Brain"). It contains the logic for time-blocking and sleep jumps.
* **`evaluation.py`**: The Critic (The "Conscience"). It checks the plan for safety and deadlines.

---

## 🔄 The Workflow Loop

```mermaid
    graph TD
    A[Start Agent] --> B[🔍 OBSERVE: Fetch Tasks]
    B --> C[🧠 PLAN: Generate Initial Blocks]
    C --> D[⚖️ EVALUATE: Check Burnout/Deadlines]
    D -->|Fail: Burnout/Miss| C
    D -->|Pass/Best Effort| E[💬 PROPOSE: Show formatted AM/PM schedule]
    E --> F{User Confirmation}
    F -->|'y'| G[🔄 SYNC: Surgical Update]
    G --> H[✨ State-Aware Sync Finished]
    F -->|'n'| I[🛑 STOP: Discard Plan]

    subgraph "The Cognitive Loop"
    C
    D
    end

    subgraph "Surgical Sync Logic"
    G --> G1[Compare Fingerprints]
    G1 --> G2[Delete Old / Add New / Keep Intact]
    end