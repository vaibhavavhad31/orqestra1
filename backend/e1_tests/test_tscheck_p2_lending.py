import threading, httpx
from conftest import BASE, demo, new_user

P = lambda h, p, j=None: httpx.post(BASE + p, headers=h, json=j if j is not None else {})
G = lambda h, p: httpx.get(BASE + p, headers=h)


def befriend(a, b, eb):
    fid = P(a, "/friends/requests", {"email": eb}).json()["outgoing"]
    fid = [f for f in fid if f["user"]["email"] == eb][0]["id"]
    r = P(b, f"/friends/requests/{fid}/accept"); assert r.status_code == 200, r.text
    return fid


def uid(h): return G(h, "/auth/me").json()["id"]


def pair():
    ea, a = new_user(); eb, b = new_user(); befriend(a, b, eb)
    return a, b


def test_friend_validation_and_unknown():
    _, a = new_user()
    for em in ("tscheck-nobody-x@example.com", "daniel.okafor@nexora.io"):
        r = P(a, "/friends/requests", {"email": em})
        assert r.status_code >= 400 and "No individual user found with that email" in r.text


def test_request_validation_cancel_decline():
    a, b = pair(); bid = uid(b)
    for amt in (0, -5, 2.5):
        r = P(a, "/lending/requests", {"friend_id": bid, "amount": amt, "reason": "tscheck"})
        assert r.status_code in (400, 422), (amt, r.text)
        assert "amount" in r.json()["detail"]["fields"]
    e = P(a, "/lending/requests", {"friend_id": bid, "amount": 50, "reason": "tscheck-cancel"}).json()
    r = P(a, f"/lending/entries/{e['id']}/cancel"); assert r.status_code == 200
    assert G(a, f"/lending/entries/{e['id']}").json()["status"] == "cancelled"
    before = G(b, "/lending/summary").json()["available"]
    e = P(a, "/lending/requests", {"friend_id": bid, "amount": 50, "reason": "tscheck-decline"}).json()
    assert P(b, f"/lending/entries/{e['id']}/decline").status_code == 200
    assert G(a, f"/lending/entries/{e['id']}").json()["status"] == "declined"
    assert G(b, "/lending/summary").json()["available"] == before


def test_accept_race_repay_dispute():
    a, b = pair(); bid = uid(b)
    sa0, sb0 = G(a, "/lending/summary").json()["available"], G(b, "/lending/summary").json()["available"]
    e = P(a, "/lending/requests", {"friend_id": bid, "amount": 100, "reason": "tscheck-loan"}).json()
    codes = []
    ts = [threading.Thread(target=lambda: codes.append(P(b, f"/lending/entries/{e['id']}/accept").status_code)) for _ in range(2)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(codes) == [200, 409], codes
    assert G(a, f"/lending/entries/{e['id']}").json()["status"] == "active"
    assert G(a, "/lending/summary").json()["available"] == sa0 + 100
    assert G(b, "/lending/summary").json()["available"] == sb0 - 100
    r = P(a, f"/lending/entries/{e['id']}/repayments", {"amount": 500})
    assert r.status_code == 400 and "Repayment exceeds outstanding amount" in r.text
    r = P(a, f"/lending/entries/{e['id']}/repayments", {"amount": 40}); assert r.status_code == 200, r.text
    ent = G(b, f"/lending/entries/{e['id']}").json()
    rep = [x for x in ent["repayments"] if x["status"] == "awaiting_confirmation"][0]
    assert P(b, f"/lending/repayments/{rep['id']}/confirm").status_code == 200
    ent = G(b, f"/lending/entries/{e['id']}").json()
    assert ent["outstanding"] == 60 and any(h["action"] == "repayment_confirmed" for h in ent["history"])
    r = P(a, f"/lending/entries/{e['id']}/repayments", {"amount": 10}); rid = [x for x in G(b, f"/lending/entries/{e['id']}").json()["repayments"] if x["status"] == "awaiting_confirmation"][0]["id"]
    assert P(b, f"/lending/repayments/{rid}/dispute").status_code == 200
    ent = G(b, f"/lending/entries/{e['id']}").json()
    assert [x for x in ent["repayments"] if x["id"] == rid][0]["status"] == "disputed" and ent["outstanding"] == 60, ent
    # third party / org 403
    _, c = new_user()
    assert G(c, f"/lending/entries/{e['id']}").status_code == 403
    assert G(demo("admin"), f"/lending/entries/{e['id']}").status_code == 403


def test_final_repay_sets_repaid():
    a, b = pair(); bid = uid(b)
    e = P(a, "/lending/requests", {"friend_id": bid, "amount": 30, "reason": "tscheck-full"}).json()
    assert P(b, f"/lending/entries/{e['id']}/accept").status_code == 200
    assert P(a, f"/lending/entries/{e['id']}/repayments", {"amount": 30}).status_code == 200
    rid = G(b, f"/lending/entries/{e['id']}").json()["repayments"][0]["id"]
    assert P(b, f"/lending/repayments/{rid}/confirm").status_code == 200
    ent = G(b, f"/lending/entries/{e['id']}").json()
    assert ent["status"] == "repaid" and ent["outstanding"] == 0


def test_kwame_not_enough_and_tomas_overdue():
    ea, a = new_user(); k = demo("kwame")
    befriend(a, k, "kwame.boateng@indie.dev")
    kid = uid(k)
    e = P(a, "/lending/requests", {"friend_id": kid, "amount": 500, "reason": "tscheck-big"}).json()
    r = P(k, f"/lending/entries/{e['id']}/accept")
    assert r.status_code >= 400 and "Not enough available credits to lend" in r.text
    P(a, f"/lending/entries/{e['id']}/cancel")
    ent = G(demo("tomas"), "/lending/entries/lnd_001").json()
    assert ent["overdue"] is True, ent
