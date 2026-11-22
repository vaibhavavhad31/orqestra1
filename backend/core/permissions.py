MODULES = [
    "overview", "tasks", "usage", "allocation", "lending", "handover", "planner",
    "notifications", "reports", "team", "integrations", "settings",
]

_EXCLUDED = {
    "individual": {"allocation", "team"},
    "admin": {"lending"},
    "manager": {"lending", "integrations"},
}
_EMPLOYEE = {"overview", "tasks", "usage", "allocation", "handover", "planner", "notifications", "settings"}

ROLE_LABELS = {
    "admin": "Organisation Admin",
    "manager": "Manager",
    "employee": "Employee",
    "individual": "Individual",
}


def allowed_modules(role: str) -> list[str]:
    if role == "employee":
        return [m for m in MODULES if m in _EMPLOYEE]
    excluded = _EXCLUDED.get(role)
    if excluded is None:
        return []
    return [m for m in MODULES if m not in excluded]
