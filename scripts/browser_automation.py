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
- Sección 7 "Marcas de baterías": tabla dentro del `<section class="panel">` que
  sigue al `<h2>7. Marcas de baterías</h2>`; cada fila de datos tiene un `<td>`
  (la fila de encabezado usa `<th>`).
- Sección 13 "Fotos": cada foto es un `<div class="foto-card" data-campo="FOTO_X">`
  que contiene o bien `<div class="foto-vacia">` (sin foto) o bien un `<img>`.
- Sección 5 "Estatus del negocio": `<p>` justo después de
  `<h2>5. Estatus del negocio (ESTNEG)</h2>`, mismo patrón que "Geo Location".
"""
from playwright.sync_api import Browser, BrowserContext, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from loguru import logger

from config import Config
from utils import retry, take_screenshot

PHOTO_FIELD_LABELS = {
    "FOTO_FACHADA": "Fachada",
    "FOTO_INTERIOR": "Interior",
    "FOTO_EXHIBIDOR": "Exhibidor",
    "FOTO_EXHIBIDOR_2": "Exhibidor 2",
    "FOTO_NEGOCIO": "Negocio",
    "MATERIAL_POP": "Material POP",
}


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
        sin id ni clase, así que se ubican por el texto exacto del label. Se toma solo el
        primer `<p>` siguiente (`[1]`): puede haber más de un `<p>` hermano (p. ej. un
        `<p class="tag-alerta">` de advertencia adicional), lo que rompería un locator sin
        índice ("strict mode violation" en Playwright).
        """
        locator = page.locator(
            f"xpath=//label[normalize-space(text())='{label_text}']/following-sibling::p[1]"
        )
        return (locator.text_content(timeout=5000) or "").strip()

    @staticmethod
    def _extract_battery_brands(page: Page) -> list[str]:
        """Devuelve los nombres de marca registrados en la Sección 7 (Marcas de baterías)."""
        section = page.locator(
            "xpath=//h2[normalize-space(text())='7. Marcas de baterías']/parent::section"
        )
        rows = section.locator("table tr").all()
        brands = []
        for row in rows:
            cells = row.locator("td")
            if cells.count() == 0:
                continue  # fila de encabezado (usa <th>, no <td>)
            name = (cells.first.text_content(timeout=2000) or "").strip()
            if name:
                brands.append(name)
        return brands

    @staticmethod
    def _extract_photo_status(page: Page) -> dict[str, bool]:
        """Devuelve `{etiqueta_legible: tiene_foto}` para las 6 fotos de la Sección 13."""
        cards = page.locator(".foto-card").all()
        status: dict[str, bool] = {}
        for card in cards:
            campo = card.get_attribute("data-campo") or ""
            label = PHOTO_FIELD_LABELS.get(campo, campo)
            has_photo = card.locator("img").count() > 0
            status[label] = has_photo
        return status

    def _extract_business_status(self, page: Page) -> str:
        """Lee el texto completo de la Sección 5 (Estatus del negocio / ESTNEG).

        Cuando el negocio no está "Operando", la plataforma agrega un segundo `<p
        class="tag-alerta">` de advertencia como hermano adicional — se toma solo el
        primer `<p>` (`[1]`), que es el valor real de ESTNEG.
        """
        locator = page.locator(
            "xpath=//h2[starts-with(normalize-space(text()),'5. Estatus')]/following-sibling::p[1]"
        )
        return (locator.text_content(timeout=5000) or "").strip()

    @retry()
    def extract_case_data(self, case_id: str, url: str | None = None) -> dict:
        """Abre el detalle de un caso y extrae los datos relevantes para el reporte.

        Si `url` no se provee, primero busca el caso con `find_case_by_id`. Devuelve:
        `{"business_name": str, "geo_location_raw": str, "business_status": str,
        "brands": list[str], "missing_photos": list[str], "total_photo_fields": int}`.
        El nombre de negocio se lee del input editable `#nomneg` (Sección 10); las
        coordenadas, del campo de solo lectura "Geo Location" (Sección 1).
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
            business_status = self._extract_business_status(detail_page)
            brands = self._extract_battery_brands(detail_page)
            photo_status = self._extract_photo_status(detail_page)
            missing_photos = [label for label, has_photo in photo_status.items() if not has_photo]
            return {
                "business_name": business_name.strip(),
                "geo_location_raw": geo_location_raw,
                "business_status": business_status,
                "brands": brands,
                "missing_photos": missing_photos,
                "total_photo_fields": len(photo_status),
            }
        except Exception:
            take_screenshot(detail_page, f"extract_error_case_{case_id}")
            raise
        finally:
            detail_page.close()

    def close(self) -> None:
        """Cierra el navegador y libera recursos."""
        self.browser.close()
