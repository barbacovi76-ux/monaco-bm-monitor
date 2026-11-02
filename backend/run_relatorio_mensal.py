"""
Relatório mensal automático — Monaco Agency BM Monitor
Roda no dia 1º de cada mês via GitHub Actions.
Busca dados do mês anterior para cada cliente ativo no config.json
e envia uma mensagem por cliente para o grupo único de relatórios.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import date, timedelta
from pathlib import Path
from calendar import monthrange

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH      = Path(__file__).parent / "config.json"
API_VER          = "v19.0"
META_TOKEN       = os.getenv("META_TOKEN", "")
WPP_API_URL      = os.getenv("WPP_API_URL", "https://evolution-api-production-2227.up.railway.app")
WPP_API_KEY      = os.getenv("WPP_API_KEY", "")
WPP_INSTANCIA    = os.getenv("WPP_INSTANCIA", "teste")
GRUPO_RELATORIOS = os.getenv("GRUPO_RELATORIOS", "120363403884174816@g.us")
DELAY_ENTRE_MSGS = 1.5  # segundos entre envios

FOOD_KEYWORDS = [
    "pizza", "grano", "berlin", "berlim", "rosa sul", "mollinari", "brados",
    "pavao", "paváo", "dia de pizza", "brava", "favorita", "fornalha", "alho",
    "duba", "bistrô", "bistro", "villas", "perché", "perche", "bari",
    "eskinado", "pizza e cia", "masters",
]

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_brl(v: float) -> str:
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def fmt_int(v: float) -> str:
    return f"{int(v):,}".replace(",", ".")


def periodo_mes_anterior():
    hoje = date.today()
    primeiro_do_mes = hoje.replace(day=1)
    ultimo_anterior = primeiro_do_mes - timedelta(days=1)
    primeiro_anterior = ultimo_anterior.replace(day=1)
    return str(primeiro_anterior), str(ultimo_anterior)


def is_food(conta: dict) -> bool:
    n = (conta.get("nome") or "").lower()
    if conta.get("metodo_forcado") == "Vendas":
        return True
    return any(k in n for k in FOOD_KEYWORDS)


def get_action(actions: list, tipo: str) -> float:
    if not actions:
        return 0.0
    for a in actions:
        if a.get("action_type") == tipo:
            return float(a.get("value", 0))
    return 0.0


def classificar_campanha(camp: dict, opt_goal_map: dict, conta: dict) -> str:
    if conta.get("metodo_forcado"):
        return conta["metodo_forcado"]
    og  = (opt_goal_map.get(camp.get("campaign_id"), "") or "").upper()
    obj = (camp.get("objective") or "").upper()
    if og == "CONVERSATIONS":
        return "Conversas WhatsApp"
    if obj == "OUTCOME_SALES" or is_food(conta):
        return "Vendas"
    if obj == "OUTCOME_LEADS":
        return "Leads"
    if obj == "OUTCOME_AWARENESS":
        return "Alcance"
    if obj in ("OUTCOME_TRAFFIC", "LINK_CLICKS"):
        return "Tráfego"
    return "Engajamento"


# ── Meta API ──────────────────────────────────────────────────────────────────

def meta_get(url: str, params: dict = None) -> dict:
    params = params or {}
    params["access_token"] = META_TOKEN
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def buscar_insights(account_id: str, since: str, until: str) -> list:
    fields = (
        "campaign_name,campaign_id,objective,spend,reach,impressions,"
        "inline_link_clicks,actions,action_values"
    )
    url = f"https://graph.facebook.com/{API_VER}/{account_id}/insights"
    params = {
        "level": "campaign",
        "time_range": json.dumps({"since": since, "until": until}),
        "fields": fields,
        "limit": 200,
    }
    data = meta_get(url, params)
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "Erro Meta API"))
    return data.get("data", [])


def buscar_opt_goals(account_id: str) -> dict:
    url = f"https://graph.facebook.com/{API_VER}/{account_id}/adsets"
    data = meta_get(url, {"fields": "campaign_id,optimization_goal", "limit": 300})
    mapa = {}
    for a in data.get("data", []):
        cid = a.get("campaign_id")
        if cid and cid not in mapa:
            mapa[cid] = a.get("optimization_goal", "")
    return mapa


def processar_conta(conta: dict, since: str, until: str) -> dict:
    account_id = conta["account_id"]
    try:
        insights     = buscar_insights(account_id, since, until)
        opt_goal_map = buscar_opt_goals(account_id)
    except Exception as e:
        log.warning(f"[{conta['nome']}] Erro ao buscar dados: {e}")
        return {"conta": conta, "metodos": {}, "total_spend": 0.0, "erro": True}

    metodos: dict[str, dict] = {}
    for camp in insights:
        metodo = classificar_campanha(camp, opt_goal_map, conta)
        if metodo not in metodos:
            metodos[metodo] = dict(
                spend=0, reach=0, impressions=0, clicks=0,
                purchases=0, purchase_value=0, cart_adds=0, page_views=0,
                conversations=0, leads=0,
            )
        m = metodos[metodo]
        actions       = camp.get("actions", [])
        action_values = camp.get("action_values", [])
        m["spend"]     += float(camp.get("spend", 0))
        m["reach"]     += float(camp.get("reach", 0))
        m["impressions"] += float(camp.get("impressions", 0))
        m["clicks"]    += float(camp.get("inline_link_clicks", 0))
        purch = get_action(actions, "omni_purchase") or get_action(actions, "purchase")
        m["purchases"] += purch
        purch_val = get_action(action_values, "omni_purchase") or get_action(action_values, "purchase")
        m["purchase_value"] += purch_val
        m["cart_adds"]  += (get_action(actions, "omni_add_to_cart") or get_action(actions, "add_to_cart"))
        m["page_views"] += (get_action(actions, "landing_page_view") or get_action(actions, "omni_landing_page_view"))
        m["conversations"] += get_action(actions, "onsite_conversion.messaging_conversation_started_7d")
        m["leads"]     += (get_action(actions, "lead") or get_action(actions, "onsite_conversion.lead_grouped"))

    total_spend = sum(v["spend"] for v in metodos.values())
    return {"conta": conta, "metodos": metodos, "total_spend": total_spend, "erro": False}


# ── Message builder ───────────────────────────────────────────────────────────

def montar_mensagem_mensal(dado: dict, since: str, until: str) -> str:
    d1    = date.fromisoformat(since)
    d2    = date.fromisoformat(until)
    mes   = MESES_PT[d1.month - 1]
    s_str = d1.strftime("%d/%m/%Y")
    u_str = d2.strftime("%d/%m/%Y")

    ORDEM = ["Vendas", "Conversas WhatsApp", "Leads", "Tráfego", "Alcance", "Engajamento"]
    ativos = [m for m in ORDEM if m in dado["metodos"] and dado["metodos"][m]["spend"] > 0]
    multi = len(ativos) > 1

    blocos = []
    EMOJI  = {
        "Vendas": "🚀",
        "Conversas WhatsApp": "💬",
        "Leads": "📋",
        "Tráfego": "👀",
        "Alcance": "📣",
        "Engajamento": "❤️",
    }

    for metodo in ativos:
        m = dado["metodos"][metodo]
        linhas = []

        if multi:
            linhas.append(f"{EMOJI.get(metodo, '')} {metodo}")
            linhas.append(f"Valor investido: {fmt_brl(m['spend'])}")
            linhas.append("")

        if metodo == "Vendas":
            if m["page_views"] > 0:
                linhas.append(f"Visualizações no cardápio: {fmt_int(m['page_views'])}")
            if m["cart_adds"] > 0:
                linhas.append(f"Carrinhos adicionados: {fmt_int(m['cart_adds'])}")
            if m["purchases"] > 0:
                linhas.append(f"Compras: {fmt_int(m['purchases'])}")
            linhas.append(f"Valor vendido: {fmt_brl(m['purchase_value'])}")
            if m["spend"] > 0:
                roas = m["purchase_value"] / m["spend"]
                linhas.append(f"ROAS: {roas:.2f}".replace(".", ","))

        elif metodo == "Conversas WhatsApp":
            linhas.append(f"Pessoas alcançadas: {fmt_int(m['reach'])}")
            linhas.append(f"Conversas iniciadas: {fmt_int(m['conversations'])}")
            if m["conversations"] > 0:
                linhas.append(f"Custo por conversa: {fmt_brl(m['spend'] / m['conversations'])}")

        elif metodo == "Leads":
            linhas.append(f"Pessoas alcançadas: {fmt_int(m['reach'])}")
            linhas.append(f"Leads recebidos: {fmt_int(m['leads'])}")
            if m["leads"] > 0:
                linhas.append(f"Custo por lead: {fmt_brl(m['spend'] / m['leads'])}")

        else:  # Tráfego / Alcance / Engajamento
            linhas.append(f"Pessoas alcançadas: {fmt_int(m['reach'])}")
            linhas.append(f"Cliques: {fmt_int(m['clicks'])}")
            if m["clicks"] > 0 and m["spend"] > 0:
                linhas.append(f"Custo por clique: {fmt_brl(m['spend'] / m['clicks'])}")

        blocos.append("\n".join(linhas))

    total_str = fmt_brl(dado["total_spend"])

    msg = (
        f"Olá pessoal, segue abaixo um resumo com os principais dados e atividades do mês:\n\n"
        f"🚀 Resultados de {mes}, {s_str} até {u_str} :\n\n"
        f"Valor investido: {total_str}\n\n"
        + "\n\n".join(blocos)
        + "\n\n🚀 Seguimos firmes na evolução do projeto, com foco total em performance e melhoria contínua.\n"
          "Desejo a todos um excelente mês!"
    )
    return msg


# ── WhatsApp ──────────────────────────────────────────────────────────────────

def enviar_whatsapp(texto: str, numero: str = GRUPO_RELATORIOS) -> bool:
    url = f"{WPP_API_URL}/message/sendText/{WPP_INSTANCIA}"
    headers = {"apikey": WPP_API_KEY, "Content-Type": "application/json"}
    payload = {"number": numero, "text": texto}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao enviar WhatsApp: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not META_TOKEN:
        log.error("META_TOKEN não definido. Abortando.")
        sys.exit(1)
    if not WPP_API_KEY:
        log.error("WPP_API_KEY não definido. Abortando.")
        sys.exit(1)

    # Load active accounts
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    contas = [c for c in cfg.get("contas", []) if c.get("ativo", True)]
    log.info(f"{len(contas)} contas ativas no config.json")

    # Period: previous month
    since, until = periodo_mes_anterior()
    log.info(f"Período: {since} a {until}")

    enviados = 0
    erros    = 0

    for conta in contas:
        log.info(f"Processando {conta['nome']} ({conta['account_id']})...")
        dado = processar_conta(conta, since, until)

        if dado["total_spend"] <= 0:
            log.info(f"  → Sem investimento. Pulando.")
            continue

        msg = montar_mensagem_mensal(dado, since, until)
        log.info(f"  → Enviando mensagem ({len(msg)} chars)...")

        ok = enviar_whatsapp(msg)
        if ok:
            log.info(f"  → Enviado com sucesso.")
            enviados += 1
        else:
            log.warning(f"  → Falha no envio.")
            erros += 1

        time.sleep(DELAY_ENTRE_MSGS)

    log.info(f"Concluído. Enviados: {enviados} | Erros: {erros}")


if __name__ == "__main__":
    main()
