#!/usr/bin/env python3
"""
Verificação automática de saldos das BMs — Monaco Agency
Roda diariamente às 16h BRT (19h UTC).
Chama a Meta API diretamente, sem browser.
Envia alerta no grupo de operações via WhatsApp se houver contas
críticas (≤ R$50) ou baixas (≤ R$100).
"""

import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent

META_TOKEN    = os.getenv("META_TOKEN", "")
API_VERSION   = "v19.0"

WPP_URL       = os.getenv("WPP_API_URL",    "https://evolution-api-production-2227.up.railway.app")
WPP_KEY       = os.getenv("WPP_API_KEY",    "monaco123")
WPP_INSTANCIA = os.getenv("WPP_INSTANCIA",  "teste")
GRUPO_OPS     = os.getenv("GRUPO_OPERACOES", "120363403884174816@g.us")

DASHBOARD_URL  = "https://barbacovi76-ux.github.io/monaco-bm-monitor/saldos_dash.html"
LIMITE_CRITICO = 50
LIMITE_BAIXO   = 100


# ── Helpers ───────────────────────────────────────────────────────

def obter_token() -> str:
    if META_TOKEN:
        return META_TOKEN
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


def carregar_contas() -> list:
    """Carrega lista de contas do config.json."""
    cfg_path = BACKEND_DIR / "config.json"
    if not cfg_path.exists():
        return []
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    contas_cfg = cfg.get("contas") or cfg.get("meta", {}).get("contas", [])
    return [
        {
            "nome": c.get("nome_exibicao") or c.get("nome", c["account_id"]),
            "account_id": c["account_id"],
        }
        for c in contas_cfg if c.get("ativo", True)
    ]


def calcular_saldo(d: dict) -> float:
    """
    Mesma lógica do saldos_dash.html:
    - Se tiver spend_cap > 0: saldo = spend_cap - amount_spent
    - Caso contrário: saldo = balance / 100
    Valores da API vêm em centavos × 100.
    """
    raw_as  = int(d.get("amount_spent", 0) or 0)
    raw_bal = int(d.get("balance", 0) or 0)
    raw_sc  = int(d.get("spend_cap", 0) or 0)

    amount_spent = raw_as / 100
    spend_cap    = raw_sc / 100

    if spend_cap > 0:
        return spend_cap - amount_spent
    return raw_bal / 100


def get_status(saldo: float) -> str:
    if saldo <= LIMITE_CRITICO:
        return "critico"
    if saldo <= LIMITE_BAIXO:
        return "baixo"
    return "ok"


def consultar_saldo(account_id: str, token: str) -> dict:
    url = (
        f"https://graph.facebook.com/{API_VERSION}/{account_id}"
        f"?fields=name,balance,spend_cap,amount_spent,account_status"
        f"&access_token={token}"
    )
    try:
        r = requests.get(url, timeout=15)
        d = r.json()
        if "error" in d:
            return {"erro": True, "msg": d["error"].get("message", "")}
        saldo = calcular_saldo(d)
        return {"saldo": saldo, "status": get_status(saldo), "erro": False}
    except Exception as e:
        return {"erro": True, "msg": str(e)}


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


# ── Main ─────────────────────────────────────────────────────────

def main():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"=== Verificação de saldos — {agora} ===")

    token = obter_token()
    if not token:
        print("[ERRO] Token Meta não encontrado.")
        sys.exit(1)

    contas = carregar_contas()
    if not contas:
        print("[ERRO] Nenhuma conta ativa no config.json.")
        sys.exit(1)

    print(f"Verificando {len(contas)} contas...")

    criticos = []
    baixos   = []
    erros    = 0

    for conta in contas:
        aid  = conta["account_id"]
        nome = conta["nome"]
        res  = consultar_saldo(aid, token)

        if res.get("erro"):
            print(f"  [ERRO] {nome}: {res.get('msg','')}")
            erros += 1
            continue

        saldo  = res["saldo"]
        status = res["status"]
        print(f"  {nome}: {fmt_brl(saldo)} ({status})")

        if status == "critico":
            criticos.append({"nome": nome, "saldo": saldo})
        elif status == "baixo":
            baixos.append({"nome": nome, "saldo": saldo})

    print(f"\nResultado: {len(criticos)} crítico(s), {len(baixos)} baixo(s), {erros} erro(s)")

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
    print("\nMensagem:")
    print(mensagem)
    print("\nEnviando alerta WhatsApp...")

    ok = enviar_whatsapp(mensagem)
    print("✅ Alerta enviado!" if ok else "❌ Falha ao enviar.")


if __name__ == "__main__":
    main()
