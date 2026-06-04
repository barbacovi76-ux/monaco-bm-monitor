"""
Auditoria 60 dias — Monaco Agency
Roda no seu PC e gera o relatório completo
"""
import requests
import json
from datetime import date, timedelta

TOKEN = "EAAZAXnO7BzBwBRevRp5kVDqV6ZBZCaqZAdtnyKYTjVZBYZCoKuqDvEWbugHchidDZAsowsNJMES7wxjBdUsIxxVvlD1ZC6K4lksjKBmGRw17JxFAru0mH5Bq5lIRubAeSpx93nAggIeQsb16j6iQkFQvbDutNFnAM9dvkgDrJFZChZAcopaV6DTHP56zmHUugGfwZDZD"
API = "v19.0"

CONTAS_FOOD = [
    ("CA - ROSA SUL NOVA", "act_2523170184768797"),
    ("Dia de Pizza - Dourados", "act_723575425785405"),
    ("IH CAMPO GRANDE MS", "act_1131240581799095"),
    ("Mollinari Pizzaria", "act_459274303920372"),
    ("MrGabs", "act_728296823243425"),
    ("IH DOURADOS", "act_831936562721815"),
    ("CA - Bella Capri Uberlândia", "act_2379679152502158"),
    ("Villa Grano Pizzaria", "act_909424425271250"),
    ("Brados Pizzaria", "act_972023765779926"),
    ("Berlim Pizzaria", "act_836447545843342"),
    ("A FAVORITA", "act_969681458906352"),
    ("CA - BRAVA PIZZA", "act_4279801688941861"),
    ("Pavão Lanchonete", "act_1759603645448352"),
    ("Fornalha Pizzaria", "act_1618084519451450"),
    ("Ótica Scherer", "act_1179077680434286"),
]

hoje = date.today()
since_60 = (hoje - timedelta(days=60)).strftime("%Y-%m-%d")
until_hoje = hoje.strftime("%Y-%m-%d")
since_30 = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
since_31_60 = (hoje - timedelta(days=60)).strftime("%Y-%m-%d")
until_31_60 = (hoje - timedelta(days=31)).strftime("%Y-%m-%d")

def fmt(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def get_insights(account_id, since, until):
    url = f"https://graph.facebook.com/{API}/{account_id}/insights"
    params = {
        "fields": "spend,impressions,reach,frequency,clicks,actions,action_values",
        "time_range": json.dumps({"since": since, "until": until}),
        "access_token": TOKEN,
    }
    r = requests.get(url, params=params, timeout=20)
    d = r.json()
    if "error" in d:
        return None
    ins = d.get("data", [{}])[0] if d.get("data") else {}
    gasto = float(ins.get("spend", 0))
    impr = int(ins.get("impressions", 0))
    reach = int(ins.get("reach", 0))
    freq = float(ins.get("frequency", 0))
    clicks = int(ins.get("clicks", 0))
    actions = ins.get("actions", [])
    avs = ins.get("action_values", [])
    pedidos = int(next((a["value"] for a in actions if a["action_type"] == "purchase"), 0))
    fat = float(next((a["value"] for a in avs if a["action_type"] == "purchase"), 0))
    lp = int(next((a["value"] for a in actions if a["action_type"] == "landing_page_view"), 0))
    cart = int(next((a["value"] for a in actions if a["action_type"] == "add_to_cart"), 0))
    checkout = int(next((a["value"] for a in actions if a["action_type"] == "initiate_checkout"), 0))
    cpr = gasto / pedidos if pedidos > 0 else 0
    roas = fat / gasto if gasto > 0 and fat > 0 else 0
    ticket = fat / pedidos if pedidos > 0 else 0
    ctr = (clicks / impr * 100) if impr > 0 else 0
    conv_lp = (pedidos / lp * 100) if lp > 0 else 0
    return dict(gasto=gasto, impr=impr, reach=reach, freq=freq, clicks=clicks,
                pedidos=pedidos, fat=fat, lp=lp, cart=cart, checkout=checkout,
                cpr=cpr, roas=roas, ticket=ticket, ctr=ctr, conv_lp=conv_lp)

resultados = []
print(f"Auditoria 60 dias: {since_60} até {until_hoje}\n")
print("Consultando BMs...")

for nome, account_id in CONTAS_FOOD:
    print(f"  {nome}...", end=" ")
    total = get_insights(account_id, since_60, until_hoje)
    m1 = get_insights(account_id, since_31_60, until_31_60)
    m2 = get_insights(account_id, since_30, until_hoje)
    if total:
        resultados.append({"nome": nome, "id": account_id, "total": total, "m1": m1 or {}, "m2": m2 or {}})
        print(f"✅ R${total['gasto']:.0f} | {total['pedidos']} pedidos | ROAS {total['roas']:.2f}x")
    else:
        print("❌ Erro")

# Salvar JSON para o relatório
with open("auditoria_dados.json", "w", encoding="utf-8") as f:
    json.dump({"gerado_em": str(hoje), "periodo": f"{since_60} a {until_hoje}", "dados": resultados}, f, ensure_ascii=False, indent=2)

print(f"\n✅ Dados salvos em auditoria_dados.json")
print(f"Total de BMs: {len(resultados)}")
print("\nAgora rode: python auditoria_relatorio.py")
