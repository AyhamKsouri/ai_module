import pytest
from main import (
    app,
    TeamMember,
    Task,
    generate_task_titles,
    estimate_hours_and_skills,
    calculate_match_score,
    adjust_hours_for_experience,
    assign_best_member,
    resolve_dependencies,
    topological_sort,
    build_schedule,
    build_sprints,
    build_gantt_data,
)
from fastapi.testclient import TestClient
from pydantic import Field
from typing import List
import math

client = TestClient(app)


# ============================================================
# HELPERS — reusable test data
# ============================================================

def make_member(id, name, skills, level="mid", hours=40):
    return TeamMember(id=id, name=name, skills=skills,
                      experience_level=level, weekly_availability_hours=hours)

def make_task(id, title, skills, est_hours=20, deps=None):
    from pydantic import Field
    return Task(
        id=id, title=title, required_skills=skills,
        estimated_hours=est_hours, start_day=0, end_day=0,
        dependencies=deps or []
    )

ALICE = make_member(1, "Alice", ["python", "fastapi", "postgresql", "testing"], "senior", 30)
BOB   = make_member(2, "Bob",   ["react", "javascript", "css"], "mid", 35)


# ============================================================
# 1. UNIT TESTS — generate_task_titles
# ============================================================

class TestGenerateTaskTitles:

    def test_agile_medium_returns_correct_titles(self):
        titles = generate_task_titles("agile", "medium")
        assert "Epic: User Management" in titles
        assert "Frontend Development" in titles

    def test_waterfall_low_returns_phases(self):
        titles = generate_task_titles("waterfall", "low")
        assert titles == ["Requirements", "Design", "Development", "Testing", "Deployment"]

    def test_kanban_high_returns_titles(self):
        titles = generate_task_titles("kanban", "high")
        assert "Backend Development" in titles
        assert "Deployment" in titles

    def test_unknown_methodology_returns_defaults(self):
        titles = generate_task_titles("unknown", "medium")
        assert titles == ["Default Task 1", "Default Task 2"]

    def test_unknown_complexity_returns_defaults(self):
        titles = generate_task_titles("agile", "ultra")
        assert titles == ["Default Task 1", "Default Task 2"]


# ============================================================
# 2. UNIT TESTS — estimate_hours_and_skills
# ============================================================

class TestEstimateHoursAndSkills:

    def test_backend_development_medium(self):
        hours, skills = estimate_hours_and_skills("Backend Development", "medium")
        assert hours == 60          # base_hours=60, multiplier=1.0
        assert "python" in skills

    def test_backend_development_high_multiplier(self):
        hours, skills = estimate_hours_and_skills("Backend Development", "high")
        assert hours == pytest.approx(96.0)   # 60 * 1.6

    def test_backend_development_low_multiplier(self):
        hours, skills = estimate_hours_and_skills("Backend Development", "low")
        assert hours == pytest.approx(42.0)   # 60 * 0.7

    def test_unknown_title_returns_defaults(self):
        hours, skills = estimate_hours_and_skills("Some Random Task", "medium")
        assert hours == 20
        assert skills == ["general"]

    def test_frontend_skills_correct(self):
        _, skills = estimate_hours_and_skills("Frontend Development", "medium")
        assert "javascript" in skills
        assert "react" in skills
        assert "css" in skills


# ============================================================
# 3. UNIT TESTS — calculate_match_score
# ============================================================

class TestCalculateMatchScore:

    def test_perfect_skill_match_scores_higher(self):
        member_available = {1: 0}
        score = calculate_match_score(["python", "fastapi"], ALICE, member_available)
        # 2 skills * 10 + senior bonus 10 = 30
        assert score == 30.0

    def test_no_skill_match_still_gets_experience_bonus(self):
        member_available = {1: 0}
        score = calculate_match_score(["react"], ALICE, member_available)
        # 0 skill matches + senior bonus 10
        assert score == 10.0

    def test_busy_member_gets_penalized(self):
        member_available = {1: 100}   # very busy
        score_busy = calculate_match_score(["python"], ALICE, member_available)
        member_available_free = {1: 0}
        score_free = calculate_match_score(["python"], ALICE, member_available_free)
        assert score_free > score_busy

    def test_junior_scores_lower_than_senior_same_skills(self):
        junior = make_member(3, "Carlos", ["python"], "junior", 40)
        senior = make_member(4, "Diana", ["python"], "senior", 40)
        available = {3: 0, 4: 0}
        assert calculate_match_score(["python"], senior, available) > \
               calculate_match_score(["python"], junior, available)


