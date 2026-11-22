import httpx, subprocess, sys
from conftest import BASE, demo, new_user
def test_reconcile_script():
    r = subprocess.run([sys.executable, "scripts/reconcile.py"], capture_output=True, text=True, cwd=__import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
    assert r.returncode == 0 and "FAIL" not in r.stdout, r.stdout[-1500:]
def test_individual_independent():
    for h in (demo("individual"), new_user()[1]):
        for p in ("auth/me", "overview?days=30", "usage?days=30", "lending/ledger"):
            t = httpx.get(f"{BASE}/{p}", headers=h).text
            for bad in ("Nexora", "Engineering", "Marketing", "Operations", "dep_"):
                assert bad not in t, (p, bad)
    _, h = new_user()
    c = httpx.get(f"{BASE}/overview?days=30", headers=h).json()["cycle"]
    assert c["budget"] == 1000 and c["used"] == 0
