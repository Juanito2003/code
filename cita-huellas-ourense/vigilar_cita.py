#!/usr/bin/env python3
"""
Vigila la cita previa de extranjería (icp.administracionelectronica.gob.es)
para "POLICÍA-TOMA DE HUELLAS" en Ourense y avisa cuando aparece una cita.

Debe ejecutarse desde un ordenador en España: la web bloquea conexiones
desde servidores en la nube o desde el extranjero.

Uso:
    pip install playwright
    python -m playwright install chromium
    cp config.example.json config.json   # y rellena tus datos
    python vigilar_cita.py
"""
import json
import random
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URL_INICIO = "https://icp.administracionelectronica.gob.es/icpplus/index.html"
TXT_SIN_CITAS = "no hay citas disponibles"
BASE = Path(__file__).resolve().parent


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).upper().strip()


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def cargar_config() -> dict:
    ruta = BASE / "config.json"
    if not ruta.exists():
        sys.exit("Falta config.json. Copia config.example.json a config.json y rellénalo.")
    return json.loads(ruta.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- avisos
def avisar(cfg: dict, mensaje: str) -> None:
    log("*** " + mensaje + " ***")
    token, chat = cfg.get("telegram_token"), cfg.get("telegram_chat_id")
    if token and chat:
        try:
            data = urllib.parse.urlencode({"chat_id": chat, "text": mensaje}).encode()
            urllib.request.urlopen(
                f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=15
            )
        except Exception as e:  # noqa: BLE001
            log(f"No se pudo enviar el Telegram: {e}")
    # Pitido / notificación local
    try:
        if sys.platform.startswith("win"):
            import winsound
            for _ in range(5):
                winsound.Beep(1200, 400)
        else:
            for _ in range(5):
                print("\a", end="", flush=True)
                time.sleep(0.4)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- helpers
def elegir_opcion(page, selector: str, texto: str) -> bool:
    """Selecciona en un <select> la primera opción cuyo texto contiene `texto`."""
    sel = page.locator(selector)
    if sel.count() == 0:
        return False
    objetivo = norm(texto)
    for op in sel.first.locator("option").all():
        etiqueta = op.inner_text()
        if objetivo in norm(etiqueta):
            valor = op.get_attribute("value")
            sel.first.select_option(value=valor)
            return True
    return False


def elegir_en_cualquier_select(page, texto: str) -> bool:
    """Busca `texto` en todos los <select> de la página (útil para trámites)."""
    objetivo = norm(texto)
    for sel in page.locator("select").all():
        for op in sel.locator("option").all():
            if objetivo in norm(op.inner_text()):
                sel.select_option(value=op.get_attribute("value"))
                return True
    return False


def pulsar(page, *selectores: str) -> None:
    for s in selectores:
        loc = page.locator(s)
        if loc.count() and loc.first.is_visible():
            loc.first.click()
            page.wait_for_load_state("domcontentloaded")
            return
    raise RuntimeError(f"No encuentro el botón ({', '.join(selectores)}) en {page.url}")


def pausa():
    time.sleep(random.uniform(1.2, 2.8))


def texto_pagina(page) -> str:
    return norm(page.locator("body").inner_text())


# ---------------------------------------------------------------- flujo
def comprobar(page, cfg: dict) -> str:
    """Devuelve 'sin_citas', 'hay_citas' o 'desconocido'."""
    page.goto(URL_INICIO, wait_until="domcontentloaded", timeout=60000)
    pausa()

    # 1. Provincia
    if not elegir_opcion(page, "select#form, select[name=form]", cfg["provincia"]):
        raise RuntimeError("No encuentro la provincia en la lista")
    pausa()
    pulsar(page, "#btnAceptar", "input[value=Aceptar]")
    pausa()

    # 2. Oficina + trámite
    elegir_opcion(page, "select#sede, select[name=sede]", cfg.get("oficina", ""))
    pausa()
    if not elegir_en_cualquier_select(page, cfg["tramite"]):
        raise RuntimeError("No encuentro el trámite en los desplegables")
    pausa()
    pulsar(page, "#btnAceptar", "input[value=Aceptar]")
    pausa()

    # 3. Página informativa -> "Presentación sin Cl@ve" / Entrar
    pulsar(page, "#btnEntrar", "input[value=Entrar]", "text=Presentación sin Cl@ve")
    pausa()

    # 4. Datos personales
    radio_nie = page.locator("#rdbTipoDocNie")
    if radio_nie.count():
        radio_nie.check()
    page.fill("#txtIdCitado", cfg["nie"])
    page.fill("#txtDesCitado", cfg["nombre"])
    if page.locator("#txtAnnoCitado").count():
        page.fill("#txtAnnoCitado", str(cfg.get("anno_nacimiento", "")))
    if page.locator("#txtPaisNac").count():
        elegir_opcion(page, "#txtPaisNac", cfg.get("pais", ""))
    pausa()
    pulsar(page, "#btnEnviar", "input[value=Aceptar]")
    pausa()

    # 5. "Solicitar Cita"
    pulsar(page, "#btnEnviar", "input[value='Solicitar Cita']")
    pausa()

    txt = texto_pagina(page)
    if norm(TXT_SIN_CITAS) in txt:
        return "sin_citas"
    if any(k in txt for k in ("SELECCIONE", "CITAS DISPONIBLES", "DISPONIBLE", "OFICINA")):
        return "hay_citas"
    return "desconocido"


def main() -> None:
    cfg = cargar_config()
    intervalo = max(3, float(cfg.get("intervalo_minutos", 7)))
    log(f"Vigilando cita '{cfg['tramite']}' en {cfg['provincia']} cada ~{intervalo} min. Ctrl+C para parar.")

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=bool(cfg.get("headless", False)))
        while True:
            ctx = navegador.new_context(locale="es-ES")
            page = ctx.new_page()
            try:
                estado = comprobar(page, cfg)
                if estado == "sin_citas":
                    log("Sin citas disponibles.")
                elif estado == "hay_citas":
                    page.screenshot(path=str(BASE / "cita_encontrada.png"), full_page=True)
                    avisar(cfg, "¡HAY CITA para toma de huellas en Ourense! Entra YA en "
                                "https://icp.administracionelectronica.gob.es/icpplus/index.html")
                    if not cfg.get("headless", False):
                        log("Dejo la ventana abierta para que reserves. Pulsa Enter para seguir vigilando.")
                        input()
                else:
                    page.screenshot(path=str(BASE / "pagina_desconocida.png"), full_page=True)
                    log("Respuesta inesperada (guardada en pagina_desconocida.png). "
                        "Puede ser un bloqueo temporal o que hay cita: revísalo.")
                    avisar(cfg, "Vigilante de cita: respuesta inesperada, revisa la web por si hay cita.")
            except (PWTimeout, RuntimeError) as e:
                log(f"Error en la comprobación: {e}")
            finally:
                ctx.close()
            espera = intervalo * 60 * random.uniform(0.85, 1.25)
            time.sleep(espera)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Parado.")
