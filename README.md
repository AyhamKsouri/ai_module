# AI Project Plan Generator

A FastAPI microservice that automatically generates project plans, assigns tasks to team members, and produces Gantt chart data based on project info and team composition.

---

## What it does

Given a project description and a list of team members, this service:

- Generates a list of tasks based on the project methodology and complexity
- Estimates hours per task
- Assigns tasks to the best-suited team member based on skills, experience, and workload
- Resolves task dependencies automatically
- Builds a schedule with start/end days per task
- Returns sprint data (for Agile projects)
- Returns Gantt chart data for visualization

---

## Tech Stack

- **Python**
- **FastAPI**
- **Pydantic**
- **Uvicorn**

---

## Project Structure

```
├── main.py              # FastAPI app, routes, and core logic
├── task_templates.py    # Task templates and skill/hours mapping
├── requirements.txt     # Python dependencies
└── test_main.py         # Tests
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn main:app --reload
```

The service will be available at `http://localhost:8000`

---

## API Reference

### `GET /`

Health check.

**Response:**
```json
{ "status": "AI Module Running" }
```

---

### `POST /generate-plan`

Generates a full project plan.

**Request Body:**
```json
{
  "project": {
    "name": "My App",
    "duration_days": 60,
    "complexity": "medium",
    "methodology": "agile"
  },
  "team_members": [
    {
      "id": 1,
      "name": "Alice",
      "skills": ["python", "fastapi", "postgresql"],
      "experience_level": "senior",
      "weekly_availability_hours": 40
    },
    {
      "id": 2,
      "name": "Bob",
      "skills": ["react", "javascript", "css"],
      "experience_level": "mid",
      "weekly_availability_hours": 35
    }
  ]
}
```

**Fields:**

| Field | Type | Values |
|---|---|---|
| `complexity` | string | `low`, `medium`, `high` |
| `methodology` | string | `agile`, `waterfall`, `kanban` |
| `experience_level` | string | `junior`, `mid`, `senior` |

**Response:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Backend Development",
      "description": "",
      "required_skills": ["python", "fastapi", "postgresql"],
      "estimated_hours": 60.0,
      "assigned_to": 1,
      "start_day": 0,
      "end_day": 8,
      "dependencies": []
    }
  ],
  "sprints": [
    {
      "sprint_number": 1,
      "start_day": 0,
      "end_day": 13,
      "task_ids": [1, 2]
    }
  ],
  "gantt_data": {
    "task_durations": [...],
    "dependencies": [...]
  },
  "warnings": [],
  "error": null
}
```

> `sprints` is only returned for `agile` methodology.

---

## Task Assignment Logic

Tasks are assigned based on a scoring system:

- **+10 points** per matching skill between task requirements and member skills
- **+0/5/10 points** for junior/mid/senior experience level
- **Penalty** for members with high existing workload (to spread work evenly)

Hours are then adjusted per experience level:
- Junior: ×1.4 (takes longer)
- Mid: ×1.0 (baseline)
- Senior: ×0.8 (faster)

---

## Running Tests

```bash
pytest test_main.py
```

---

## Deployment (Render)

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## Interactive Docs

Once running, FastAPI provides automatic docs at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`