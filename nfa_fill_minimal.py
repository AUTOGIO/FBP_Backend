from playwright.sync_api import sync_playwright
import time

LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
FORM_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

USERNAME = "eduardof"
PASSWORD = "atf101010"

def fill_fast(frame, sel, value):
    frame.fill(sel, value)
    time.sleep(0.3)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context()
        page = context.new_page()

        print("🌐 Opening login...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        print("🔐 Filling username/password...")
        page.fill("input[name='edtNoLogin']", USERNAME)
        page.fill("input[name='edtDsSenha']", PASSWORD)

        print("➡️ Submitting...")
        page.click("button[name='btnAvancar']")
        time.sleep(3)

        print("➡️ Going directly to FORM...")
        page.goto(FORM_URL, wait_until="domcontentloaded")
        time.sleep(3)

        # ===== GET MAIN FORM FRAME =====
        frames = page.frames
        form_frame = None
        for f in frames:
            if "EmitirNFAeReparticao" in f.url:
                form_frame = f
                break

        if not form_frame:
            print("❌ Form frame not found.")
            return

        print("✅ Form frame found.")

        # ================================
        # START FILLING REAL FORM FIELDS
        # ================================

        print("🧾 Filling Natureza Operação...")
        form_frame.select_option("select[name='cmbNaturezaOperacao']", "75")

        print("📌 Filling Motivo...")
        form_frame.select_option("select[name='cmbMotivo']", "1")

        print("🔄 Filling Tipo Operação...")
        form_frame.select_option("select[name='cmbTpOperacao']", "S")

        print("📦 Filling CFOP...")
        form_frame.fill("input[name='cmbNrCfop']", "6908")

        # ===== PRODUCT AREA =====
        print("📦 Filling product description...")
        form_frame.fill("textarea[name='txaDsDetalheProduto']", "SERVIÇO DE REMESSA")

        print("📏 Filling Unidade Medida...")
        form_frame.select_option("select[name='cmbUnidMedida']", "9")

        print("💲 Filling product value...")
        form_frame.fill("input[name='edtVlProduto']", "100.00")

        print("🔢 Filling quantity...")
        form_frame.fill("input[name='edtQtdProduto']", "1")

        print("📊 Filling Aliquota...")
        form_frame.fill("input[name='edtVlAliquota']", "18")

        print("📄 Filling CST...")
        form_frame.select_option("select[name='cmbNrCST']", "00")

        print("🏛 Filling Receita SEFIN...")
        form_frame.select_option("select[name='cmbSqReceitaSefin']", "335")

        print("📝 Filling Informações Adicionais...")
        form_frame.fill("textarea[name='txaInformacoesAdicionais']", "DOCUMENTO GERADO AUTOMATICAMENTE.")

        print("🎯 DONE. Form is filled (not submitted). Keep window open.")
        time.sleep(9999)


if __name__ == "__main__":
    main()