# ============================================================
# 4. UNIT TESTS — adjust_hours_for_experience
# ============================================================

class TestAdjustHoursForExperience:

    def test_senior_reduces_hours(self):
        senior = make_member(1, "Alice", [], "senior")
        assert adjust_hours_for_experience(100, senior) == pytest.approx(80.0)

    def test_mid_keeps_hours_same(self):
        mid = make_member(1, "Bob", [], "mid")
        assert adjust_hours_for_experience(100, mid) == pytest.approx(100.0)

    def test_junior_increases_hours(self):
        junior = make_member(1, "Carlos", [], "junior")
        assert adjust_hours_for_experience(100, junior) == pytest.approx(140.0)

    def test_senior_always_less_than_junior_same_base(self):
        senior = make_member(1, "A", [], "senior")
        junior = make_member(2, "B", [], "junior")
        assert adjust_hours_for_experience(50, senior) < adjust_hours_for_experience(50, junior)


# ============================================================
# 5. UNIT TESTS — assign_best_member
# ============================================================

class TestAssignBestMember:

    def test_assigns_member_with_matching_skills(self):
        available = {1: 0, 2: 0}
        member_id, warning = assign_best_member(["python", "fastapi"], [ALICE, BOB], available)
        assert member_id == ALICE.id    # Alice has python+fastapi, Bob doesn't
        assert warning is None

    def test_assigns_member_with_frontend_skills(self):
        available = {1: 0, 2: 0}
        member_id, warning = assign_best_member(["react", "javascript"], [ALICE, BOB], available)
        assert member_id == BOB.id      # Bob has react+javascript

    def test_warns_when_no_skill_match(self):
        available = {1: 0, 2: 0}
        member_id, warning = assign_best_member(["cobol", "fortran"], [ALICE, BOB], available)
        assert warning is not None
        assert "No perfect match" in warning

    def test_raises_when_no_members(self):
        with pytest.raises(ValueError):
            assign_best_member(["python"], [], {})

    def test_prefers_less_busy_member_when_skills_equal(self):
        # Both members have "testing", Alice is busy (available day 50), Bob is free
        alice = make_member(1, "Alice", ["testing"], "mid", 40)
        bob   = make_member(2, "Bob",   ["testing"], "mid", 40)
        available = {1: 50, 2: 0}   # Alice is busy
        member_id, _ = assign_best_member(["testing"], [alice, bob], available)
        assert member_id == bob.id


# ============================================================
# 6. UNIT TESTS — resolve_dependencies
# ============================================================

class TestResolveDependencies:

    def test_backend_tasks_chained(self):
        t1 = make_task(1, "Backend Development", ["python", "fastapi"])
        t2 = make_task(2, "API Integration", ["python", "rest_api"])
        tasks = resolve_dependencies([t1, t2])
        # t2 should depend on t1 (both backend)
        assert 1 in t2.dependencies

    def test_frontend_and_backend_run_in_parallel(self):
        t1 = make_task(1, "Backend Development", ["python"])
        t2 = make_task(2, "Frontend Development", ["javascript", "react"])
        tasks = resolve_dependencies([t1, t2])
        # Different groups — no cross dependencies
        assert 1 not in t2.dependencies
        assert 2 not in t1.dependencies

    def test_general_tasks_depend_on_all_others(self):
        t1 = make_task(1, "Backend Development", ["python"])
        t2 = make_task(2, "Frontend Development", ["javascript"])
        t3 = make_task(3, "Integration Testing", ["testing"])  # general group
        tasks = resolve_dependencies([t1, t2, t3])
        # t3 must depend on both t1 and t2
        assert 1 in t3.dependencies
        assert 2 in t3.dependencies

    def test_no_duplicate_dependencies(self):
        t1 = make_task(1, "Backend Development", ["python"])
        t2 = make_task(2, "Integration Testing", ["testing"])
        tasks = resolve_dependencies([t1, t2])
        assert len(t2.dependencies) == len(set(t2.dependencies))


