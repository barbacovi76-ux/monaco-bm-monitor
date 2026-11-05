#!/usr/bin/env python3
"""
Verificação diária de campanhas e conjuntos de anúncios próximos ao encerramento.
Roda todos os dias às 08h BRT.
Alerta no grupo de operações via WhatsApp se houver:
  - Campanhas/conjuntos que encerraram ontem
  - Campanhas/conjuntos que encerram hoje
  - Campanhas/conjuntos que encerram nos próximos 3 dias
"""

import json
import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent

META_TOKEN   = os.getenv("META_TOKEN", "")
API_VERSION  = "v19.0"

WPP_URL      = os.getenv("WPP_API_URL",    "https://evolution-api-production-2227.up.railway.app")
WPP_KEY      = os.getenv("WPP_API_KEY",    "monaco123")
WPP_INSTANCIA = os.getenv("WPP_INSTANCIA", "teste")
GRUPO_OPS    = os.getenv("GRUPO_OPERACOES","120363403884174816@g.us")

DASHBOARD_URL = "https://barbacovi76-ux.github.io/monaco-bm-monitor/saldos_dash.html"


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


def buscar_itens(account_id: str, token: str, tipo: str) -> list:
    """Busca campanhas ou conjuntos de anúncios com stop_time definido."""
    endpoint = "campaigns" if tipo == "campanha" else "adsets"
    campos   = "id,name,status,effective_status,stop_time"
    url = (f"https://graph.facebook.com/{API_VERSION}/{account_id}/{endpoint}"
           f"?fields={campos}&limit=100&access_token={token}")
    itens = []
    while url:
        try:
            r = requests.get(url, timeout=20)
            data = r.json()
            if "error" in data:
                print(f"  [AVISO] {data['error'].get('message', '')}")
                break
            itens.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
        except Exception as e:
            print(f"  [ERRO] {e}")
            break
    return itens


def main():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"=== Verificação de encerramentos — {agora} ===")

    token = obter_token()
    if not token:
        print("[ERRO] Token Meta não encontrado.")
        sys.exit(1)

    contas = carregar_contas()
    if not contas:
        print("[ERRO] Nenhuma conta ativa no config.json.")
        sys.exit(1)

    print(f"Verificando {len(contas)} contas...")

    hoje   = datetime.now(timezone.utc).date()
    ontem  = hoje - timedelta(days=1)
    em3    = hoje + timedelta(days=3)

    encerradas      = []  # stop_time == ontem
    encerrando_hoje = []  # stop_time == hoje
    encerrando_em3  = []  # stop_time em 1-3 dias

    for conta in contas:
        aid  = conta["account_id"]
        nome = conta["nome"]
        print(f"  {nome}...")

        for tipo in ("campanha", "conjunto"):
            itens = buscar_itens(aid, token, tipo)
            for item in itens:
                stop = item.get("stop_time")
                if not stop:
                    continue
                try:
                    stop_date = datetime.fromisoformat(stop.replace("Z", "+00:00")).date()
                except Exception:
                    continue

                entry = {
                    "bm":   nome,
                    "nome": item["name"],
                    "tipo": tipo,
                    "data": stop_date.strftime("%d/%m/%Y"),
                    "status": item.get("effective_status", item.get("status", "")),
                }

                if stop_date == ontem:
                    encerradas.append(entry)
                elif stop_date == hoje:
                    encerrando_hoje.append(entry)
                elif hoje < stop_date <= em3:
                    entry["dias"] = (stop_date - hoje).days
                    encerrando_em3.append(entry)

    total = len(encerradas) + len(encerrando_hoje) + len(encerrando_em3)
    print(f"Resultado: {len(encerradas)} encerradas ontem | {len(encerrando_hoje)} hoje | {len(encerrando_em3)} nos próximos 3 dias")

    if total == 0:
        print("Nenhum encerramento detectado. Encerrando.")
        return

    # Montar mensagem
    linhas = ["📋 BOB Encerramentos — Monaco Agency", agora, ""]

    if encerradas:
        linhas.append(f"🔴 ENCERRADAS ONTEM ({len(encerradas)})")
        for c in encerradas:
            tipo_label = "🗂 Camp" if c["tipo"] == "campanha" else "📦 Conj"
            linhas.append(f"  {tipo_label} · {c['bm']}")
            linhas.append(f"  → {c['nome']}")
            linhas.append(f"  Encerrou em {c['data']} | Ação: duplicar ou criar nova")
            linhas.append("")

    if encerrando_hoje:
        linhas.append(f"🟠 ENCERRAM HOJE ({len(encerrando_hoje)})")
        for c in encerrando_hoje:
            tipo_label = "🗂 Camp" if c["tipo"] == "campanha" else "📦 Conj"
            linhas.append(f"  {tipo_label} · {c['bm']}")
            linhas.append(f"  → {c['nome']}")
            linhas.append(f"  Encerra hoje ({c['data']}) | Ação: renovar agora!")
            linhas.append("")

    if encerrando_em3:
        linhas.append(f"🟡 ENCERRAM EM ATÉ 3 DIAS ({len(encerrando_em3)})")
        for c in sorted(encerrando_em3, key=lambda x: x["dias"]):
            tipo_label = "🗂 Camp" if c["tipo"] == "campanha" else "📦 Conj"
            dias_txt = "amanhã" if c["dias"] == 1 else f"em {c['dias']} dias"
            linhas.append(f"  {tipo_label} · {c['bm']}")
            linhas.append(f"  → {c['nome']}")
            linhas.append(f"  Encerra {dias_txt} ({c['data']})")
            linhas.append("")

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append(f"Total: {len(encerradas)} ontem | {len(encerrando_hoje)} hoje | {len(encerrando_em3)} em até 3 dias")
    linhas.append(DASHBOARD_URL)

    mensagem = "\n".join(linhas)
    print("\nEnviando alerta WhatsApp...")
    print(mensagem)

    ok = enviar_whatsapp(mensagem)
    print("✅ Alerta enviado!" if ok else "❌ Falha ao enviar.")


if __name__ == "__main__":
    main()
