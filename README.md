# 🐴 Homework-Horse
> Homework-Horse is a Reasoning Agent that transforms a chaotic list of Canvas assignments into a high-performance study schedule. Homework-Horse is designed to bridge the gap between "I have an assignment" and "When am I actually going to do it?" It respects your sleep, avoids burnout, and writes directly to your Canvas calendar.

## Prerequisites
 
### Canvas Setup
1. Log in to Canvas and go to **Account → Settings**
2. Scroll to **Approved Integrations** and generate a new access token
3. Fill in the required fields and save the token
### Hugging Face Setup
1. Go to `https://huggingface.co/settings/tokens`
2. Create new token
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

* **`agents.py`**: Manages the conversation state, maintains the "memory" of previous planning attempts, and makes final decisions based on tool feedback.
* **`tools.py`**: Contains each of the tools.
* **`evaluation.py`**: Used to validate the agent's logic to ensure reliability and safety.

---

| Tool Name | Capability | Purpose |
| :--- | :--- | :--- |
| **`fetch_canvas_tasks`** | **Observation** | Connects to the Canvas API to retrieve assignment titles and deadlines within a rolling window. |
| **`generate_smart_schedule`** | **Planning** | A heuristic engine that maps tasks to time blocks while respecting sleep windows and "Blackout Dates." |
| **`evaluate_schedule`** | **Criticism** | Analyzes a proposed plan for two failure states: **Burnout** (daily load > 6h) and **Deadline Violations**. |
| **`sync_study_blocks`** | **Action** | Performs a "Surgical Sync." It uses fingerprinting to ensure it only adds or deletes what is necessary, leaving existing events untouched. |

---

## 🔄 The Workflow Loop

```mermaid
    graph TD
    [Start Agent] --> [Fetch Tasks]
    [Fetch Tasks] --> [Generate Initial Plan]
    [Generate Initial Plan] --> [Check Burnout/Deadlines]

    if [Check Burnout/Deadlines] Fails --> [Generate Initial Plan]
    if [Check Burnout/Deadlines] Passes -->[💬 PROPOSE: Show schedule to user]

    if [💬 PROPOSE: Show schedule to user] 'n' --> I[🛑 STOP: Discard Plan]
    if [💬 PROPOSE: Show schedule to user] {User FeedBack} --> [Generate Initial Plan]
    if [💬 PROPOSE: Show schedule to user] 'y' --> {User Confirmation}

    {User Confirmation} -->|'y'| [🔄 SYNC: Surgical Update]
    [🔄 SYNC: Surgical Update] --> [✨ State-Aware Sync Finished]