from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import math
from datetime import datetime, timedelta
from task_templates import TASK_TEMPLATES, TASK_SKILL_MAP

app = FastAPI()


# ---------- Input Structures ----------
class TeamMember(BaseModel):
    id: int
    name: str
    skills: List[str]
    experience_level: Literal["junior", "mid", "senior"]
    weekly_availability_hours: int


class ProjectInfo(BaseModel):
    name: str
    duration_days: int
    complexity: Literal["low", "medium", "high"]
    methodology: Literal["agile", "waterfall", "kanban"]


class PlanRequest(BaseModel):
    project: ProjectInfo
    team_members: List[TeamMember]


# ---------- Output Structures ----------
class Task(BaseModel):
    tempId: str
    title: str
    description: Optional[str] = ""
    assignedToUserId: Optional[int] = None
    estimatedHours: float
    startDate: str  # ISO date string
    dueDate: str    # ISO date string
    dependencies: List[str] = Field(default_factory=list)
    status: str = "todo"
    
    # Internal fields for scheduling logic (not part of backend response if excluded)
    required_skills: List[str] = Field(default_factory=list, exclude=True)
    start_day: int = Field(default=0, exclude=True)
    end_day: int = Field(default=0, exclude=True)


class Sprint(BaseModel):
    sprint_number: int
    start_day: int
    end_day: int
    task_ids: List[str]  # Updated to use tempId


class GanttData(BaseModel):
    task_durations: List[dict]  # [{tempId, title, start_day, end_day, assignedToUserId}]
    dependencies: List[dict]    # [{from, to}] (using tempId)


class GeneratePlanResponse(BaseModel):
    tasks: List[Task]
    sprints: Optional[List[Sprint]] = None
    gantt_data: Optional[GanttData] = None
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


@app.get("/")
def root():
    return {"status": "AI Module Running"}


# ---------- Helper Functions ----------

def days_to_iso(days: int) -> str:
    """Converts a day number (starting from 0 for today) to an ISO date string."""
    base_date = datetime.now()
    target_date = base_date + timedelta(days=days)
    return target_date.date().isoformat()


def generate_task_titles(methodology: str, complexity: str) -> List[str]:
    templates = TASK_TEMPLATES.get(methodology, {})
    return templates.get(complexity, ["Default Task 1", "Default Task 2"])


def estimate_hours_and_skills(title: str, complexity: str):

    task = TASK_SKILL_MAP.get(title)

    if not task:
        return 20, ["general"]

    hours = task["base_hours"]
    skills = task["skills"]

    multiplier = {
        "low": 0.7,
        "medium": 1,
        "high": 1.6
    }

    hours = hours * multiplier.get(complexity, 1)

    return hours, skills


def calculate_match_score(task_skills: List[str], member: TeamMember, member_available: dict) -> float:
    score = 0.0
    # 10 points for each matching skill
    for skill in task_skills:
        if skill in member.skills:
            score += 10

    # Experience bonus
    exp_bonus = {"junior": 0, "mid": 5, "senior": 10}
    score += exp_bonus[member.experience_level]

    # Penalize busy members slightly to spread work
    score -= member_available.get(member.id, 0) * 0.1

    return score


def adjust_hours_for_experience(hours: float, member: TeamMember) -> float:
    factor = {"junior": 1.4, "mid": 1.0, "senior": 0.8}
    return hours * factor[member.experience_level]


def assign_best_member(task_skills: List[str], members: List[TeamMember], member_available: dict) -> tuple[int, Optional[str]]:
    best_member = None
    best_score = -1000
    best_skill_matches = 0

    for member in members:
        skill_matches = sum(1 for s in task_skills if s in member.skills)
        score = calculate_match_score(task_skills, member, member_available)
        if score > best_score:
            best_score = score
            best_skill_matches = skill_matches
            best_member = member

    if not best_member:
        raise ValueError(f"No team members provided to assign tasks.")

    # ⚠️ Warn but don't fail — assign best available person
    warning = None
    if best_skill_matches == 0:
        warning = f"Warning: No perfect match for skills {task_skills}, assigned {best_member.name} as best available"

    return best_member.id, warning


def resolve_dependencies(tasks: List[Task]) -> List[Task]:
    # Group by primary skill domain
    backend_skills = {"python", "fastapi", "postgresql", "sql", "api", "rest_api", "security"}
    frontend_skills = {"javascript", "react", "css"}
    devops_skills = {"docker", "devops"}

    def get_group(task):
        for skill in task.required_skills:
            if skill in backend_skills: return "backend"
            if skill in frontend_skills: return "frontend"
            if skill in devops_skills: return "devops"
        return "general"

    groups: dict = {}
    for task in tasks:
        g = get_group(task)
        groups.setdefault(g, []).append(task)

    # Chain dependencies only within each group
    for group_tasks in groups.values():
        for i in range(1, len(group_tasks)):
            group_tasks[i].dependencies.append(group_tasks[i - 1].tempId)

    # ✅ Make "general" group tasks (like testing) start after all other groups finish
    general_tasks = groups.get("general", [])
    all_other_tasks = [t for t in tasks if t not in general_tasks]
    if all_other_tasks and general_tasks:
        # Make the first general task depend on ALL non-general tasks
        # This ensures it doesn't start until every core task is finished
        for non_general_task in all_other_tasks:
            if non_general_task.tempId not in general_tasks[0].dependencies:
                general_tasks[0].dependencies.append(non_general_task.tempId)

    return tasks


