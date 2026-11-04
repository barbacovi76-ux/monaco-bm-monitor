#!/usr/bin/env python3
"""
Verificação automática de saldos das BMs — Monaco Agency
Roda diariamente às 16h (BRT) e envia alerta no grupo de operações via WhatsApp
se houver contas críticas (≤ R$50) ou baixas (≤ R$100).
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).parent

# Credenciais WhatsApp (Evolution API)
WPP_URL       = os.getenv("WPP_API_URL",    "https://evolution-api-production-2227.up.railway.app")
WPP_KEY       = os.getenv("WPP_API_KEY",    "monaco123")
WPP_INSTANCIA = os.getenv("WPP_INSTANCIA",  "teste")
GRUPO_OPS     = os.getenv("GRUPO_OPERACOES", "120363403884174816@g.us")

# Meta API
API_VERSION    = "v19.0"
META_TOKEN_ENV = os.getenv("META_TOKEN", "")

LIMITE_CRITICO = 50
LIMITE_BAIXO   = 100

CONTAS = [
    {"nome": "Rosa Sul Nova",           "id": "act_2523170184768797"},
    {"nome": "Mollinari",               "id": "act_459274303920372"},
    {"nome": "Villa Grano",             "id": "act_909424425271250"},
    {"nome": "Brados",                  "id": "act_972023765779926"},
    {"nome": "Berlim",                  "id": "act_836447545843342"},
    {"nome": "CA RJK SHOP",             "id": "act_297417165372711"},
    {"nome": "CA - Miotto Construtora", "id": "act_213109970735074"},
    {"nome": "CA - ICGP",               "id": "act_360815898753195"},
    {"nome": "CA - Monaco Agency",      "id": "act_732966175219099"},
    {"nome": "BRUNA MACHADO - DOTCON",  "id": "act_1102427261426373"},
    {"nome": "CA - AMK Estética",       "id": "act_590117117342811"},
    {"nome": "JS - UNIFORME",           "id": "act_1452225369942067"},
    {"nome": "SH Tijolos",              "id": "act_3858259327816511"},
]


# ── Helpers ───────────────────────────────────────────────────────

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def obter_token() -> str:
    """Tenta META_TOKEN env → config.json → vazio."""
    if META_TOKEN_ENV:
        return META_TOKEN_ENV
    cfg_path = BACKEND_DIR / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            # formato legado: meta.contas[0].access_token
            contas = cfg.get("meta", {}).get("contas", [])
            if contas:
                return contas[0].get("access_token", "")
        except Exception:
            pass
    return ""


def consultar_saldo(account_id: str, token: str) -> dict | None:
    try:
        url = f"https://graph.facebook.com/{API_VERSION}/{account_id}"
        r = requests.get(
            url,
            params={"fields": "name,balance,spend_cap,amount_spent", "access_token": token},
            timeout=15,
        )
        d = r.json()
        if "error" in d:
            print(f"[ERRO] {account_id}: {d['error'].get('message')}")
            return None
        raw_sc = int(d.get("spend_cap", 0))
        raw_as = int(d.get("amount_spent", 0))
        raw_bal = int(d.get("balance", 0))
        spend_cap    = raw_sc / 100
        amount_spent = raw_as / 100
        saldo = (spend_cap - amount_spent) if spend_cap > 0 else raw_bal / 100
        return {"saldo": saldo}
    except Exception as e:
        print(f"[ERRO] {account_id}: {e}")
        return None


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
        print("[ERRO] Token Meta não encontrado. Defina META_TOKEN ou verifique config.json")
        return

    criticos = []
    baixos   = []
    ok_count = 0

    for conta in CONTAS:
        print(f"Consultando: {conta['nome']}...")
        resultado = consultar_saldo(conta["id"], token)
        if resultado is None:
            continue
        saldo = resultado["saldo"]
        print(f"  Saldo: {fmt_brl(saldo)}")
        if saldo <= LIMITE_CRITICO:
            criticos.append({"nome": conta["nome"], "saldo": saldo})
        elif saldo <= LIMITE_BAIXO:
            baixos.append({"nome": conta["nome"], "saldo": saldo})
        else:
            ok_count += 1

    print(f"\nResultado: {len(criticos)} crítico(s), {len(baixos)} baixo(s), {ok_count} ok")

    if not criticos and not baixos:
        print("Nenhum alerta necessário. Encerrando.")
        return

    # Montar mensagem
    linhas = [
        "🤖 BOB Saldos — Monaco Agency",
        agora,
        "",
    ]
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
    linhas.append("Acesse: https://barbacovi76-ux.github.io/monaco-bm-monitor/saldos_dash.html")

    mensagem = "\n".join(linhas)
    print("\nEnviando alerta WhatsApp...")
    print(mensagem)

    ok = enviar_whatsapp(mensagem)
    if ok:
        print("\n✅ Alerta enviado com sucesso!")
    else:
        print("\n❌ Falha ao enviar alerta.")


if __name__ == "__main__":
    main()
