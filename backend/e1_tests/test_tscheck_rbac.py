import httpx, pytest
from conftest import BASE, demo
M = {"org":{"admin":200,"manager":200,"employee":200,"individual":403},
     "org/departments":{"admin":200,"manager":200,"employee":403,"individual":403},
     "team/members":{"admin":200,"manager":200,"employee":403,"individual":403},
     "lending/summary":{"admin":403,"manager":403,"employee":403,"individual":200},
     "lending/ledger":{"admin":403,"manager":403,"employee":403,"individual":200}}
@pytest.mark.parametrize("path", list(M))
def test_rbac(path):
    for role, exp in M[path].items():
        r = httpx.get(f"{BASE}/{path}", headers=demo(role)); assert r.status_code==exp, (path, role, r.status_code)
def test_unauth():
    for p in ["overview","usage","org"]: assert httpx.get(f"{BASE}/{p}").status_code==401
