from playwright.sync_api import sync_playwright
import time

LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
NFA_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

USERNAME = "eduardof"
PASSWORD = "atf101010"

def main():
    print("=== NFA Forced Navigation Test ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("Opening login page...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        print("Logging in...")
        page.fill("input[name='edtNoLogin']", USERNAME)
        page.fill("input[name='edtDsSenha']", PASSWORD)
        page.click("button[name='btnAvancar']")

        # Wait briefly (SEFAZ no longer redirects)
        time.sleep(2)

        print("Forcing redirect to NFA form...")
        page.goto(NFA_URL, wait_until="domcontentloaded")

        print("Done. Check the browser.")
        input("Press ENTER to close...")
