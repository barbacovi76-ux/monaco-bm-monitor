"""
Monitor de Saldo de BMs do Meta
Consulta saldo via API do Meta e dispara alertas via WhatsApp (Evolution API)
"""

import json
import os
import random
import time
import logging
import requests
from datetime import datetime, date, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"
ALERTAS_LOG = Path(__file__).parent / "alertas_enviados.json"


def carregar_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "meta": {
            "api_version": "v19.0",
            "contas": [
                {"nome": "Rosa Sul Nova", "account_id": "act_2523170184768797", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Dia de Pizza Dourados", "account_id": "act_723575425785405", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "IH Campo Grande", "account_id": "act_1131240581799095", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Mollinari", "account_id": "act_459274303920372", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "MrGabs", "account_id": "act_728296823243425", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "IH Dourados", "account_id": "act_831936562721815", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Villa Grano", "account_id": "act_909424425271250", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Brados", "account_id": "act_972023765779926", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Berlim", "account_id": "act_836447545843342", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "A Favorita", "account_id": "act_969681458906352", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Brava Pizza", "account_id": "act_4279801688941861", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Pavao", "account_id": "act_1759603645448352", "access_token": os.getenv("META_TOKEN", "")},
                {"nome": "Fornalha", "account_id": "act_1618084519451450", "access_token": os.getenv("META_TOKEN", "")},
            ]
        },
        "alertas": {
            "limite_critico": 50,
            "limite_baixo": 100,
            "horario_verificacao": "15:00",
            "alertar_uma_vez_por_dia": True
        },
        "whatsapp": {
            "api_url": os.getenv("WPP_API_URL", "http://localhost:8080"),
            "api_key": os.getenv("WPP_API_KEY", "minhaChave123"),
            "instancia": os.getenv("WPP_INSTANCIA", "meu-whatsapp"),
            "numeros_destino": [os.getenv("GRUPO_OPERACOES", "")]
        }
    }


def carregar_alertas_enviados() -> dict:
    if ALERTAS_LOG.exists():
        with open(ALERTAS_LOG, encoding="utf-8") as f:
            return json.load(f)
    return {}


