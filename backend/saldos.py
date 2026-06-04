import json
import requests

cfg = json.load(open('config.json'))
token = cfg['meta']['contas'][0]['access_token']

print('=== SALDOS ATUAIS ===\n')
criticos = []
baixos = []
ok = []

for c in cfg['meta']['contas']:
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{c['account_id']}",
        params={'fields': 'name,balance,spend_cap,amount_spent', 'access_token': token},
        timeout=15
    ).json()
    raw_sc = int(r.get('spend_cap', 0))
    raw_as = int(r.get('amount_spent', 0))
    bal = (raw_sc - raw_as) / 100 if raw_sc > 0 else int(r.get('balance', 0)) / 100

    if bal <= 50:
        criticos.append((c['nome'], bal))
    elif bal <= 100:
        baixos.append((c['nome'], bal))
    else:
        ok.append((c['nome'], bal))

print(f'🔴 CRÍTICO (abaixo de R$ 50) — {len(criticos)} conta(s):')
for n, b in sorted(criticos, key=lambda x: x[1]):
    print(f'   {n}: R$ {b:.2f}')

print(f'\n🟡 BAIXO (R$ 50 a R$ 100) — {len(baixos)} conta(s):')
for n, b in sorted(baixos, key=lambda x: x[1]):
    print(f'   {n}: R$ {b:.2f}')

print(f'\n🟢 OK (acima de R$ 100) — {len(ok)} conta(s):')
for n, b in sorted(ok, key=lambda x: x[1], reverse=True):
    print(f'   {n}: R$ {b:.2f}')