def get_daily_hours(member: TeamMember) -> float:
    return member.weekly_availability_hours / 5  # assuming 5-day work week


def topological_sort(tasks: List[Task]) -> List[Task]:
    task_map = {t.tempId: t for t in tasks}
    visited = set()
    result = []

    def visit(task):
        if task.tempId in visited:
            return
        for dep_id in task.dependencies:
            visit(task_map[dep_id])
        visited.add(task.tempId)
        result.append(task)

    for task in tasks:
        visit(task)

    return result


def build_schedule(tasks: List[Task], members: List[TeamMember]) -> List[str]:
    member_map = {m.id: m for m in members}
    member_available = {m.id: 0 for m in members}
    # Proper topological sort for complex dependency chains
    sorted_tasks = topological_sort(tasks)
    warnings = []

    for task in sorted_tasks:
        # ✅ Assign best member at scheduling time to account for workload
        assignee_id, warning = assign_best_member(task.required_skills, members, member_available)
        
        if warning:
            warnings.append(f"Task {task.tempId} ('{task.title}'): {warning}")
            
        task.assignedToUserId = assignee_id
        
        # ✅ Adjust hours for experience now that we have the assignee
        member = member_map[assignee_id]
        task.estimatedHours = adjust_hours_for_experience(task.estimatedHours, member)

        dep_end = max(
            (next(t for t in tasks if t.tempId == dep_id).end_day for dep_id in task.dependencies),
            default=0
        )
        daily_hours = get_daily_hours(member)
        start = max(dep_end, member_available[assignee_id])
        duration_days = math.ceil(task.estimatedHours / daily_hours)  # ✅ realistic
        end = start + duration_days

        task.start_day = int(start)
        task.end_day = int(end)
        task.startDate = days_to_iso(task.start_day)
        task.dueDate = days_to_iso(task.end_day)
        member_available[assignee_id] = end
    
    return warnings


def build_sprints(tasks: List[Task], sprint_length_days: int = 14) -> List[Sprint]:
    if not tasks:
        return []
    sprints = []
    min_day = min(t.start_day for t in tasks)
    max_day = max(t.end_day for t in tasks)

    current_sprint = 1
    sprint_start = min_day
    while sprint_start <= max_day:
        sprint_end = sprint_start + sprint_length_days - 1
        task_ids = [t.tempId for t in tasks if t.start_day <= sprint_end and t.end_day >= sprint_start]
        if task_ids:
            sprints.append(Sprint(
                sprint_number=current_sprint,
                start_day=sprint_start,
                end_day=sprint_end,
                task_ids=task_ids
            ))
        sprint_start += sprint_length_days
        current_sprint += 1
    return sprints


def build_gantt_data(tasks: List[Task]) -> GanttData:
    durations = [
        {"tempId": t.tempId, "title": t.title, "start_day": t.start_day,
         "end_day": t.end_day, "assignedToUserId": t.assignedToUserId}
        for t in tasks
    ]
    deps = [
        {"from": dep_id, "to": t.tempId}
        for t in tasks for dep_id in t.dependencies
    ]
    return GanttData(task_durations=durations, dependencies=deps)


# ---------- Core Logic ----------

@app.post("/generate", response_model=GeneratePlanResponse)
def generate_plan(request: PlanRequest):
    try:
        titles = generate_task_titles(
            request.project.methodology,
            request.project.complexity
        )

        tasks = []
        task_counter = 1

        for title in titles:
            hours, skills = estimate_hours_and_skills(title, request.project.complexity)

            task = Task(
                tempId=f"task{task_counter}",
                title=title,
                required_skills=skills,
                estimatedHours=hours,
                startDate="", # Will be set in build_schedule
                dueDate="",   # Will be set in build_schedule
                assignedToUserId=None,
                start_day=0,
                end_day=0
            )
            tasks.append(task)
            task_counter += 1

        tasks = resolve_dependencies(tasks)        
        warnings = build_schedule(tasks, request.team_members) 

        sprints = None
        if request.project.methodology == "agile":
            sprints = build_sprints(tasks)          

        gantt_data = build_gantt_data(tasks)        

        return GeneratePlanResponse(
            tasks=tasks, 
            sprints=sprints, 
            gantt_data=gantt_data,
            warnings=warnings
        )

    except ValueError as e:
        return GeneratePlanResponse(tasks=[], error=str(e))