# ============================================================
# 7. UNIT TESTS — topological_sort
# ============================================================

class TestTopologicalSort:

    def test_task_with_no_deps_comes_first(self):
        t1 = make_task(1, "Task A", ["python"])
        t2 = make_task(2, "Task B", ["python"], deps=[1])
        result = topological_sort([t1, t2])
        assert result.index(t1) < result.index(t2)

    def test_chain_of_three_sorted_correctly(self):
        t1 = make_task(1, "A", ["python"])
        t2 = make_task(2, "B", ["python"], deps=[1])
        t3 = make_task(3, "C", ["python"], deps=[2])
        result = topological_sort([t1, t2, t3])
        ids = [t.id for t in result]
        assert ids.index(1) < ids.index(2) < ids.index(3)

    def test_parallel_tasks_both_appear(self):
        t1 = make_task(1, "Backend", ["python"])
        t2 = make_task(2, "Frontend", ["javascript"])
        result = topological_sort([t1, t2])
        assert len(result) == 2


# ============================================================
# 8. UNIT TESTS — build_schedule
# ============================================================

class TestBuildSchedule:

    def test_all_tasks_get_assigned(self):
        t1 = make_task(1, "Backend Development", ["python", "fastapi"])
        t2 = make_task(2, "Frontend Development", ["javascript", "react"])
        build_schedule([t1, t2], [ALICE, BOB])
        assert t1.assigned_to is not None
        assert t2.assigned_to is not None

    def test_start_and_end_days_not_zero_after_schedule(self):
        t1 = make_task(1, "Backend Development", ["python"], est_hours=40)
        build_schedule([t1], [ALICE])
        assert t1.end_day > t1.start_day

    def test_dependent_task_starts_after_dependency_ends(self):
        t1 = make_task(1, "Backend Development", ["python"], est_hours=40)
        t2 = make_task(2, "Integration Testing", ["testing"], est_hours=20, deps=[1])
        build_schedule([t1, t2], [ALICE])
        assert t2.start_day >= t1.end_day

    def test_returns_warnings_list(self):
        t1 = make_task(1, "Backend Development", ["python"])
        warnings = build_schedule([t1], [ALICE])
        assert isinstance(warnings, list)

    def test_warning_generated_for_missing_skill(self):
        t1 = make_task(1, "Some Task", ["cobol"])   # nobody has cobol
        warnings = build_schedule([t1], [ALICE, BOB])
        assert len(warnings) == 1
        assert "No perfect match" in warnings[0]

    def test_experience_affects_estimated_hours(self):
        # Senior should end up with fewer hours than junior for same task
        senior = make_member(1, "Senior Dev", ["python"], "senior", 40)
        junior = make_member(2, "Junior Dev", ["python"], "junior", 40)

        t_senior = make_task(1, "Backend Development", ["python"], est_hours=60)
        t_junior = make_task(1, "Backend Development", ["python"], est_hours=60)

        build_schedule([t_senior], [senior])
        build_schedule([t_junior], [junior])

        assert t_senior.estimated_hours < t_junior.estimated_hours


# ============================================================
# 9. UNIT TESTS — build_sprints
# ============================================================

class TestBuildSprints:

    def test_returns_empty_list_for_no_tasks(self):
        assert build_sprints([]) == []

    def test_sprints_are_14_days_long(self):
        t1 = make_task(1, "A", ["python"])
        t1.start_day = 0
        t1.end_day = 30
        sprints = build_sprints([t1])
        for sprint in sprints:
            assert (sprint.end_day - sprint.start_day) == 13   # 14 days inclusive

    def test_task_appears_in_correct_sprint(self):
        t1 = make_task(1, "A", ["python"])
        t1.start_day = 0
        t1.end_day = 5
        sprints = build_sprints([t1])
        assert t1.id in sprints[0].task_ids

    def test_sprint_numbers_are_sequential(self):
        t1 = make_task(1, "A", ["python"])
        t1.start_day = 0
        t1.end_day = 40
        sprints = build_sprints([t1])
        for i, sprint in enumerate(sprints):
            assert sprint.sprint_number == i + 1


