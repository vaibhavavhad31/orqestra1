from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

Mode = Literal["individual", "organisation"]
Role = Literal["admin", "manager", "employee", "individual"]


class RegisterIn(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    mode: str = ""
    org_name: str = ""


class LoginIn(BaseModel):
    email: str = ""
    password: str = ""


class GoogleSessionIn(BaseModel):
    session_id: str


class GoogleCompleteIn(BaseModel):
    pending_token: str
    mode: str = ""
    org_name: str = ""


class DemoLoginIn(BaseModel):
    key: Literal["admin", "manager", "employee", "individual", "tomas", "hana", "kwame"]


class DemoSwitchIn(BaseModel):
    target_user_id: str


class Ref(BaseModel):
    id: str
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    title: Optional[str] = None
    mode: Mode
    role: Role
    role_label: str
    is_demo: bool = False
    auth_provider: str
    picture: Optional[str] = None
    organization: Optional[Ref] = None
    department: Optional[Ref] = None
    allowed_modules: list[str]
    must_change_password: bool = False


class AuthOut(BaseModel):
    user: UserOut
    access_token: str


class DemoAccountOut(BaseModel):
    key: str
    user_id: str
    name: str
    title: Optional[str] = None
    email: str
    role: Role
    role_label: str
    workspace: str
    description: str
    group: str = "primary"
