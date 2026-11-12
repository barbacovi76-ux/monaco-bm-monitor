"""
Script standalone para verificar campanhas encerradas/encerrando.
Roda via GitHub Actions (encerramentos_diario.yml).
"""
import json
import os
import requests
from datetime import datetime, timedelta, timezone

# ── Config ──────────────────────────────────────────────────────────
import os as _os
_base = _os.path.dirname(_os.path.abspath(__file__))
cfg   = json.load(open(_os.path.join(_base, 'config.json')))

token    = os.getenv("META_TOKEN", "")
WPP_URL  = os.getenv("WPP_API_URL",  "https://evolution-api-production-2227.up.railway.app")
WPP_KEY  = os.getenv("WPP_API_KEY",  "monaco123")
WPP_INST = os.getenv("WPP_INSTANCIA","teste")
WPP_DEST = os.getenv("WPP_DESTINO",  "120363403884174816@g.us")

if not token:
    print("❌ META_TOKEN não definido")
    exit(1)

API_VERSION = cfg.get("meta", {}).get("api_version", "v19.0")
contas_ativas = [c for c in cfg['contas'] if c.get('ativo', True)]

hoje  = datetime.now(timezone.utc).date()
ontem = hoje - timedelta(days=1)

encerradas      = []
encerrando_hoje = []
erros           = []

print(f"Verificando encerramentos — {hoje.strftime('%d/%m/%Y')}")

for c in contas_ativas:
    nome = c.get('nome_exibicao') or c.get('nome', c['account_id'])
    try:
        campanhas = []
        url = (f"https://graph.facebook.com/{API_VERSION}/{c['account_id']}/campaigns"
               f"?fields=id,name,status,effective_status,stop_time"
               f"&limit=100&access_token={token}")
        while url:
            r = requests.get(url, timeout=20).json()
            if 'error' in r:
                erros.append(f"{nome}: {r['error'].get('message','erro')}")
                break
            campanhas.extend(r.get("data", []))
            url = r.get("paging", {}).get("next")

        for camp in campanhas:
            stop = camp.get("stop_time")
            if not stop:
                continue
            stop_date = datetime.fromisoformat(stop.replace("Z", "+00:00")).date()
            item = {"bm": nome, "camp": camp["name"], "data": stop_date.strftime("%d/%m/%Y")}
            if stop_date == ontem:
                encerradas.append(item)
            elif stop_date == hoje:
                encerrando_hoje.append(item)

    except Exception as e:
        erros.append(f"{nome}: {e}")

# ── Montar mensagem ──────────────────────────────────────────────────
if not encerradas and not encerrando_hoje:
    print("✅ Nenhum encerramento detectado.")
    exit(0)

agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
linhas = [f"⏰ *ENCERRAMENTOS — Monaco Agency*", f"_{agora_str}_", ""]

if encerradas:
    linhas.append(f"🔴 *ENCERRADAS ONTEM* ({len(encerradas)})")
    for item in encerradas:
        linhas.append(f"   • *{item['bm']}*")
        linhas.append(f"     {item['camp']}")
        linhas.append(f"     Encerrou: {item['data']}")
    linhas.append("")

if encerrando_hoje:
    linhas.append(f"🟡 *ENCERRAM HOJE* ({len(encerrando_hoje)})")
    for item in encerrando_hoje:
        linhas.append(f"   • *{item['bm']}*")
        linhas.append(f"     {item['camp']}")
        linhas.append(f"     Encerra: {item['data']}")
    linhas.append("")

if erros:
    linhas.append(f"⚠️ *Erros* ({len(erros)}):")
    for e in erros:
        linhas.append(f"   • {e}")
    linhas.append("")

linhas.append(f"Total: {len(encerradas)} encerrada(s) ontem | {len(encerrando_hoje)} encerrando hoje")

mensagem = "\n".join(linhas)
print(mensagem)

# ── Enviar WhatsApp ──────────────────────────────────────────────────
url     = f"{WPP_URL}/message/sendText/{WPP_INST}"
payload = {"number": WPP_DEST, "textMessage": {"text": mensagem}}
headers = {"apikey": WPP_KEY, "Content-Type": "application/json"}

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code in (200, 201):
        print("\n✅ Mensagem enviada no WhatsApp")
    else:
        print(f"\n❌ Falha ao enviar: {resp.status_code} — {resp.text[:200]}")
except Exception as e:
    print(f"\n❌ Erro ao enviar WhatsApp: {e}")
