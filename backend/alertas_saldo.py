#!/usr/bin/env python3
"""
Verificação automática de saldos das BMs — Monaco Agency
Roda diariamente às 16h (BRT).
Abre a página saldos_dash.html via browser headless, injeta o token,
executa a verificação e envia alerta no grupo de operações via WhatsApp
se houver contas críticas (≤ R$50) ou baixas (≤ R$100).
"""

import json
import os
import sys
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Configuração ──────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent

# Token Meta — pode vir de variável de ambiente ou config.json
def obter_token() -> str:
    t = os.getenv("META_TOKEN", "")
    if t:
        return t
    cfg_path = BACKEND_DIR / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            contas = cfg.get("meta", {}).get("contas", [])
            if contas:
                return contas[0].get("access_token", "")
        except Exception:
            pass
    return ""

# Credenciais WhatsApp (Evolution API)
WPP_URL       = os.getenv("WPP_API_URL",    "https://evolution-api-production-2227.up.railway.app")
WPP_KEY       = os.getenv("WPP_API_KEY",    "monaco123")
WPP_INSTANCIA = os.getenv("WPP_INSTANCIA",  "teste")
GRUPO_OPS     = os.getenv("GRUPO_OPERACOES", "120363403884174816@g.us")

DASHBOARD_URL = "https://barbacovi76-ux.github.io/monaco-bm-monitor/saldos_dash.html"

LIMITE_CRITICO = 50
LIMITE_BAIXO   = 100


# ── Helpers ───────────────────────────────────────────────────────

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def enviar_whatsapp(mensagem: str) -> bool:
    url = f"{WPP_URL}/message/sendText/{WPP_INSTANCIA}"
    headers = {"apikey": WPP_KEY, "Content-Type": "application/json"}
    payload = {"number": GRUPO_OPS, "textMessage": {"text": mensagem}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERRO] WhatsApp: {e}")
        return False


def consultar_via_browser(token: str) -> list:
    """Abre a página via Playwright, injeta o token e coleta os saldos."""
    resultados = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Injeta o token no localStorage antes da página carregar
        page.goto(DASHBOARD_URL)
        page.evaluate(f"localStorage.setItem('monaco_meta_token', '{token}')")

        # Recarrega para a página usar o token
        page.reload()
        page.wait_for_load_state("networkidle", timeout=5000)

        # Clica em Atualizar e aguarda carregar todos os saldos
        print("Iniciando consulta via browser headless...")
        page.click("#btn-atualizar")

        # Aguarda até a tabela ter linhas reais (máx 60s para 13 contas)
        page.wait_for_function(
            "document.querySelectorAll('#tbody tr td:first-child .nome-cell').length >= 27",
            timeout=60000
        )

        # Coleta os dados de dadosSaldos via JS
        resultados = page.evaluate("""
            () => dadosSaldos.map(d => ({
                nome: d.nome,
                saldo: d.saldo,
                status: d.status,
                erro: d.erro || false
            }))
        """)
        browser.close()
    return resultados


# ── Main ─────────────────────────────────────────────────────────

def main():
    from datetime import datetime
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"=== Verificação de saldos — {agora} ===")

    token = obter_token()
    if not token:
        print("[ERRO] Token Meta não encontrado. Defina META_TOKEN ou verifique config.json")
        sys.exit(1)

    try:
        dados = consultar_via_browser(token)
    except Exception as e:
        print(f"[ERRO] Falha no browser headless: {e}")
        sys.exit(1)

    criticos = [d for d in dados if d["status"] == "critico" and not d["erro"]]
    baixos   = [d for d in dados if d["status"] == "baixo"   and not d["erro"]]
    ok_count = len([d for d in dados if d["status"] == "ok"])

    print(f"Resultado: {len(criticos)} crítico(s), {len(baixos)} baixo(s), {ok_count} ok")

    if not criticos and not baixos:
        print("Nenhum alerta necessário. Encerrando.")
        return

    # Montar mensagem
    linhas = ["🤖 BOB Saldos — Monaco Agency", agora, ""]
    if criticos:
        linhas.append(f"🔴 CRÍTICO ({len(criticos)})")
        for d in sorted(criticos, key=lambda x: x["saldo"]):
            linhas.append(f"  · {d['nome']} → {fmt_brl(d['saldo'])}")
        linhas.append("")
    if baixos:
        linhas.append(f"🟡 BAIXO ({len(baixos)})")
        for d in sorted(baixos, key=lambda x: x["saldo"]):
            linhas.append(f"  · {d['nome']} → {fmt_brl(d['saldo'])}")
        linhas.append("")
    linhas.append("Acesse: " + DASHBOARD_URL)

    mensagem = "\n".join(linhas)
    print("\nEnviando alerta WhatsApp...")
    print(mensagem)

    ok = enviar_whatsapp(mensagem)
    print("✅ Alerta enviado!" if ok else "❌ Falha ao enviar.")


if __name__ == "__main__":
    main()
