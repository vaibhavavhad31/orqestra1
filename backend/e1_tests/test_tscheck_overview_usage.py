import httpx, pytest
from conftest import BASE, demo
@pytest.mark.parametrize("role", ["admin","manager","employee","individual"])
def test_totals_match(role):
    h = demo(role)
    for d in (7,30,90):
        o = httpx.get(f"{BASE}/overview", params={"days":d}, headers=h).json()
        u = httpx.get(f"{BASE}/usage", params={"days":d}, headers=h).json()
        assert o["totals"]["credits"]==u["totals"]["credits"] and u["simulated"] is True
def test_filter_changes_and_org():
    h = demo("admin")
    a = httpx.get(f"{BASE}/overview", params={"days":7}, headers=h).json()["totals"]["credits"]
    b = httpx.get(f"{BASE}/overview", params={"days":90}, headers=h).json()
    assert a < b["totals"]["credits"]
    assert b["organization"]["employees"]==12 and b["organization"]["departments"]==4
    names = {p["name"] for p in httpx.get(f"{BASE}/usage", headers=h).json()["providers"]}
    assert names=={"ChatGPT","Claude","Gemini","Copilot","Perplexity"}
def test_employee_self_only():
    u = httpx.get(f"{BASE}/usage", params={"days":30}, headers=demo("employee")).json()
    assert u["scope"]["type"]=="self" and not u["members"] and not u["departments"]
