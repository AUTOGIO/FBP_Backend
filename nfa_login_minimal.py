
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
NFA_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

USERNAME = "eduardof"
PASSWORD = "atf101010"

def main():
    print("=== NFA Minimal Login Test (JS SUBMISSION FIX) ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("Navigating to login...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

        print("Filling username...")
        page.fill("input[name='edtNoLogin']", USERNAME)

        print("Filling password...")
        page.fill("input[name='edtDsSenha']", PASSWORD)

        print("Triggering JavaScript login...")
        page.evaluate("logarSistema()")

        print("Waiting for post-login navigation...")
        try:
            page.wait_for_url("**/seg/SEGf_MontarMenu.jsp*", timeout=60000)
            print("✔️ Login successful:", page.url)
        except:
            print("❌ Login failed — page never left login screen.")
            print("Current URL:", page.url)
            input("Press ENTER to close browser...")
            browser.close()
            return

        print("Navigating to NFA form...")
        page.goto(NFA_URL, wait_until="domcontentloaded")
        print("✔️ Arrived on NFA Form:", page.url)

        input("Press ENTER to close browser...")
        browser.close()

if __name__ == "__main__":
    main()
