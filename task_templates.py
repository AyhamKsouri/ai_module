TASK_TEMPLATES = {
    "waterfall": {
        "low": ["Requirements", "Design", "Development", "Testing", "Deployment"],
        "medium": [
            "Detailed Requirements",
            "High-Level Design",
            "Detailed Design",
            "Backend Development",
            "Frontend Development",
            "Integration Testing",
            "User Acceptance",
            "Deployment"
        ],
        "high": [
            "System Requirements",
            "Architecture Design",
            "Database Design",
            "Backend Development",
            "Frontend Development",
            "API Integration",
            "Integration Testing",
            "Performance Testing",
            "User Acceptance",
            "Deployment"
        ]
    },
    "agile": {
        "low": [
            "User Story: Login",
            "User Story: Profile",
            "Environment Setup",
            "Testing"
        ],
        "medium": [
            "Epic: User Management",
            "Epic: Order Processing",
            "Backend Development",
            "Frontend Development",
            "Integration Testing"
        ],
        "high": [
            "Epic: Authentication",
            "Epic: Payments",
            "Database Design",
            "Backend Development",
            "Frontend Development",
            "API Integration",
            "Integration Testing",
            "Performance Testing"
        ]
    },
    "kanban": {
        "low": ["Setup Environment", "Feature Implementation", "Testing"],
        "medium": [
            "Database Design",
            "Backend Development",
            "Frontend Development",
            "Testing",
            "Deployment"
        ],
        "high": [
            "System Architecture",
            "Database Design",
            "Backend Development",
            "Frontend Development",
            "API Integration",
            "Integration Testing",
            "Deployment"
        ]
    }
}

TASK_SKILL_MAP = {
    "Requirements": {"skills": ["analysis"], "base_hours": 20},
    "Detailed Requirements": {"skills": ["analysis"], "base_hours": 30},
    "System Requirements": {"skills": ["analysis"], "base_hours": 40},

    "Design": {"skills": ["system_design"], "base_hours": 25},
    "High-Level Design": {"skills": ["architecture"], "base_hours": 35},
    "Detailed Design": {"skills": ["architecture"], "base_hours": 35},
    "Architecture Design": {"skills": ["architecture"], "base_hours": 50},

    "Database Design": {"skills": ["sql", "postgresql"], "base_hours": 40},

    "Development": {"skills": ["programming"], "base_hours": 60},
    "Backend Development": {"skills": ["python", "fastapi", "postgresql"], "base_hours": 60},
    "Frontend Development": {"skills": ["javascript", "react", "css"], "base_hours": 50},

    "API Integration": {"skills": ["python", "rest_api"], "base_hours": 35},

    "Testing": {"skills": ["testing"], "base_hours": 25},
    "Integration Testing": {"skills": ["testing"], "base_hours": 35},
    "Performance Testing": {"skills": ["testing"], "base_hours": 40},
    "User Acceptance": {"skills": ["testing"], "base_hours": 20},

    "Deployment": {"skills": ["docker", "devops"], "base_hours": 25},

    "Environment Setup": {"skills": ["devops"], "base_hours": 15},
    "Setup Environment": {"skills": ["devops"], "base_hours": 15},

    "Epic: User Management": {"skills": ["python", "react"], "base_hours": 70},
    "Epic: Order Processing": {"skills": ["python", "react"], "base_hours": 70},
    "Epic: Authentication": {"skills": ["python", "security"], "base_hours": 60},
    "Epic: Payments": {"skills": ["python", "api"], "base_hours": 60},

    "User Story: Login": {"skills": ["python", "react"], "base_hours": 25},
    "User Story: Profile": {"skills": ["python", "react"], "base_hours": 25},

    "Feature Implementation": {"skills": ["programming"], "base_hours": 40}
}