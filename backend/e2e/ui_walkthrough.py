"""Browser walkthrough of the main Orqestra workflows across roles. Run against a local server:
    BASE=http://localhost:8001 python e2e/ui_walkthrough.py
Prints PASS/FAIL per step and saves screenshots to e2e/shots/.
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BASE", "http://localhost:8001")
SHOTS = Path(__file__).parent / "shots"
SHOTS.mkdir(exist_ok=True)
results = []


def step(name, fn):
    try:
        fn()
        results.append((name, "PASS", ""))
    except Exception as exc:  # report and continue
        results.append((name, "FAIL", str(exc).splitlines()[0][:200]))


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def demo_login(label):
            page.goto(f"{BASE}/login")
            page.get_by_role("button", name=label).first.click()
            page.wait_for_url("**/overview", timeout=15000)

        def demo_login_btn(key):
            ctx.clear_cookies()
            page.goto(f"{BASE}/login")
            page.get_by_test_id(f"demo-login-{key}").click()
            page.wait_for_url("**/overview", timeout=15000)

        # ---- login page ----
        def login_page():
            page.goto(f"{BASE}/login")
            expect(page.get_by_text("Orqestra").first).to_be_visible()
            assert page.get_by_test_id("google-login-button").count() == 0, "Google button should be hidden"
            page.screenshot(path=str(SHOTS / "01_login.png"))
        step("Login page shows Orqestra, no Google button", login_page)

        def no_tracking():
            html = page.content()
            assert "posthog" not in html.lower() and "emergent" not in html.lower(), "tracking or Emergent script present"
            assert page.evaluate("typeof window.posthog") == "undefined"
        step("No PostHog / Emergent scripts in the page", no_tracking)

        # ---- manager: create goal with breakdown, assign, slot ----
        def manager_overview():
            page.goto(f"{BASE}/login")
            page.screenshot(path=str(SHOTS / "02_demo_buttons.png"))
            page.get_by_test_id("demo-login-manager").click()
            page.wait_for_url("**/overview", timeout=15000)
            expect(page.get_by_test_id("page-title")).to_be_visible()
        step("Manager demo login lands on Overview", manager_overview)

        def tasks_nav():
            page.get_by_role("link", name="Tasks").first.click()
            page.wait_for_url("**/tasks")
            expect(page.get_by_test_id("goals-list")).to_be_visible(timeout=10000)
            expect(page.get_by_text("Ship the payments API v2 retry logic")).to_be_visible()
            page.screenshot(path=str(SHOTS / "03_tasks_list.png"))
        step("Tasks page lists the seeded goal", tasks_nav)

        def create_goal():
            page.get_by_test_id("open-goal-dialog").click()
            page.get_by_test_id("input-goal-title").fill("Build the invoice export API")
            page.get_by_test_id("input-goal-description").fill("CSV and JSON export endpoints with tests and docs for finance.")
            page.get_by_test_id("goal-breakdown").click()
            expect(page.get_by_test_id("goal-subtasks")).to_be_visible(timeout=10000)
            expect(page.get_by_test_id("goal-breakdown-notice")).to_contain_text("software")
            n = page.get_by_test_id("goal-subtasks").locator("> li").count()
            assert n >= 4, f"only {n} sub-tasks"
            page.screenshot(path=str(SHOTS / "04_breakdown.png"), full_page=True)
            page.get_by_test_id("goal-dialog-submit").click()
            expect(page.get_by_test_id("goal-sheet")).to_be_visible(timeout=10000)
            expect(page.get_by_test_id("wave-2")).to_contain_text("can run in parallel")
            page.screenshot(path=str(SHOTS / "05_goal_sheet.png"), full_page=True)
        step("Manager breaks a goal into sub-tasks and saves it (waves shown)", create_goal)

        def assign_and_slot():
            sheet = page.get_by_test_id("goal-sheet")
            first = sheet.locator("[data-testid^='subtask-tsk_']").first
            first.locator("[data-testid$='-suggest-assignee']").click()
            expect(sheet.get_by_test_id("candidates-panel")).to_be_visible(timeout=10000)
            expect(sheet.get_by_test_id("candidate-0")).to_contain_text("open task")
            page.screenshot(path=str(SHOTS / "06_candidates.png"), full_page=True)
            sheet.get_by_test_id("candidate-0-assign").click()
            expect(first).to_contain_text("Assigned to", timeout=10000)
            first.locator("[data-testid$='-suggest-slot']").click()
            expect(sheet.get_by_test_id("slot-panel")).to_be_visible(timeout=10000)
            page.screenshot(path=str(SHOTS / "07_slot.png"), full_page=True)
            sheet.get_by_test_id("slot-accept").click()
            page.wait_for_timeout(1500)
        step("Manager gets ranked assignees with reasons, assigns, and gets a slot", assign_and_slot)

        def blocked_dependency():
            sheet = page.get_by_test_id("goal-sheet")
            later = sheet.get_by_test_id("wave-1").locator("[data-testid$='-status-select']").first
            later.select_option("in_progress")
            expect(sheet.get_by_role("alert").first).to_contain_text("Waiting on", timeout=10000)
        step("Starting a sub-task before its dependency is refused", blocked_dependency)

        def allocation_page():
            page.keyboard.press("Escape")
            page.goto(f"{BASE}/allocation")
            expect(page.get_by_test_id("page-title")).to_have_text("Resource Allocation", timeout=10000)
        step("Manager Resource Allocation still loads", allocation_page)

        # ---- admin: privacy + cross-department suggestions ----
        def admin_privacy():
            demo_login_btn("admin")
            page.goto(f"{BASE}/handover")
            page.get_by_test_id("handover-tab-all").click()
            row = page.locator("[data-testid^='handover-row-']").filter(has_text="Q1 onboarding research synthesis").first
            row.click()
            expect(page.get_by_test_id("handover-restricted-note")).to_be_visible(timeout=10000)
            assert page.get_by_test_id("handover-objective").count() == 0
            page.screenshot(path=str(SHOTS / "08_admin_handover_restricted.png"))
            page.keyboard.press("Escape")
        step("Admin sees handover metadata only (content restricted)", admin_privacy)

        def admin_suggestions():
            page.goto(f"{BASE}/allocation")
            expect(page.get_by_test_id("suggestion-0")).to_be_visible(timeout=10000)
            page.screenshot(path=str(SHOTS / "09_admin_suggestions.png"), full_page=True)
        step("Admin sees reallocation suggestions (previously empty)", admin_suggestions)

        def admin_pages():
            for path, title in [("/overview", None), ("/usage", "AI Usage"), ("/reports", "Reports"), ("/team", "Team"),
                                ("/integrations", "Integrations"), ("/settings", "Settings"), ("/notifications", "Notifications"),
                                ("/planner", "Session Planner"), ("/tasks", "Tasks")]:
                page.goto(f"{BASE}{path}")
                expect(page.get_by_test_id("page-title")).to_be_visible(timeout=10000)
                if title:
                    expect(page.get_by_test_id("page-title")).to_have_text(title)
        step("Admin: every module page loads", admin_pages)

        # ---- employee: assigned work visible, planner ----
        def employee_flow():
            demo_login_btn("employee")
            page.goto(f"{BASE}/tasks")
            expect(page.get_by_text("Ship the payments API v2 retry logic")).to_be_visible(timeout=10000)
            page.get_by_text("Ship the payments API v2 retry logic").click()
            expect(page.get_by_test_id("goal-sheet")).to_contain_text("Assigned to", timeout=10000)
            page.screenshot(path=str(SHOTS / "10_employee_goal.png"), full_page=True)
            page.keyboard.press("Escape")
            page.goto(f"{BASE}/planner")
            expect(page.get_by_test_id("page-title")).to_have_text("Session Planner", timeout=10000)
            page.screenshot(path=str(SHOTS / "11_employee_planner.png"), full_page=True)
        step("Employee sees goals they work on and their planner", employee_flow)

        # ---- individual: lending + tasks ----
        def individual_flow():
            demo_login_btn("individual")
            page.goto(f"{BASE}/lending")
            expect(page.get_by_test_id("page-title")).to_be_visible(timeout=10000)
            page.goto(f"{BASE}/tasks")
            expect(page.get_by_text("Research onboarding drop-off for a fintech app")).to_be_visible(timeout=10000)
            page.screenshot(path=str(SHOTS / "12_individual_tasks.png"), full_page=True)
        step("Individual: Credit Lending and Tasks load", individual_flow)

        def mobile_view():
            m = browser.new_context(viewport={"width": 390, "height": 844}, storage_state=ctx.storage_state())
            mp = m.new_page()
            mp.goto(f"{BASE}/tasks")
            expect(mp.get_by_test_id("tasks-page")).to_be_visible(timeout=10000)
            mp.screenshot(path=str(SHOTS / "13_mobile_tasks.png"), full_page=True)
            m.close()
        step("Tasks page renders on a phone-sized screen", mobile_view)

        step("No uncaught JavaScript errors", lambda: (_ for _ in ()).throw(AssertionError("; ".join(errors[:3]))) if errors else None)
        browser.close()


if __name__ == "__main__":
    run()
    width = max(len(n) for n, _, _ in results)
    for n, r, msg in results:
        print(f"{r}  {n.ljust(width)}  {msg}")
    print(f"\n{sum(r == 'PASS' for _, r, _ in results)} passed, {sum(r == 'FAIL' for _, r, _ in results)} failed")
    sys.exit(0 if all(r == "PASS" for _, r, _ in results) else 1)
