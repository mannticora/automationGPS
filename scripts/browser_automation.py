"""Wrappers de Playwright para interactuar con la plataforma Censo Baterías.

Estado de los selectores (verificado 2026-09-04 contra el DOM real, con acceso
confirmado y Case ID 1777 / AUTOSERVICIO CALVA como caso de prueba):
- Login: formulario `form.login-form`, banner de error `.alert-error`.
- Listado ("Cola de revisión"): tabla `table.tabla-encuestas`, columnas
  Case ID (1), Negocio (3), Revisión/estado (9, `<span class="tag ...">`),
  acción "Revisar" (`<a href="revisar.php?id=...">`, único link de la fila).
  El estado pendiente se muestra como "PENDIENTE" (español).
- Detalle de caso ("Revisar Case ID N"): el nombre de negocio editable vive en
  `input#nomneg`; las coordenadas GPS ("Geo Location") NO son un input, sino un
  `<p>` justo después de un `<label>Geo Location</label>` — no tienen id/clase,
  por lo que se ubican por XPath sobre el texto del label.
"""
from playwright.sync_api import Browser, BrowserContext, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from utils import retry, take_screenshot


class LoginError(Exception):
    """Se lanza cuando el login falla (credenciales incorrectas o error de plataforma)."""


class CaseNotFoundError(Exception):
    """Se lanza cuando no se encuentra un Case ID en el listado."""


class CensoBateriasClient:
    """Cliente de alto nivel para navegar la plataforma Censo Baterías con Playwright."""

    def __init__(self, playwright, headless: bool | None = None):
        """Lanza el navegador configurado en `Config.BROWSER_TYPE` y abre una página."""
        self._playwright = playwright
        self._headless = Config.HEADLESS_MODE if headless is None else headless
        browser_launcher = getattr(playwright, Config.BROWSER_TYPE)
        self.browser: Browser = browser_launcher.launch(headless=self._headless)
        # Un único BrowserContext para todas las páginas: browser.new_page() crearía un
        # contexto nuevo (y por lo tanto sin cookies de sesión) por cada página.
        self.context: BrowserContext = self.browser.new_context()
        self.context.set_default_timeout(Config.TIMEOUT_SEGUNDOS * 1000)
        self.page: Page = self.context.new_page()

    def login(self) -> None:
        """Inicia sesión con las credenciales de `config.py`.

        Lanza `LoginError` si la plataforma responde con el banner de error
        (`.alert-error`, ej. "Correo o contraseña incorrectos.").
        """
        logger.info(f"Accediendo a {Config.CENSO_URL} ...")
        self.page.goto(Config.CENSO_URL)
        self.page.fill("input[name='email']", Config.CENSO_EMAIL)
        self.page.fill("input[name='password']", Config.CENSO_PASSWORD)
        self.page.click("form.login-form button[type='submit']")

        try:
            self.page.wait_for_selector(".alert-error", timeout=5000)
        except PlaywrightTimeoutError:
            # No apareció el banner de error dentro del timeout -> login exitoso.
            self.page.wait_for_load_state("networkidle")
            logger.success("Login exitoso.")
            return

        error_text = (self.page.locator(".alert-error").text_content() or "").strip()
        take_screenshot(self.page, "login_error")
        raise LoginError(f"Login falló: {error_text or 'credenciales incorrectas'}")

    @retry()
    def get_pending_cases(self, order_by: str | None = None, ascending: bool | None = None,
                           limit: int | None = None) -> list[dict]:
        """Extrae la lista de casos cuya columna "Revisión" coincide con `Config.FILTRO_ESTADO`
        (por defecto "pendiente").

        Devuelve una lista de dicts `{"case_id": str, "url": str, "status_raw": str}`.
        """
        order_by = order_by or Config.ORDEN_POR
        ascending = Config.ORDEN_ASCENDENTE if ascending is None else ascending
        direction = "asc" if ascending else "desc"
        url = f"{Config.CENSO_URL.rstrip('/')}/?sort={order_by}&dir={direction}"

        logger.info(f"Cargando listado de casos: {url}")
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

        rows = self.page.locator("table.tabla-encuestas tbody tr").all()
        cases: list[dict] = []
        for row in rows:
            try:
                case_id = (row.locator("td:nth-child(1)").text_content(timeout=2000) or "").strip()
                status = (row.locator("td:nth-child(9)").text_content(timeout=2000) or "").strip()
                href = row.locator("a").get_attribute("href", timeout=2000)
            except PlaywrightTimeoutError:
                continue
            if status and Config.FILTRO_ESTADO.lower() in status.lower():
                cases.append({"case_id": case_id, "url": href, "status_raw": status})

        logger.info(f"{len(cases)} casos encontrados con estado '{Config.FILTRO_ESTADO}'.")
        return cases[:limit] if limit else cases

    def find_case_by_id(self, case_id: str) -> dict:
        """Busca un Case ID específico en el listado. Lanza `CaseNotFoundError` si no aparece."""
        self.page.goto(Config.CENSO_URL)
        self.page.wait_for_load_state("networkidle")

        rows = self.page.locator("table.tabla-encuestas tbody tr").all()
        for row in rows:
            row_id = (row.locator("td:nth-child(1)").text_content(timeout=2000) or "").strip()
            if row_id == str(case_id):
                href = row.locator("a").get_attribute("href", timeout=2000)
                return {"case_id": row_id, "url": href}

        raise CaseNotFoundError(f"No se encontró el Case ID {case_id} en el listado.")

    @staticmethod
    def _labeled_value(page: Page, label_text: str) -> str:
        """Lee el texto del `<p>` que sigue inmediatamente a un `<label>` con `label_text`.

        La plataforma muestra varios campos de solo lectura como `<label>...</label><p>...</p>`
        sin id ni clase, así que se ubican por el texto exacto del label.
        """
        locator = page.locator(f"xpath=//label[normalize-space(text())='{label_text}']/following-sibling::p")
        return (locator.text_content(timeout=5000) or "").strip()

    @retry()
    def extract_case_data(self, case_id: str, url: str | None = None) -> dict:
        """Abre el detalle de un caso y extrae nombre de negocio + coordenadas GPS crudas.

        Si `url` no se provee, primero busca el caso con `find_case_by_id`. Devuelve
        `{"business_name": str, "geo_location_raw": str}`. El nombre de negocio se lee
        del input editable `#nomneg` (Sección 10); las coordenadas, del campo de solo
        lectura "Geo Location" (Sección 1).
        """
        if not url:
            url = self.find_case_by_id(case_id)["url"]
        full_url = url if url.startswith("http") else f"{Config.CENSO_URL.rstrip('/')}/{url.lstrip('/')}"

        logger.info(f"Abriendo Case ID {case_id}: {full_url}")
        detail_page = self.context.new_page()
        try:
            detail_page.goto(full_url)
            detail_page.wait_for_load_state("networkidle")
            business_name = detail_page.locator("#nomneg").input_value()
            geo_location_raw = self._labeled_value(detail_page, "Geo Location")
            return {"business_name": business_name.strip(), "geo_location_raw": geo_location_raw}
        except Exception:
            take_screenshot(detail_page, f"extract_error_case_{case_id}")
            raise
        finally:
            detail_page.close()

    def close(self) -> None:
        """Cierra el navegador y libera recursos."""
        self.browser.close()