# ============================================================
# 10. UNIT TESTS — build_gantt_data
# ============================================================

class TestBuildGanttData:

    def test_gantt_has_entry_for_every_task(self):
        t1 = make_task(1, "A", ["python"])
        t1.start_day = 0; t1.end_day = 5; t1.assigned_to = 1
        t2 = make_task(2, "B", ["javascript"])
        t2.start_day = 0; t2.end_day = 8; t2.assigned_to = 2
        gantt = build_gantt_data([t1, t2])
        assert len(gantt.task_durations) == 2

    def test_gantt_dependencies_recorded_correctly(self):
        t1 = make_task(1, "A", ["python"])
        t1.start_day = 0; t1.end_day = 5; t1.assigned_to = 1
        t2 = make_task(2, "B", ["python"], deps=[1])
        t2.start_day = 5; t2.end_day = 10; t2.assigned_to = 1
        gantt = build_gantt_data([t1, t2])
        assert {"from": 1, "to": 2} in gantt.dependencies

    def test_gantt_duration_fields_present(self):
        t1 = make_task(1, "A", ["python"])
        t1.start_day = 0; t1.end_day = 5; t1.assigned_to = 1
        gantt = build_gantt_data([t1])
        entry = gantt.task_durations[0]
        assert "start_day" in entry
        assert "end_day" in entry
        assert "assigned_to" in entry


# ============================================================
# 11. INTEGRATION TESTS — full API endpoint
# ============================================================

AGILE_PAYLOAD = {
    "project": {
        "name": "Mobile App",
        "duration_days": 60,
        "complexity": "medium",
        "methodology": "agile"
    },
    "team_members": [
        {
            "id": 1, "name": "Alice",
            "skills": ["python", "fastapi", "postgresql", "testing"],
            "experience_level": "senior",
            "weekly_availability_hours": 30
        },
        {
            "id": 2, "name": "Bob",
            "skills": ["react", "javascript", "css"],
            "experience_level": "mid",
            "weekly_availability_hours": 35
        }
    ]
}

WATERFALL_PAYLOAD = {
    "project": {
        "name": "Enterprise System",
        "duration_days": 120,
        "complexity": "high",
        "methodology": "waterfall"
    },
    "team_members": [
        {
            "id": 1, "name": "Alice",
            "skills": ["python", "fastapi", "postgresql", "sql", "testing"],
            "experience_level": "senior",
            "weekly_availability_hours": 40
        },
        {
            "id": 2, "name": "Bob",
            "skills": ["react", "javascript", "css"],
            "experience_level": "junior",
            "weekly_availability_hours": 40
        },
        {
            "id": 3, "name": "Charlie",
            "skills": ["docker", "devops"],
            "experience_level": "mid",
            "weekly_availability_hours": 30
        }
    ]
}

MISSING_SKILLS_PAYLOAD = {
    "project": {
        "name": "Broken Project",
        "duration_days": 30,
        "complexity": "low",
        "methodology": "kanban"
    },
    "team_members": [
        {
            "id": 1, "name": "Alice",
            "skills": ["react", "javascript"],   # no devops — Deployment will warn
            "experience_level": "mid",
            "weekly_availability_hours": 30
        }
    ]
}


