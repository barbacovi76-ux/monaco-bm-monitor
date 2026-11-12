import json
import os
import requests

# ── Config ──────────────────────────────────────────────────────────
import os as _os
_base = _os.path.dirname(_os.path.abspath(__file__))
cfg    = json.load(open(_os.path.join(_base, 'config.json')))
token  = os.getenv("META_TOKEN", "")

WPP_URL   = os.getenv("WPP_API_URL",  "https://evolution-api-production-2227.up.railway.app")
WPP_KEY   = os.getenv("WPP_API_KEY",  "monaco123")
WPP_INST  = os.getenv("WPP_INSTANCIA","teste")
WPP_DEST  = os.getenv("WPP_DESTINO",  "120363403884174816@g.us")

if not token:
    print("❌ META_TOKEN não definido")
    exit(1)

# ── Buscar saldos ────────────────────────────────────────────────────
contas_ativas = [c for c in cfg['contas'] if c.get('ativo', True)]

criticos, baixos, ok, erros = [], [], [], []

for c in contas_ativas:
    nome = c.get('nome_exibicao') or c.get('nome', c['account_id'])
    lim_crit = c.get('limite_critico', 50)
    lim_baixo = c.get('limite_baixo', 150)
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/{c['account_id']}",
            params={'fields': 'name,balance,spend_cap,amount_spent', 'access_token': token},
            timeout=15
        ).json()
        if 'error' in r:
            erros.append(f"{nome}: {r['error'].get('message','erro desconhecido')}")
            continue
        raw_sc = int(r.get('spend_cap', 0))
        raw_as = int(r.get('amount_spent', 0))
        bal = (raw_sc - raw_as) / 100 if raw_sc > 0 else int(r.get('balance', 0)) / 100

        if bal <= lim_crit:
            criticos.append((nome, bal))
        elif bal <= lim_baixo:
            baixos.append((nome, bal))
        else:
            ok.append((nome, bal))
    except Exception as e:
        erros.append(f"{nome}: {e}")

# ── Montar mensagem ──────────────────────────────────────────────────
linhas = ["💰 *SALDOS DAS CONTAS — Monaco Agency*\n"]

if criticos:
    linhas.append(f"🔴 *CRÍTICO* ({len(criticos)} conta(s)):")
    for n, b in sorted(criticos, key=lambda x: x[1]):
        linhas.append(f"   • {n}: R$ {b:.2f}")
    linhas.append("")

if baixos:
    linhas.append(f"🟡 *BAIXO* ({len(baixos)} conta(s)):")
    for n, b in sorted(baixos, key=lambda x: x[1]):
        linhas.append(f"   • {n}: R$ {b:.2f}")
    linhas.append("")

if ok:
    linhas.append(f"🟢 *OK* ({len(ok)} conta(s)):")
    for n, b in sorted(ok, key=lambda x: x[1], reverse=True):
        linhas.append(f"   • {n}: R$ {b:.2f}")
    linhas.append("")

if erros:
    linhas.append(f"⚠️ *Erros* ({len(erros)}):")
    for e in erros:
        linhas.append(f"   • {e}")
    linhas.append("")

linhas.append(f"Total: {len(criticos)+len(baixos)+len(ok)} contas consultadas")
mensagem = "\n".join(linhas)
print(mensagem)

# ── Enviar WhatsApp ──────────────────────────────────────────────────
if not WPP_KEY:
    print("\n⚠️  WPP_API_KEY não definida — mensagem não enviada")
    exit(0)

url = f"{WPP_URL}/message/sendText/{WPP_INST}"
payload = {"number": WPP_DEST, "text": mensagem}
headers = {"apikey": WPP_KEY, "Content-Type": "application/json"}

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code == 200:
        print("\n✅ Mensagem enviada no WhatsApp")
    else:
        print(f"\n❌ Falha ao enviar: {resp.status_code} — {resp.text[:200]}")
except Exception as e:
    print(f"\n❌ Erro ao enviar WhatsApp: {e}")
