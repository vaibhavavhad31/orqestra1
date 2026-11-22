import re
from fastapi import HTTPException

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def field_error(status: int, fields: dict[str, str]) -> HTTPException:
    return HTTPException(status_code=status, detail={"message": next(iter(fields.values())), "fields": fields})


def validate_mode(mode: str, org_name: str, errors: dict) -> None:
    if mode not in ("individual", "organisation"):
        errors["mode"] = "Choose Individual or Organisation"
    elif mode == "organisation" and not org_name.strip():
        errors["org_name"] = "Enter your organisation name"


def validate_signup(name: str, email: str, password: str, mode: str, org_name: str) -> None:
    errors: dict[str, str] = {}
    if not name.strip():
        errors["name"] = "Enter your full name"
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address"
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"
    validate_mode(mode, org_name, errors)
    if errors:
        raise field_error(422, errors)