class TestAPIEndpoint:

    # --- Basic response structure ---

    def test_agile_returns_200(self):
        r = client.post("/generate", json=AGILE_PAYLOAD)
        assert r.status_code == 200

    def test_agile_response_has_required_fields(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        assert "tasks" in data
        assert "sprints" in data
        assert "gantt_data" in data
        assert "warnings" in data
        assert "error" in data

    def test_agile_error_is_null(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        assert data["error"] is None

    # --- Tasks ---

    def test_agile_returns_tasks(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        assert len(data["tasks"]) > 0

    def test_all_tasks_have_assignments(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        for task in data["tasks"]:
            assert task["assigned_to"] is not None

    def test_all_tasks_have_valid_schedule(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        for task in data["tasks"]:
            assert task["end_day"] > task["start_day"], \
                f"Task '{task['title']}' has invalid schedule: {task['start_day']} → {task['end_day']}"

    def test_dependencies_are_respected(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        task_map = {t["id"]: t for t in data["tasks"]}
        for task in data["tasks"]:
            for dep_id in task["dependencies"]:
                dep = task_map[dep_id]
                assert task["start_day"] >= dep["end_day"], \
                    f"Task {task['id']} starts day {task['start_day']} but depends on task {dep_id} which ends day {dep['end_day']}"

    def test_skill_based_assignment_backend_goes_to_alice(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        backend_tasks = [t for t in data["tasks"] if "python" in t["required_skills"]]
        for task in backend_tasks:
            assert task["assigned_to"] == 1, \
                f"Backend task '{task['title']}' should go to Alice (id=1)"

    def test_skill_based_assignment_frontend_goes_to_bob(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        frontend_tasks = [t for t in data["tasks"]
                          if "javascript" in t["required_skills"] or "css" in t["required_skills"]]
        for task in frontend_tasks:
            assert task["assigned_to"] == 2, \
                f"Frontend task '{task['title']}' should go to Bob (id=2)"

    def test_frontend_and_backend_run_in_parallel(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        task_map = {t["id"]: t for t in data["tasks"]}
        backend  = next((t for t in data["tasks" ] if "python" in t["required_skills"]
                         and t["assigned_to"] == 1), None)
        frontend = next((t for t in data["tasks"] if "javascript" in t["required_skills"]
                         and t["assigned_to"] == 2), None)
        if backend and frontend:
            # They should overlap in time — frontend doesn't wait for backend
            overlap = backend["start_day"] < frontend["end_day"] and \
                      frontend["start_day"] < backend["end_day"]
            assert overlap, "Frontend and backend tasks should run in parallel"

    # --- Sprints ---

    def test_agile_returns_sprints(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        assert data["sprints"] is not None
        assert len(data["sprints"]) > 0

    def test_waterfall_returns_no_sprints(self):
        data = client.post("/generate", json=WATERFALL_PAYLOAD).json()
        assert data["sprints"] is None

    def test_sprints_are_14_days(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        for sprint in data["sprints"]:
            length = sprint["end_day"] - sprint["start_day"] + 1
            assert length == 14, f"Sprint {sprint['sprint_number']} is {length} days, expected 14"

    def test_sprint_numbers_sequential(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        for i, sprint in enumerate(data["sprints"]):
            assert sprint["sprint_number"] == i + 1

    # --- Gantt data ---

    def test_gantt_data_present(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        assert data["gantt_data"] is not None
        assert len(data["gantt_data"]["task_durations"]) == len(data["tasks"])

    def test_gantt_dependencies_match_task_dependencies(self):
        data = client.post("/generate", json=AGILE_PAYLOAD).json()
        gantt_deps = {(d["from"], d["to"]) for d in data["gantt_data"]["dependencies"]}
        for task in data["tasks"]:
            for dep_id in task["dependencies"]:
                assert (dep_id, task["id"]) in gantt_deps

    # --- Error & warnings ---

    def test_missing_skills_returns_warnings_not_error(self):
        data = client.post("/generate", json=MISSING_SKILLS_PAYLOAD).json()
        # Should still return a plan (with warnings), not crash
        assert data["error"] is None
        assert len(data["tasks"]) > 0
        assert len(data["warnings"] ) > 0

    def test_empty_team_returns_error(self):
        payload = {**AGILE_PAYLOAD, "team_members": []}
        data = client.post("/generate", json=payload).json()
        assert data["error"] is not None
        assert data["tasks"] == []

    def test_root_endpoint(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json() == {"status": "AI Module Running"}