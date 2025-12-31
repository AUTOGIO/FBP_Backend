"""Automation task for CAD REDESIM consulta."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.core.config import settings
from app.core.logging_config import setup_logger
from app.modules.cadastro.consultar_redesim import (
    DEFAULT_CRIACAO_FIM,
    DEFAULT_CRIACAO_INICIO,
    consultar_redesim,
)
from app.modules.nfa.atf_login import perform_login
from app.modules.nfa.browser_launcher import (
    launch_persistent_browser,
    navigate_to_sefaz_with_fallback,
)

logger = setup_logger(__name__)


async def run_cad_redesim_consulta(payload: dict[str, Any]) -> dict[str, Any]:
    """Executes the headful REDESIM consulta with fixed filters."""
    username: Optional[str] = payload.get("username") or settings.NFA_USERNAME
    password: Optional[str] = payload.get("password") or settings.NFA_PASSWORD
    wait_user_dates: bool = bool(payload.get("wait_user_dates", True))
    data_inicio: str = payload.get("data_criacao_inicio") or DEFAULT_CRIACAO_INICIO
    data_fim: str = payload.get("data_criacao_fim") or DEFAULT_CRIACAO_FIM

    result: dict[str, Any] = {
        "status": "error",
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "error": None,
        "screenshot": None,
    }

    if not username or not password:
        result["error"] = "ATF credentials missing (set NFA_USERNAME/NFA_PASSWORD)."
        return result

    browser = None
    context = None
    page = None

    try:
        browser, context, page = await launch_persistent_browser(
            headless=False, slow_mo=100
        )
        nav_ok = await navigate_to_sefaz_with_fallback(page)
        if not nav_ok:
            raise RuntimeError("Navigation to ATF failed.")

        login_ok = await perform_login(page, username=username, password=password)
        if not login_ok:
            raise RuntimeError("ATF login failed.")

        await consultar_redesim(
            page,
            payload={
                "data_criacao_inicio": data_inicio,
                "data_criacao_fim": data_fim,
                "natureza_solicitacao": "CADASTRAMENTO",
            },
            wait_user_dates=wait_user_dates,
        )

        try:
            screenshot_path = (
                settings.paths.project_root / "output" / "redesim" / "screenshots"
            )
            screenshot_path.mkdir(parents=True, exist_ok=True)
            path = screenshot_path / "cad_redesim_consulta.png"
            await page.screenshot(path=str(path), full_page=True)
            result["screenshot"] = str(path)
        except Exception:
            pass

        result["status"] = "ok"
        return result

    except Exception as e:
        logger.exception("cad_redesim_consulta: automation failed: %s", e)
        result["error"] = str(e)
        return result

    finally:
        result["finished_at"] = datetime.utcnow().isoformat()
        try:
            if context:
                await context.close()
        except Exception:
            pass
        try:
            if browser:
                await browser.close()
        except Exception:
            pass

