import httpx
from conftest import BASE, demo, new_user
def test_maya_lending():
    h = demo("individual")
    s = httpx.get(f"{BASE}/lending/summary", headers=h).json()
    assert s["lent_outstanding"] == 200 and s["borrowed_outstanding"] == 250 and s["net"] == -50 and s["pending_requests"] == 1
    assert "no provider credits are transferred" in s["simulated_disclaimer"].lower()
    l = httpx.get(f"{BASE}/lending/ledger", headers=h).json()
    assert {e["status"] for e in l["entries"]} == {"active", "pending", "repaid"}
def test_new_individual_empty_and_org_forbidden():
    _, h = new_user()
    assert httpx.get(f"{BASE}/lending/ledger", headers=h).json()["entries"] == []
    assert httpx.get(f"{BASE}/lending/summary", headers=demo("admin")).status_code == 403