def salvar_alertas_enviados(dados: dict):
    with open(ALERTAS_LOG, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def consultar_saldo(account_id: str, token: str, api_version: str) -> dict | None:
    url = f"https://graph.facebook.com/{api_version}/{account_id}"
    params = {"fields": "name,balance,spend_cap,amount_spent,currency,account_status", "access_token": token}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            log.error(f"Erro API Meta [{account_id}]: {data['error'].get('message')}")
            return None
        raw_balance = int(data.get("balance", 0))
        raw_spend_cap = int(data.get("spend_cap", 0))
        raw_amount_spent = int(data.get("amount_spent", 0))
        spend_cap = raw_spend_cap / 100
        amount_spent = raw_amount_spent / 100
        balance = (spend_cap - amount_spent) if spend_cap > 0 else raw_balance / 100
        return {"account_id": account_id, "nome": data.get("name", account_id), "balance": balance, "spend_cap": spend_cap, "currency": data.get("currency", "BRL"), "status": data.get("account_status", 1)}
    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao consultar [{account_id}]: {e}")
        return None

FRASES_MOTIVACIONAIS = [
    "Só vive o extraordinário quem arrisca o ordinário.",
    "O mercado não espera. Age agora ou fica para trás.",
    "Cada campanha bem otimizada é dinheiro no bolso do cliente.",
    "Resultado não acontece por acaso. Acontece por estratégia.",
    "Quem não mede, não melhora. Quem não melhora, não cresce.",
    "ROAS alto não é sorte. É trabalho inteligente todos os dias.",
    "Empreender é transformar insegurança em ação.",
    "O dinheiro flui para quem resolve problemas reais.",
    "Cada lead é uma oportunidade. Não desperdice nenhuma.",
    "Consistência vence talento quando o talento é inconsistente.",
    "Seu cliente não compra produto. Compra resultado.",
    "Pequenas otimizações diárias constroem grandes resultados mensais.",
    "Quem domina os dados, domina o mercado.",
    "O medo de errar é mais caro que o erro em si.",
    "Invista no que traz retorno. Corte o que drena.",
    "Um bom anúncio não vende — ele conecta pessoas a soluções.",
    "A diferença entre fracasso e sucesso é uma campanha bem ajustada.",
    "Quem acorda cedo para olhar os dados, dorme tranquilo à noite.",
    "Não existe fórmula mágica. Existe teste, análise e escala.",
    "Seu concorrente também está acordado. A diferença é o que você faz com isso.",
    "Foco no processo. Os resultados são consequência.",
    "Tráfego pago é o acelerador. Estratégia é o motor.",
    "Cada real investido precisa trabalhar por você.",
    "Não venda produto. Venda transformação.",
    "O sucesso do cliente é o seu maior ativo.",
    "Dados não mentem. Ouça o que os números estão dizendo.",
    "Campanha parada é dinheiro perdido. Analise e ajuste sempre.",
    "Quem entende o comportamento do consumidor, controla o jogo.",
    "Escalar um negócio é ciência, não aposta.",
    "O melhor momento para otimizar foi ontem. O segundo melhor é agora.",
]


def gerar_frase_motivacional() -> str:
    dia_do_ano = datetime.now().timetuple().tm_yday
    indice = dia_do_ano % len(FRASES_MOTIVACIONAIS)
    return FRASES_MOTIVACIONAIS[indice]


def enviar_motivacional():
    cfg = carregar_config()
    cfg_wpp = cfg["whatsapp"]
    grupo = cfg_wpp["numeros_destino"][0]
    frase = gerar_frase_motivacional()
    agora = datetime.now().strftime("%d/%m/%Y")
    mensagem = (
        f"🤖 BOB cita:\n\n"
        f"🔥 Bora time, vamos fechar o dia com tudo!\n\n"
        f"{frase}\n\n"
        f"💪 Que hoje seja um dia de grandes resultados!\n"
        f"📅 {agora}"
    )
    log.info("Enviando mensagem motivacional do dia")
    ok = enviar_whatsapp(cfg_wpp, grupo, mensagem)
    if ok:
        log.info("Mensagem motivacional enviada!")
    else:
        log.error("Falha ao enviar mensagem motivacional")
def enviar_whatsapp(cfg_wpp: dict, numero: str, mensagem: str) -> bool:
    url = f"{cfg_wpp['api_url']}/message/sendText/{cfg_wpp['instancia']}"
    headers = {"apikey": cfg_wpp["api_key"], "Content-Type": "application/json"}
    payload = {"number": numero, "textMessage": {"text": mensagem}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        log.info(f"Mensagem enviada para {numero}")
        return True
    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao enviar WhatsApp para {numero}: {e}")
        return False


def montar_mensagem_saldo(conta: dict, nivel: str, limite: float) -> str:
    emoji = "Alerta CRITICO" if nivel == "critico" else "Alerta BAIXO"
    linhas = [
        f"Alerta de Saldo — {emoji}",
        "",
        f"BM: {conta['nome']}",
        f"Saldo atual: {fmt_brl(conta['balance'])}",
        f"Limite de alerta: {fmt_brl(limite)}",
    ]
    if conta["spend_cap"] > 0:
        linhas.append(f"Limite de gasto: {fmt_brl(conta['spend_cap'])}")
    linhas += ["", "Recarregue o saldo para evitar interrupcoes nas campanhas.", f"Horario: {datetime.now().strftime('%d/%m/%Y %H:%M')}"]
    return "\n".join(linhas)


def verificar_e_alertar():
    cfg = carregar_config()
    alertas_enviados = carregar_alertas_enviados()
    hoje = str(date.today())
    limite_critico = cfg["alertas"]["limite_critico"]
    limite_baixo = cfg["alertas"]["limite_baixo"]
    uma_vez_por_dia = cfg["alertas"]["alertar_uma_vez_por_dia"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp = cfg["whatsapp"]
    numeros = cfg_wpp["numeros_destino"]

    log.info(f"=== Verificacao de saldo — {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")

    for conta_cfg in cfg["meta"]["contas"]:
        account_id = conta_cfg["account_id"]
        token = conta_cfg["access_token"]
        nome = conta_cfg["nome"]
        log.info(f"Consultando: {nome} ({account_id})")
        conta = consultar_saldo(account_id, token, api_version)
        if conta is None:
            log.warning(f"Pulando {nome} — erro na consulta")
            continue
        balance = conta["balance"]
        log.info(f"  Saldo: {fmt_brl(balance)}")
        if balance <= limite_critico:
            nivel = "critico"
            limite_ref = limite_critico
        elif balance <= limite_baixo:
            nivel = "baixo"
            limite_ref = limite_baixo
        else:
            log.info(f"  Status: OK")
            if account_id in alertas_enviados:
                del alertas_enviados[account_id]
                salvar_alertas_enviados(alertas_enviados)
            continue
        if uma_vez_por_dia:
            ultimo = alertas_enviados.get(account_id, {})
            if ultimo.get("data") == hoje and ultimo.get("nivel") == nivel:
                log.info(f"  Alerta ja enviado hoje para {nome} — pulando")
                continue
        mensagem = montar_mensagem_saldo(conta, nivel, limite_ref)
        enviou = False
        for numero in numeros:
            ok = enviar_whatsapp(cfg_wpp, numero, mensagem)
            if ok:
                enviou = True
        if enviou:
            alertas_enviados[account_id] = {"data": hoje, "nivel": nivel, "balance": balance, "hora": datetime.now().strftime("%H:%M"), "nome": nome}
            salvar_alertas_enviados(alertas_enviados)

    log.info("=== Verificacao de saldo concluida ===\n")


def consultar_insights(account_id: str, token: str, api_version: str, since: str, until: str) -> dict:
    url = f"https://graph.facebook.com/{api_version}/{account_id}/insights"
    params = {"fields": "spend,actions,action_values", "time_range": f'{{"since":"{since}","until":"{until}"}}', "access_token": token}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if "data" in data and data["data"]:
            ins = data["data"][0]
            gasto = float(ins.get("spend", 0))
            actions = ins.get("actions", [])
            action_values = ins.get("action_values", [])
            pedidos = next((int(a["value"]) for a in actions if a["action_type"] == "purchase"), 0)
            faturamento = next((float(a["value"]) for a in action_values if a["action_type"] == "purchase"), 0.0)
            cpr = gasto / pedidos if pedidos > 0 else 0
            roas = faturamento / gasto if gasto > 0 else 0
            return {"gasto": gasto, "pedidos": pedidos, "faturamento": faturamento, "cpr": cpr, "roas": roas}
    except Exception as e:
        log.error(f"Erro insights [{account_id}]: {e}")
    return {"gasto": 0, "pedidos": 0, "faturamento": 0, "cpr": 0, "roas": 0}


def rodar_agente_automatico():
    cfg = carregar_config()
    token = cfg["meta"]["contas"][0]["access_token"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp = cfg["whatsapp"]
    grupo = cfg_wpp["numeros_destino"][0]

    CONTAS_FOOD = [
        ("CA - ROSA SUL NOVA", "act_2523170184768797"),
        ("Dia de Pizza - Dourados", "act_723575425785405"),
        ("IH CAMPO GRANDE MS", "act_1131240581799095"),
        ("Mollinari Pizzaria", "act_459274303920372"),
        ("MrGabs", "act_728296823243425"),
        ("IH DOURADOS", "act_831936562721815"),
        ("Villa Grano Pizzaria", "act_909424425271250"),
        ("Brados Pizzaria", "act_972023765779926"),
        ("Berlim Pizzaria", "act_836447545843342"),
        ("A FAVORITA", "act_969681458906352"),
        ("CA - BRAVA PIZZA", "act_4279801688941861"),
        ("Pavao Lanchonete", "act_1759603645448352"),
        ("Fornalha Pizzaria", "act_1618084519451450"),
    ]

    log.info("BOB iniciado — analisando campanhas...")
    alertas_criticos = []
    alertas_atencao = []
    hoje = date.today()

    for nome_bm, account_id in CONTAS_FOOD:
        try:
            url = (f"https://graph.facebook.com/{api_version}/{account_id}/campaigns"
                   f"?fields=id,name,status,effective_status,lifetime_budget,daily_budget,"
                   f"budget_remaining,start_time,stop_time,"
                   f"insights.date_preset(last_7d){{spend,actions,action_values}}"
                   f",ads.limit(50){{id,status,effective_status}}"
                   f"&limit=50&access_token={token}")
            r = requests.get(url, timeout=20)
            campanhas = r.json().get("data", [])

            for camp in campanhas:
                status = camp.get("effective_status") or camp.get("status")
                ins = camp.get("insights", {}).get("data", [{}])[0]
                gasto = float(ins.get("spend", 0))
                actions = ins.get("actions", [])
                action_values = ins.get("action_values", [])
                pedidos = int(next((a["value"] for a in actions if a["action_type"] == "purchase"), 0))
                fat = float(next((a["value"] for a in action_values if a["action_type"] == "purchase"), 0))
                roas = fat / gasto if gasto > 0 and fat > 0 else 0
                ads = camp.get("ads", {}).get("data", [])
                ads_ativos = [a for a in ads if a.get("effective_status") == "ACTIVE"]
                dias_rest = None
                if camp.get("stop_time"):
                    stop = datetime.fromisoformat(camp["stop_time"].replace("Z", "+00:00")).date()
                    dias_rest = (stop - hoje).days
                lifetime = float(camp.get("lifetime_budget", 0)) / 100
                remaining = float(camp.get("budget_remaining", 0)) / 100
                pct_gasto = ((lifetime - remaining) / lifetime * 100) if lifetime > 0 else 0
                camp_info = {"bm": nome_bm, "camp": camp["name"], "gasto": gasto, "pedidos": pedidos, "roas": roas, "dias_rest": dias_rest, "ads_ativos": len(ads_ativos)}

                if status == "ACTIVE":
                    if gasto > 0 and pedidos == 0:
                        camp_info["motivo"] = "Gasto sem retorno"
                        alertas_criticos.append(camp_info)
                    elif gasto > 0 and roas < 1.5:
                        camp_info["motivo"] = f"ROAS critico ({roas:.2f}x)"
                        alertas_criticos.append(camp_info)
                    elif pct_gasto > 90:
                        camp_info["motivo"] = f"Orcamento {pct_gasto:.0f}% esgotado"
                        alertas_criticos.append(camp_info)
                    elif dias_rest is not None and 0 < dias_rest <= 2:
                        camp_info["motivo"] = f"Encerra em {dias_rest} dia(s)"
                        alertas_criticos.append(camp_info)
                    elif gasto > 0 and 1.5 <= roas < 3:
                        camp_info["motivo"] = f"ROAS abaixo do ideal ({roas:.2f}x)"
                        alertas_atencao.append(camp_info)
                    elif pct_gasto > 70:
                        camp_info["motivo"] = f"Orcamento {pct_gasto:.0f}% gasto"
                        alertas_atencao.append(camp_info)
                    elif dias_rest is not None and 2 < dias_rest <= 7:
                        camp_info["motivo"] = f"Encerra em {dias_rest} dias"
                        alertas_atencao.append(camp_info)
        except Exception as e:
            log.error(f"Erro agente [{nome_bm}]: {e}")

    if not alertas_criticos and not alertas_atencao:
        log.info("BOB: nenhum alerta encontrado — tudo saudavel!")
        return

    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [f"🤖 Relatorio do BOB — Agente de Trafego", f"Monaco Agency | {agora_str}", ""]

    if alertas_criticos:
        linhas.append(f"🔴 CRITICO ({len(alertas_criticos)} alerta(s))")
        for a in alertas_criticos:
            linhas.append(f"  {a['bm']}")
            linhas.append(f"  {a['camp']}")
            linhas.append(f"  {a['motivo']}")
            if a['dias_rest'] is not None:
                linhas.append(f"  Encerra em {a['dias_rest']} dia(s)")
            linhas.append("")

    if alertas_atencao:
        linhas.append(f"⚠️ ATENCAO ({len(alertas_atencao)} alerta(s))")
        for a in alertas_atencao:
            linhas.append(f"  {a['bm']}")
            linhas.append(f"  {a['camp']}")
            linhas.append(f"  {a['motivo']}")
            if a['dias_rest'] is not None:
                linhas.append(f"  Encerra em {a['dias_rest']} dia(s)")
            linhas.append("")

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append(f"Total: {len(alertas_criticos)} critico(s) | {len(alertas_atencao)} atencao")

    ok = enviar_whatsapp(cfg_wpp, grupo, "\n".join(linhas))
    if ok:
        log.info(f"BOB: relatorio enviado")
    else:
        log.error("BOB: falha ao enviar relatorio")


def verificar_encerramentos():
    """Detecta campanhas que encerraram ontem ou encerram hoje e avisa no grupo."""
    cfg = carregar_config()
    token = cfg["meta"]["contas"][0]["access_token"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp = cfg["whatsapp"]
    grupo = cfg_wpp["numeros_destino"][0]

    CONTAS_MONITOR = [
        ("Rosa Sul Nova", "act_2523170184768797"),
        ("Dia de Pizza Dourados", "act_723575425785405"),
        ("IH Campo Grande", "act_1131240581799095"),
        ("Mollinari Pizzaria", "act_459274303920372"),
        ("MrGabs", "act_728296823243425"),
        ("IH Dourados", "act_831936562721815"),
        ("Villa Grano Pizzaria", "act_909424425271250"),
        ("Brados Pizzaria", "act_972023765779926"),
        ("Berlim Pizzaria", "act_836447545843342"),
        ("A Favorita", "act_969681458906352"),
        ("Brava Pizza", "act_4279801688941861"),
        ("Pavao Lanchonete", "act_1759603645448352"),
        ("Fornalha Pizzaria", "act_1618084519451450"),
    ]

    hoje = datetime.utcnow().date()
    ontem = hoje - timedelta(days=1)
    encerradas = []
    encerrando_hoje = []

    log.info("Verificando encerramentos de campanhas...")

    for nome_bm, account_id in CONTAS_MONITOR:
        try:
            url = (f"https://graph.facebook.com/{api_version}/{account_id}/campaigns"
                   f"?fields=id,name,status,effective_status,stop_time"
                   f"&limit=50&access_token={token}")
            r = requests.get(url, timeout=20)
            campanhas = r.json().get("data", [])
            for camp in campanhas:
                stop = camp.get("stop_time")
                if not stop:
                    continue
                stop_date = datetime.fromisoformat(stop.replace("Z", "+00:00")).date()
                item = {"bm": nome_bm, "camp": camp["name"], "data": stop_date.strftime("%d/%m/%Y")}
                if stop_date == ontem:
                    encerradas.append(item)
                elif stop_date == hoje:
                    encerrando_hoje.append(item)
        except Exception as e:
            log.error(f"Erro encerramentos [{nome_bm}]: {e}")

    if not encerradas and not encerrando_hoje:
        log.info("Nenhum encerramento detectado hoje.")
        return

    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [f"⏰ Alerta de Encerramentos — BOB", f"Monaco Agency | {agora_str}", ""]

    if encerradas:
        linhas.append(f"🔴 ENCERRADAS ONTEM ({len(encerradas)})")
        for c in encerradas:
            linhas.append(f"  ❌ {c['bm']}")
            linhas.append(f"  📢 {c['camp']}")
            linhas.append(f"  📅 Encerrou em {c['data']}")
            linhas.append(f"  💡 Acao: duplicar ou criar nova campanha")
            linhas.append("")

    if encerrando_hoje:
        linhas.append(f"⚠️ ENCERRAM HOJE ({len(encerrando_hoje)})")
        for c in encerrando_hoje:
            linhas.append(f"  ⚠️ {c['bm']}")
            linhas.append(f"  📢 {c['camp']}")
            linhas.append(f"  📅 Encerra hoje ({c['data']})")
            linhas.append(f"  💡 Acao: renovar ou criar nova campanha")
            linhas.append("")

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append(f"Total: {len(encerradas)} encerrada(s) ontem | {len(encerrando_hoje)} encerrando hoje")

    ok = enviar_whatsapp(cfg_wpp, grupo, "\n".join(linhas))
    if ok:
        log.info("Alerta de encerramentos enviado!")
    else:
        log.error("Falha ao enviar alerta de encerramentos")


def gerar_frase_motivacional() -> str:
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    fallback = "So vive o extraordinario quem arrisca o ordinario. Bora fechar o dia com tudo!"
    if not anthropic_key:
        return fallback
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": "Crie UMA frase motivacional curta (max 2 linhas) sobre empreendedorismo, trafego pago, vendas ou performance, no estilo 'so vive o extraordinario quem arrisca'. Responda APENAS com a frase, sem aspas, sem explicacao."}]
            },
            timeout=20,
        )
        r.raise_for_status()
        frase = r.json()["content"][0]["text"].strip()
        return frase if frase else fallback
    except Exception as e:
        log.error(f"Erro ao gerar frase via IA: {e}")
        return fallback


FRASES_MOTIVACIONAIS = [
   
    "O mercado não espera. Age agora ou fica para trás.",
    "Cada campanha bem otimizada é dinheiro no bolso do cliente.",
    "Resultado não acontece por acaso. Acontece por estratégia.",
    "Quem não mede, não melhora. Quem não melhora, não cresce.",
    "ROAS alto não é sorte. É trabalho inteligente todos os dias.",
    "Empreender é transformar insegurança em ação.",
    "O dinheiro flui para quem resolve problemas reais.",
    "Cada lead é uma oportunidade. Não desperdice nenhuma.",
    "Consistência vence talento quando o talento é inconsistente.",
    "Seu cliente não compra produto. Compra resultado.",
    "Pequenas otimizações diárias constroem grandes resultados mensais.",
    "Quem domina os dados, domina o mercado.",
    "O medo de errar é mais caro que o erro em si.",
    "Invista no que traz retorno. Corte o que drena.",
    "Um bom anúncio não vende — ele conecta pessoas a soluções.",
    "A diferença entre fracasso e sucesso é uma campanha bem ajustada.",
    "Quem acorda cedo para olhar os dados, dorme tranquilo à noite.",
    "Não existe fórmula mágica. Existe teste, análise e escala.",
    "Seu concorrente também está acordado. A diferença é o que você faz com isso.",
    "Foco no processo. Os resultados são consequência.",
    "Tráfego pago é o acelerador. Estratégia é o motor.",
    "Cada real investido precisa trabalhar por você.",
    "Não venda produto. Venda transformação.",
    "O sucesso do cliente é o seu maior ativo.",
    "Dados não mentem. Ouça o que os números estão dizendo.",
    "Campanha parada é dinheiro perdido. Analise e ajuste sempre.",
    "Quem entende o comportamento do consumidor, controla o jogo.",
    "Escalar um negócio é ciência, não aposta.",
    "O melhor momento para otimizar foi ontem. O segundo melhor é agora.",
    "Sem clareza de meta, qualquer resultado parece suficiente.",
    "Audiência certa, mensagem certa, hora certa. Simples assim.",
    "Todo grande negócio começou com alguém que não desistiu no terceiro mês.",
    "Seu próximo cliente está a um anúncio de distância.",
    "Trabalhe nos detalhes. Eles fazem a diferença nos resultados.",
    "Crescimento é desconforto tolerado com propósito.",
    "Não espere condições perfeitas. Crie resultados nas condições que tem.",
    "A meta de hoje é o ponto de partida de amanhã.",
    "Quem testa mais, aprende mais. Quem aprende mais, ganha mais.",
    "Empreender é resolver problemas que outros evitam.",
    "CPR baixo é sinal de mensagem certa para a pessoa certa.",
    "Um bom criativo pode mudar o destino de uma campanha inteira.",
    "O que não é medido não pode ser melhorado.",
    "Cada rejeição no mercado é um redirecionamento para algo melhor.",
    "Resultados extraordinários vêm de hábitos ordinários mantidos.",
    "Quem controla o funil, controla o faturamento.",
    "Não é sobre trabalhar mais. É sobre trabalhar no que importa.",
    "O mercado recompensa quem entrega valor de verdade.",
    "Visão sem execução é ilusão. Execute hoje.",
    "Cada crise é uma oportunidade disfarçada de problema.",
    "Negócio saudável tem meta, processo e execução. Todos os dias.",
    "O cliente que volta é mais valioso que dez novos clientes.",
    "Criatividade com dados é a combinação mais poderosa do marketing.",
    "Não construa campanhas. Construa relacionamentos escaláveis.",
    "Quem domina a atenção do cliente, domina o mercado.",
    "Hoje é o dia de fazer o que amanhã vai parecer fácil.",
    "Ganhar dinheiro é a consequência de gerar valor genuíno.",
    "Cuide dos detalhes e os grandes números cuidarão de si mesmos.",
    "Cada anúncio é uma conversa com um potencial cliente. Fale bem.",
    "O melhor investimento é aquele que traz clientes recorrentes.",
    "Quem analisa o passado, constrói um futuro melhor.",
    "Não existe concorrência quando você domina sua expertise.",
    "Pausa para ajuste não é fraqueza. É inteligência estratégica.",
    "Sua marca é a percepção que o cliente tem. Cuide bem dela.",
    "O primeiro passo é sempre o mais difícil. Mas o mais importante.",
    "Quem sabe escalar sabe quando pausar e quando acelerar.",
    "Resultados são criados antes das campanhas, no planejamento.",
    "Não existe vento favorável para quem não sabe para onde vai.",
    "O mercado pune a inércia e recompensa a ação.",
    "Seja o gestor que os números respeitam.",
    "Toda grande conta começou com uma primeira campanha bem feita.",
    "Disciplina financeira é o alicerce de qualquer escala.",
    "Quem entende de pessoas, entende de vendas.",
    "O segredo do crescimento é reinvestir nos acertos.",
    "Campanha boa não é a que gasta mais. É a que retorna mais.",
    "Trabalhe com dados, pense com estratégia, aja com coragem.",
    "O sucesso é uma série de decisões certas tomadas sob pressão.",
    "Cada BM bem gerenciada é uma máquina de resultados.",
    "Não tenha medo do erro. Tenha medo de não aprender com ele.",
    "Quem domina o pixel, domina a conversão.",
    "Crescimento sustentável vem de processos bem executados.",
    "O cliente certo para a oferta certa muda o jogo.",
    "Análise semanal evita surpresa mensal.",
    "Quem não inova, estagna. Quem estagna, perde mercado.",
    "O faturamento é o resultado de muitas pequenas decisões certas.",
    "Cada teste A/B é uma conversa com o mercado. Ouça.",
    "Empreender é ter a coragem de apostar no próprio potencial.",
    "Quando os dados falam, a opinião cala.",
    "O melhor anúncio é aquele que parece uma conversa natural.",
    "Quem gerencia bem uma conta, pode gerenciar qualquer negócio.",
    "Faturamento alto com margem baixa não é sucesso. Revise o modelo.",
    "Cada real economizado na campanha é lucro na operação.",
    "A escalada começa quando o processo vira rotina.",
    "Não espere inspiração. Crie sistemas que gerem resultados.",
    "Quem conhece o cliente melhor que o próprio cliente, vende mais.",
    "A persistência transforma campanhas medianas em casos de sucesso.",
    "Otimize o que funciona. Elimine o que drena.",
    "O mercado recompensa quem age antes de estar pronto.",
    "Cada objeção do cliente é uma oportunidade de conexão.",
    "Não existe campanha perfeita. Existe campanha em constante melhoria.",
    "Quem pensa longo prazo constrói negócios. Quem pensa curto, corre atrás.",
    "Um criativo que converte vale mais que mil seguidores.",
    "Seu posicionamento determina seu preço. Posicione-se bem.",
    "Dados diários constroem decisões mensais acertadas.",
    "O diferencial não é o produto. É a experiência que ele proporciona.",
    "Quem tem clareza de público, tem clareza de resultado.",
    "Cada cliente satisfeito é um vendedor gratuito do seu negócio.",
    "O mercado não paga pelo esforço. Paga pelo resultado entregue.",
    "Automatize o repetitivo. Humanize o estratégico.",
    "Crescimento sem controle vira caos. Cresça com estrutura.",
    "Quem investe em aprendizado colhe resultados exponenciais.",
    "A consistência de 90 dias supera qualquer talento de 30.",
    "Não venda para todo mundo. Venda para quem precisa de verdade.",
    "Cada euro investido precisa justificar sua presença no orçamento.",
    "Estratégia sem execução é poesia. Execute hoje.",
    "O maior erro é parar quando os resultados começam a aparecer.",
    "Quem sabe ler relatório, sabe onde está o dinheiro escondido.",
    "Foco é a habilidade mais valiosa no mundo das distrações.",
    "Campanha ativa sem monitoramento é dinheiro jogado fora.",
    "A virada acontece quando você para de reagir e começa a planejar.",
    "Cada ponto percentual de ROAS a mais representa lucro real.",
    "Quem cuida da retenção, não precisa correr tanto pela aquisição.",
    "O mercado muda. Quem se adapta primeiro, leva vantagem.",
    "Resultados extraordinários são consequência de dias ordinários bem vividos.",
    "Não construa apenas campanhas. Construa funis completos.",
    "O sucesso não é um destino. É um hábito cultivado todo dia.",
    "Quem testa hipóteses com rapidez aprende mais rápido que os concorrentes.",
    "Cada segmentação errada é dinheiro sendo dado à concorrência.",
    "A melhor estratégia é a que você consegue executar todos os dias.",
    "Negócio bom é aquele que funciona mesmo quando o dono não está.",
    "Não meça apenas o que é fácil medir. Meça o que importa.",
    "O cliente compra quando a dor supera o custo da solução.",
    "Quem cria valor genuíno não precisa vender com desconto.",
    "Cada crise de campanha resolvida é expertise acumulada.",
    "A diferença entre bom e excelente está nos detalhes ignorados.",
    "Quem domina o remarketing, recupera dinheiro que já foi investido.",
    "Planejamento sem execução é só papel. Execute.",
    "O mercado digital não dorme. Mas quem se prepara dorme tranquilo.",
    "Cada campanha pausada por estratégia difere de pausada por medo.",
    "Resultado consistente vem de processo consistente.",
    "Quem aprende com os dados de outros economiza meses de teste.",
    "A qualidade do seu serviço determina a qualidade dos seus clientes.",
    "Não espere o momento perfeito. Faça o momento ser perfeito.",
    "Cada insight de analytics vale mais que uma hora de suposições.",
    "Quem sabe gerenciar expectativas, sabe fidelizar clientes.",
    "O crescimento não é linear. Mas a disciplina precisa ser.",
    "Invista no que você pode medir. Corte o que não tem retorno.",
    "Cada cliente novo custa mais que manter um antigo. Pense nisso.",
    "Não existe atalho para o resultado consistente. Existe processo.",
    "Quem entende de funil não desperdiça verba em topo sem fundo.",
    "A campanha que converte é a que fala a língua do cliente.",
    "Crescimento real começa quando você para de terceirizar a responsabilidade.",
    "Cada métrica tem uma história. Aprenda a ouvi-las.",
    "O empresário que aprende nunca fica obsoleto.",
    "Quem sabe precificar, sabe crescer com saúde financeira.",
    "Cada campanha bem estruturada é um ativo que trabalha por você.",
    "Não construa para o curto prazo. Construa para durar.",
    "O maior diferencial competitivo é a velocidade de aprendizado.",
    "Quem cuida do fluxo de caixa cuida do futuro do negócio.",
    "Resultados aparecem para quem não desiste na terceira semana.",
    "O mercado recompensa a clareza de posicionamento.",
    "Cada decisão de hoje é o resultado de amanhã.",
    "Quem age com dados tem confiança. Quem age com achismo, tem sorte.",
    "A excelência não é um evento. É uma escolha feita todos os dias.",
    "Não espere o mercado mudar. Seja a mudança que o mercado precisa.",
    "Cada meta batida é o combustível para a próxima meta maior.",
    "Quem domina a atenção do público, domina o mercado.",
    "O caminho para o extraordinário passa pelo ordinário bem feito.",
    "Quem investe em criativo investe em conversão.",
    "Dinheiro parado é oportunidade perdida. Faça ele trabalhar.",
    "O lucro real começa quando o processo é replicável.",
    "Cada cliente bem atendido é um contrato renovado.",
    "Não espere chegar ao topo para acreditar no caminho.",
    "Quem domina sua niche domina seus resultados.",
    "A mentalidade certa abre portas que o mercado fecha.",
]


def gerar_frase_motivacional() -> str:
    """Rotaciona frases por dia do ano — sem repetir por 180 dias."""
    dia_do_ano = datetime.now().timetuple().tm_yday
    indice = dia_do_ano % len(FRASES_MOTIVACIONAIS)
    return FRASES_MOTIVACIONAIS[indice]


def rodar_loop():
    cfg = carregar_config()
    horario_alvo = cfg["alertas"].get("horario_verificacao", "15:00")

    # Horarios em UTC (Railway usa UTC — BRT = UTC-3)
    # 07:00 BRT = 10:00 UTC — motivacional
    # 08:00 BRT = 11:00 UTC — encerramentos
    # 12:00 BRT = 15:00 UTC — saldo (horario_alvo)
    horario_motivacional  = "10:00"
    horario_encerramentos = "11:00"

    log.info("Monito de BMs iniciado")
    log.info(f"  Motivacional:   {horario_motivacional} UTC (07:00 BRT)")
    log.info(f"  Encerramentos:  {horario_encerramentos} UTC (08:00 BRT)")
    log.info(f"  Saldo:          {horario_alvo} UTC (12:00 BRT)")
    log.info(f"  Contas:         {len(cfg['meta']['contas'])}")
    log.info(f"  Limite critico: {fmt_brl(cfg['alertas']['limite_critico'])}")
    log.info(f"  Limite baixo:   {fmt_brl(cfg['alertas']['limite_baixo'])}")
    log.info("")

    ultimo_dia_motivacional  = None
    ultimo_dia_encerramentos = None
    ultimo_dia_saldo         = None

    while True:
        agora = datetime.utcnow()
        hora_atual = agora.strftime("%H:%M")
        hoje = agora.date()

        if hora_atual == horario_motivacional and ultimo_dia_motivacional != hoje:
            ultimo_dia_motivacional = hoje
            try:
                enviar_motivacional()
            except Exception as e:
                log.exception(f"Erro motivacional: {e}")

        if hora_atual == horario_encerramentos and ultimo_dia_encerramentos != hoje:
            ultimo_dia_encerramentos = hoje
            try:
                verificar_encerramentos()
            except Exception as e:
                log.exception(f"Erro encerramentos: {e}")

        if hora_atual == horario_alvo and ultimo_dia_saldo != hoje:
            ultimo_dia_saldo = hoje
            try:
                verificar_e_alertar()
            except Exception as e:
                log.exception(f"Erro saldo: {e}")

        if hora_atual not in (horario_motivacional, horario_encerramentos, horario_alvo):
            h, m = map(int, horario_alvo.split(":"))
            proximo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
            if proximo <= agora:
                proximo += timedelta(days=1)
            falta = proximo - agora
            horas = int(falta.total_seconds() // 3600)
            minutos = int((falta.total_seconds() % 3600) // 60)
            log.info(f"Proxima verificacao de saldo em {horas}h {minutos}min")

        time.sleep(60)


if __name__ == "__main__":
    rodar_loop()
