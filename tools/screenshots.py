"""Take screenshots of the running app with headless Chrome via Playwright (dev-only tool; not needed to run the app).
   pip install playwright ; python tools/screenshots.py [base_url]"""
import sys, pathlib
from playwright.sync_api import sync_playwright
base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
out = pathlib.Path(__file__).resolve().parent.parent / "screenshots"; out.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900}, locale="el-GR")
    pg.goto(base); pg.wait_for_timeout(500)
    pg.screenshot(path=str(out / "01_form.png"))
    pg.click("#sample"); pg.wait_for_timeout(800)
    pg.screenshot(path=str(out / "02_form_filled_tz.png"))
    pg.click("#go"); pg.wait_for_selector("#results:not([hidden])"); pg.wait_for_timeout(1500)
    pg.add_style_tag(content=".jump{position:static!important}")
    pg.locator("#sec-chart").screenshot(path=str(out / "03_chart_wheel.png"))
    pg.locator("#sec-reading").screenshot(path=str(out / "04_reading.png"))
    pg.locator("#sec-aspects").screenshot(path=str(out / "05_aspects.png"))
    pg.locator("#sec-china").screenshot(path=str(out / "06_china.png"))
    pg.locator("#sec-numbers").screenshot(path=str(out / "07_numbers.png"))
    pg.locator("#sec-90").screenshot(path=str(out / "08_90days.png"))
    pg.screenshot(path=str(out / "00_result_fullpage.png"), full_page=True)
    pg.fill("#msg", "Τι να προσέξω σήμερα;"); pg.click("#send"); pg.wait_for_timeout(1500)
    pg.fill("#msg", "Έχω άγχος με μια απόφαση στη δουλειά, τι κάνω;"); pg.click("#send"); pg.wait_for_timeout(1500)
    pg.locator("#sec-chat").screenshot(path=str(out / "09_chat.png"))
    # mobile
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="el-GR")
    m.goto(base); m.click("#sample"); m.wait_for_timeout(600); m.click("#go"); m.wait_for_selector("#results:not([hidden])"); m.wait_for_timeout(1500)
    m.add_style_tag(content=".jump{position:static!important}")
    m.locator("#sec-chart").screenshot(path=str(out / "10_mobile_chart.png"))
    m.fill("#msg", "Πώς πάω στις σχέσεις;"); m.click("#send"); m.wait_for_timeout(1200)
    m.locator("#sec-chat").screenshot(path=str(out / "11_mobile_chat.png"))
    b.close()
print("ok")
