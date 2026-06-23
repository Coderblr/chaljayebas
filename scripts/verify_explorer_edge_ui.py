from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 1100})
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    page.goto("http://127.0.0.1:8501", timeout=30000)
    page.wait_for_timeout(2000)
    page.fill('input[aria-label="Username"]', "admin")
    page.fill('input[aria-label="Password"]', "Admin@123")
    page.click('button:has-text("Log in")')
    page.wait_for_timeout(2500)

    page.click('[data-testid="stSidebarNav"] >> text="Application Explorer"')
    page.wait_for_timeout(1500)
    page.screenshot(path="F:/NBC_project/storage/screenshots/90_explorer_edge_default.png", full_page=True)
    print("Saved 90_explorer_edge_default.png")
    print("CONSOLE ERRORS:", console_errors)
    browser.close()
