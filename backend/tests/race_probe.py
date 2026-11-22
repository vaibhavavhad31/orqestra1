# Probe: TOCTOU races across DIFFERENT entries/requests (lender available, dept pool). Run manually: python tests/race_probe.py
import os, concurrent.futures as cf, requests
from pymongo import MongoClient
API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
env = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l)
db = MongoClient(env["MONGO_URL"].strip('"'))[env["DB_NAME"].strip('"')]
tok = lambda k: {"Authorization": "Bearer " + requests.post(f"{API}/demo/login", json={"key": k}).json()["access_token"]}
M, K, MG, AD, E = tok("individual"), tok("kwame"), tok("manager"), tok("admin"), tok("employee")
created_e, created_r = [], []
try:
    k0 = requests.get(f"{API}/lending/summary", headers=K).json()["available"]
    amt = max(10, int(k0 * 0.75))
    print("kwame available", k0, "each request", amt)
    for _ in range(2):
        e = requests.post(f"{API}/lending/requests", json={"friend_id": "usr_kwame_boateng", "amount": amt, "reason": "TEST_race"}, headers=M).json()
        created_e.append(e["id"])
    with cf.ThreadPoolExecutor(2) as ex:
        codes = list(ex.map(lambda i: requests.post(f"{API}/lending/entries/{i}/accept", headers=K).status_code, created_e))
    print("lending accept codes", codes, "kwame available after", requests.get(f"{API}/lending/summary", headers=K).json()["available"])
    arjun0 = requests.get(f"{API}/allocation", headers=E).json()["me"]["monthly_allocation"]
    pool = [d for d in requests.get(f"{API}/allocation", headers=MG).json()["departments"] if d["id"] == "dep_engineering"][0]["unallocated"]
    amt = max(1, int(pool * 0.75))
    for _ in range(2):
        r = requests.post(f"{API}/allocation/requests", json={"amount": amt, "reason": "TEST_race", "urgency": "low"}, headers=E).json()
        created_r.append(r["id"])
    with cf.ThreadPoolExecutor(2) as ex:
        codes = list(ex.map(lambda a: requests.post(f"{API}/allocation/requests/{a[0]}/approve", json={}, headers=a[1]).status_code,
                            zip(created_r, [MG, AD])))
    pool2 = [d for d in requests.get(f"{API}/allocation", headers=MG).json()["departments"] if d["id"] == "dep_engineering"][0]["unallocated"]
    print("pool", pool, "each", amt, "approve codes", codes, "pool after", pool2)
    os.system("cd /app/backend && python scripts/reconcile.py | grep -v checked")
finally:
    requests.put(f"{API}/allocation/members/usr_arjun_mehta", json={"credits": arjun0}, headers=AD)
    for i in created_e:
        db.lending_ledger.delete_one({"id": i}); db.notifications.delete_many({"meta.entry_id": i})
    for i in created_r:
        db.resource_requests.delete_one({"id": i}); db.notifications.delete_many({"meta.request_id": i})
    print("arjun restored to", requests.get(f"{API}/allocation", headers=E).json()["me"]["monthly_allocation"])
