"""
Monitor de Saldo de BMs do Meta
Consulta saldo via API do Meta e dispara alertas via WhatsApp (Evolution API)
"""

import json
import os
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

CONFIG_PATH  = Path(__file__).parent / "config.json"
ALERTAS_LOG  = Path(__file__).parent / "alertas_enviados.json"

# Lista padrao de contas (nome + account_id apenas — sem segredos).
# Pode ser sobrescrita/expandida pelo cadastro de clientes (config.json),
# que so guarda dados nao sensiveis: o token do Meta sempre vem do
# ambiente (META_TOKEN), nunca de arquivo versionado no repositorio publico.
DEFAULT_CONTAS = [
    {"nome": "Rosa Sul Nova",           "account_id": "act_2523170184768797"},
    {"nome": "Dia de Pizza Dourados",   "account_id": "act_723575425785405"},
    {"nome": "IH Campo Grande",         "account_id": "act_1131240581799095"},
    {"nome": "Mollinari",               "account_id": "act_459274303920372"},
    {"nome": "MrGabs",                  "account_id": "act_728296823243425"},
    {"nome": "IH Dourados",             "account_id": "act_831936562721815"},
    {"nome": "Villa Grano",             "account_id": "act_909424425271250"},
    {"nome": "Brados",                  "account_id": "act_972023765779926"},
    {"nome": "Berlim",                  "account_id": "act_836447545843342"},
    {"nome": "A Favorita",              "account_id": "act_969681458906352"},
    {"nome": "Brava Pizza",             "account_id": "act_4279801688941861"},
    {"nome": "Pavao",                   "account_id": "act_1759603645448352"},
    {"nome": "Fornalha",                "account_id": "act_1618084519451450"},
    {"nome": "CA- Leni ADS 02",         "account_id": "act_1569287454130140"},
    {"nome": "CA RJK SHOP",             "account_id": "act_297417165372711"},
    {"nome": "CA - Miotto Construtora", "account_id": "act_213109970735074"},
    {"nome": "CA - ICGP",               "account_id": "act_360815898753195"},
    {"nome": "CA - Miotto Backup",      "account_id": "act_533683308259417"},
    {"nome": "CA - Monaco Agency",      "account_id": "act_732966175219099"},
    {"nome": "BRUNA MACHADO - DOTCON",  "account_id": "act_1102427261426373"},
    {"nome": "CA - AMK Estetica",       "account_id": "act_590117117342811"},
    {"nome": "JS - UNIFORME",           "account_id": "act_1452225369942067"},
    {"nome": "SH Tijolos",              "account_id": "act_3858259327816511"},
]


# ── Config ────────────────────────────────────────────────────────

def carregar_config() -> dict:
    """Monta a configuracao em runtime. A lista de clientes (contas) pode vir
    do config.json versionado (cadastrado via clientes.html), mas token do
    Meta e credenciais do WhatsApp SEMPRE vem de variavel de ambiente —
    nunca de arquivo, porque o repositorio e publico."""
    contas = [dict(c) for c in DEFAULT_CONTAS]

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("contas"):
                contas = data["contas"]
        except Exception as e:
            log.error(f"Erro ao ler config.json, usando contas padrao: {e}")

    token = os.getenv("META_TOKEN", "")
    for c in contas:
        c.setdefault("ativo", True)
        c.setdefault("metricas", ["saldo"])
        c.setdefault("whatsapp_numero", "")
        c.setdefault("limite_critico", None)
        c.setdefault("limite_baixo", None)
        c["access_token"] = token  # sempre via env var

    return {
        "meta": {
            "api_version": "v19.0",
            "contas": contas,
        },
        "alertas": {
            "limite_critico": 50,
            "limite_baixo": 100,
            "horario_verificacao": "15:00",
            "alertar_uma_vez_por_dia": True,
        },
        "whatsapp": {
            "api_url":          os.getenv("WPP_API_URL",     "http://localhost:8080"),
            "api_key":          os.getenv("WPP_API_KEY",     "minhaChave123"),
            "instancia":        os.getenv("WPP_INSTANCIA",   "meu-whatsapp"),
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


# ── WhatsApp ──────────────────────────────────────────────────────

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


def destino_cliente(conta_cfg: dict, cfg_wpp: dict) -> list:
    """Retorna o(s) numero(s)/grupo de WhatsApp de destino para um cliente.
    Se o cliente tiver um WhatsApp proprio cadastrado, envia so pra ele.
    Caso contrario, cai no grupo interno de operacoes (comportamento antigo)."""
    numero = (conta_cfg.get("whatsapp_numero") or "").strip()
    if numero:
        return [numero]
    return cfg_wpp["numeros_destino"]


# ── Saldo ─────────────────────────────────────────────────────────

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
        raw_balance      = int(data.get("balance", 0))
        raw_spend_cap    = int(data.get("spend_cap", 0))
        raw_amount_spent = int(data.get("amount_spent", 0))
        spend_cap    = raw_spend_cap / 100
        amount_spent = raw_amount_spent / 100
        balance = (spend_cap - amount_spent) if spend_cap > 0 else raw_balance / 100
        return {
            "account_id": account_id,
            "nome":       data.get("name", account_id),
            "balance":    balance,
            "spend_cap":  spend_cap,
            "currency":   data.get("currency", "BRL"),
            "status":     data.get("account_status", 1),
        }
    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao consultar [{account_id}]: {e}")
        return None


def montar_mensagem_saldo(conta: dict, nivel: str, limite: float) -> str:
    label = "CRITICO" if nivel == "critico" else "BAIXO"
    linhas = [
        f"Alerta de Saldo — {label}", "",
        f"BM: {conta['nome']}",
        f"Saldo atual: {fmt_brl(conta['balance'])}",
        f"Limite de alerta: {fmt_brl(limite)}",
    ]
    if conta["spend_cap"] > 0:
        linhas.append(f"Limite de gasto: {fmt_brl(conta['spend_cap'])}")
    linhas += ["", "Recarregue o saldo para evitar interrupcoes nas campanhas.",
               f"Horario: {datetime.now().strftime('%d/%m/%Y %H:%M')}"]
    return "\n".join(linhas)


def verificar_e_alertar():
    cfg             = carregar_config()
    alertas_enviados = carregar_alertas_enviados()
    hoje            = str(date.today())
    limite_critico_padrao = cfg["alertas"]["limite_critico"]
    limite_baixo_padrao   = cfg["alertas"]["limite_baixo"]
    uma_vez_por_dia = cfg["alertas"]["alertar_uma_vez_por_dia"]
    api_version     = cfg["meta"]["api_version"]
    cfg_wpp         = cfg["whatsapp"]

    log.info(f"=== Verificacao de saldo — {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")

    for conta_cfg in cfg["meta"]["contas"]:
        if not conta_cfg.get("ativo", True):
            continue
        if "saldo" not in conta_cfg.get("metricas", ["saldo"]):
            continue

        account_id = conta_cfg["account_id"]
        token      = conta_cfg["access_token"]
        nome       = conta_cfg["nome"]
        limite_critico = conta_cfg.get("limite_critico") or limite_critico_padrao
        limite_baixo   = conta_cfg.get("limite_baixo") or limite_baixo_padrao

        log.info(f"Consultando: {nome} ({account_id})")
        conta = consultar_saldo(account_id, token, api_version)
        if conta is None:
            log.warning(f"Pulando {nome} — erro na consulta")
            continue
        balance = conta["balance"]
        log.info(f"  Saldo: {fmt_brl(balance)}")
        if balance <= limite_critico:
            nivel = "critico"; limite_ref = limite_critico
        elif balance <= limite_baixo:
            nivel = "baixo"; limite_ref = limite_baixo
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
        for numero in destino_cliente(conta_cfg, cfg_wpp):
            if enviar_whatsapp(cfg_wpp, numero, mensagem):
                enviou = True
        if enviou:
            alertas_enviados[account_id] = {
                "data": hoje, "nivel": nivel, "balance": balance,
                "hora": datetime.now().strftime("%H:%M"), "nome": nome,
            }
            salvar_alertas_enviados(alertas_enviados)

    log.info("=== Verificacao de saldo concluida ===\n")


# ── Relatorio de performance por cliente ─────────────────────────
# Equivalente ao relatorio automatico da Metrifiquei: cada cliente recebe,
# no proprio WhatsApp, so as metricas que ele escolheu no cadastro.

def buscar_insights_periodo(account_id: str, token: str, api_version: str, date_preset: str = "last_7d") -> dict:
    url = (f"https://graph.facebook.com/{api_version}/{account_id}/insights"
           f"?fields=spend,actions,action_values,impressions,clicks"
           f"&date_preset={date_preset}&access_token={token}")
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        if not data.get("data"):
            return {"gasto": 0, "pedidos": 0, "fat": 0, "leads": 0, "clicks": 0, "impr": 0}
        ins     = data["data"][0]
        gasto   = float(ins.get("spend", 0))
        actions = ins.get("actions", [])
        av      = ins.get("action_values", [])
        pedidos = int(next((a["value"] for a in actions if a["action_type"] == "purchase"), 0))
        fat     = float(next((a["value"] for a in av if a["action_type"] == "purchase"), 0))
        leads   = int(next((a["value"] for a in actions if a["action_type"] == "lead"), 0))
        clicks  = int(ins.get("clicks", 0))
        impr    = int(ins.get("impressions", 0))
        return {"gasto": gasto, "pedidos": pedidos, "fat": fat, "leads": leads, "clicks": clicks, "impr": impr}
    except Exception as e:
        log.error(f"Erro insights performance [{account_id}]: {e}")
        return {"gasto": 0, "pedidos": 0, "fat": 0, "leads": 0, "clicks": 0, "impr": 0}


def montar_mensagem_performance(nome: str, ins: dict) -> str:
    gasto, pedidos, fat, leads, clicks = ins["gasto"], ins["pedidos"], ins["fat"], ins["leads"], ins["clicks"]
    linhas = ["Relatorio de Performance — BOB", nome, "Periodo: ultimos 7 dias", ""]
    if pedidos > 0 or fat > 0:
        cpr  = gasto / pedidos if pedidos > 0 else 0
        roas = fat / gasto if gasto > 0 and fat > 0 else 0
        linhas += [
            f"Investido: {fmt_brl(gasto)}",
            f"Pedidos: {pedidos}",
            f"Faturamento: {fmt_brl(fat)}",
            f"CPR: {fmt_brl(cpr) if cpr else '-'}",
            f"ROAS: {roas:.2f}x" if roas else "ROAS: -",
        ]
    elif leads > 0:
        cpl = gasto / leads if leads > 0 else 0
        linhas += [
            f"Investido: {fmt_brl(gasto)}",
            f"Leads: {leads}",
            f"Custo por lead: {fmt_brl(cpl) if cpl else '-'}",
        ]
    else:
        linhas += [
            f"Investido: {fmt_brl(gasto)}",
            f"Cliques: {clicks}",
            f"Impressoes: {ins['impr']}",
        ]
    linhas += ["", f"Horario: {datetime.now().strftime('%d/%m/%Y %H:%M')}"]
    return "\n".join(linhas)


def enviar_relatorios_performance():
    cfg         = carregar_config()
    api_version = cfg["meta"]["api_version"]
    cfg_wpp     = cfg["whatsapp"]

    log.info("Enviando relatorios de performance por cliente...")
    for conta_cfg in cfg["meta"]["contas"]:
        if not conta_cfg.get("ativo", True):
            continue
        if "performance" not in conta_cfg.get("metricas", []):
            continue
        account_id = conta_cfg["account_id"]
        token      = conta_cfg["access_token"]
        nome       = conta_cfg["nome"]
        ins = buscar_insights_periodo(account_id, token, api_version)
        if ins["gasto"] == 0:
            log.info(f"  {nome}: sem gasto no periodo, pulando relatorio")
            continue
        mensagem = montar_mensagem_performance(nome, ins)
        for numero in destino_cliente(conta_cfg, cfg_wpp):
            enviar_whatsapp(cfg_wpp, numero, mensagem)
    log.info("Relatorios de performance concluidos.")


# ── Comparativo semanal individual por cliente ───────────────────

def buscar_insights_range(account_id: str, token: str, api_version: str, since: str, until: str) -> dict:
    time_range = '{' + f'"since":"{since}","until":"{until}"' + '}'
    url = (f"https://graph.facebook.com/{api_version}/{account_id}/insights"
           f"?fields=spend,actions,action_values,impressions,clicks"
           f"&time_range={time_range}&access_token={token}")
    try:
        r = requests.get(url, timeout=20)
        data = r.json()
        if not data.get("data"):
            return {"gasto": 0, "pedidos": 0, "fat": 0, "leads": 0, "clicks": 0}
        ins     = data["data"][0]
        gasto   = float(ins.get("spend", 0))
        actions = ins.get("actions", [])
        av      = ins.get("action_values", [])
        pedidos = int(next((a["value"] for a in actions if a["action_type"] == "purchase"), 0))
        fat     = float(next((a["value"] for a in av if a["action_type"] == "purchase"), 0))
        leads   = int(next((a["value"] for a in actions if a["action_type"] == "lead"), 0))
        clicks  = int(ins.get("clicks", 0))
        return {"gasto": gasto, "pedidos": pedidos, "fat": fat, "leads": leads, "clicks": clicks}
    except Exception as e:
        log.error(f"Erro insights range [{account_id}]: {e}")
        return {"gasto": 0, "pedidos": 0, "fat": 0, "leads": 0, "clicks": 0}


def enviar_comparativo_individual():
    """Comparativo semanal individual (seg/qua/sex) so para clientes que
    marcaram 'comparativo' no cadastro. Independente do relatorio interno
    da equipe (analisar_comparativo), que continua igual."""
    hoje = date.today()
    if hoje.weekday() not in (0, 2, 4):
        return

    cfg         = carregar_config()
    api_version = cfg["meta"]["api_version"]
    cfg_wpp     = cfg["whatsapp"]

    fim_atual    = hoje - timedelta(days=1)
    ini_atual    = fim_atual - timedelta(days=6)
    fim_anterior = ini_atual - timedelta(days=1)
    ini_anterior = fim_anterior - timedelta(days=6)
    fmt_date = lambda d: d.strftime("%Y-%m-%d")
    fmt_br   = lambda d: d.strftime("%d/%m")

    log.info("Enviando comparativos individuais por cliente...")
    for conta_cfg in cfg["meta"]["contas"]:
        if not conta_cfg.get("ativo", True):
            continue
        if "comparativo" not in conta_cfg.get("metricas", []):
            continue
        account_id = conta_cfg["account_id"]
        token      = conta_cfg["access_token"]
        nome       = conta_cfg["nome"]

        atual    = buscar_insights_range(account_id, token, api_version, fmt_date(ini_atual), fmt_date(fim_atual))
        anterior = buscar_insights_range(account_id, token, api_version, fmt_date(ini_anterior), fmt_date(fim_anterior))
        if atual["gasto"] == 0 and anterior["gasto"] == 0:
            continue

        linhas = [
            "Comparativo Semanal — BOB", nome, "",
            f"Periodo atual: {fmt_br(ini_atual)} - {fmt_br(fim_atual)}",
            f"Periodo anterior: {fmt_br(ini_anterior)} - {fmt_br(fim_anterior)}", "",
        ]
        if anterior["pedidos"] > 0 or atual["pedidos"] > 0:
            var_ped = ((atual["pedidos"] - anterior["pedidos"]) / anterior["pedidos"] * 100) if anterior["pedidos"] > 0 else 0
            linhas.append(f"Pedidos: {anterior['pedidos']} -> {atual['pedidos']} ({var_ped:+.1f}%)")
            linhas.append(f"Faturamento: {fmt_brl(anterior['fat'])} -> {fmt_brl(atual['fat'])}")
        elif anterior["leads"] > 0 or atual["leads"] > 0:
            var_leads = ((atual["leads"] - anterior["leads"]) / anterior["leads"] * 100) if anterior["leads"] > 0 else 0
            linhas.append(f"Leads: {anterior['leads']} -> {atual['leads']} ({var_leads:+.1f}%)")
        linhas.append(f"Investido: {fmt_brl(anterior['gasto'])} -> {fmt_brl(atual['gasto'])}")
        linhas += ["", f"Horario: {datetime.now().strftime('%d/%m/%Y %H:%M')}"]

        mensagem = "\n".join(linhas)
        for numero in destino_cliente(conta_cfg, cfg_wpp):
            enviar_whatsapp(cfg_wpp, numero, mensagem)
    log.info("Comparativos individuais concluidos.")


# ── Encerramentos ─────────────────────────────────────────────────

def verificar_encerramentos():
    cfg         = carregar_config()
    token       = cfg["meta"]["contas"][0]["access_token"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp     = cfg["whatsapp"]
    grupo       = cfg_wpp["numeros_destino"][0]

    CONTAS_MONITOR = [
        ("Rosa Sul Nova",          "act_2523170184768797"),
        ("Dia de Pizza Dourados",  "act_723575425785405"),
        ("IH Campo Grande",        "act_1131240581799095"),
        ("Mollinari Pizzaria",     "act_459274303920372"),
        ("MrGabs",                 "act_728296823243425"),
        ("IH Dourados",            "act_831936562721815"),
        ("Villa Grano Pizzaria",   "act_909424425271250"),
        ("Brados Pizzaria",        "act_972023765779926"),
        ("Berlim Pizzaria",        "act_836447545843342"),
        ("A Favorita",             "act_969681458906352"),
        ("Brava Pizza",            "act_4279801688941861"),
        ("Pavao Lanchonete",       "act_1759603645448352"),
        ("Fornalha Pizzaria",      "act_1618084519451450"),
        ("CA- Leni ADS 02",        "act_1569287454130140"),
        ("CA RJK SHOP",            "act_297417165372711"),
        ("CA - Miotto Construtora","act_213109970735074"),
        ("CA - ICGP",              "act_360815898753195"),
        ("CA - Miotto Backup",     "act_533683308259417"),
        ("CA - Monaco Agency",     "act_732966175219099"),
        ("BRUNA MACHADO",          "act_1102427261426373"),
        ("CA - AMK Estetica",      "act_590117117342811"),
        ("JS - UNIFORME",          "act_1452225369942067"),
        ("SH Tijolos",             "act_3858259327816511"),
    ]

    hoje  = datetime.now(datetime.UTC).date() if hasattr(datetime, 'UTC') else datetime.utcnow().date()
    ontem = hoje - timedelta(days=1)
    encerradas      = []
    encerrando_hoje = []

    log.info("Verificando encerramentos de campanhas...")

    for nome_bm, account_id in CONTAS_MONITOR:
        try:
            campanhas = []
            url = (f"https://graph.facebook.com/{api_version}/{account_id}/campaigns"
                   f"?fields=id,name,status,effective_status,stop_time"
                   f"&limit=100&access_token={token}")
            while url:
                r = requests.get(url, timeout=20).json()
                campanhas.extend(r.get("data", []))
                url = r.get("paging", {}).get("next")

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
    linhas = [f"Alerta de Encerramentos — BOB", f"Monaco Agency | {agora_str}", ""]

    if encerradas:
        linhas.append(f"ENCERRADAS ONTEM ({len(encerradas)})")
        for c in encerradas:
            linhas.append(f"  BM: {c['bm']}")
            linhas.append(f"  Campanha: {c['camp']}")
            linhas.append(f"  Encerrou em: {c['data']}")
            linhas.append(f"  Acao: duplicar ou criar nova campanha")
            linhas.append("")

    if encerrando_hoje:
        linhas.append(f"ENCERRAM HOJE ({len(encerrando_hoje)})")
        for c in encerrando_hoje:
            linhas.append(f"  BM: {c['bm']}")
            linhas.append(f"  Campanha: {c['camp']}")
            linhas.append(f"  Encerra hoje ({c['data']})")
            linhas.append(f"  Acao: renovar ou criar nova campanha")
            linhas.append("")

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append(f"Total: {len(encerradas)} encerrada(s) ontem | {len(encerrando_hoje)} encerrando hoje")

    ok = enviar_whatsapp(cfg_wpp, grupo, "\n".join(linhas))
    if ok:
        log.info("Alerta de encerramentos enviado!")
    else:
        log.error("Falha ao enviar alerta de encerramentos")


# ── Motivacional ──────────────────────────────────────────────────

FRASES_MOTIVACIONAIS = [
    "So vive o extraordinario quem arrisca o ordinario.",
    "O mercado nao espera. Age agora ou fica para tras.",
    "Cada campanha bem otimizada e dinheiro no bolso do cliente.",
    "Resultado nao acontece por acaso. Acontece por estrategia.",
    "Quem nao mede, nao melhora. Quem nao melhora, nao cresce.",
    "ROAS alto nao e sorte. E trabalho inteligente todos os dias.",
    "Empreender e transformar inseguranca em acao.",
    "O dinheiro flui para quem resolve problemas reais.",
    "Cada lead e uma oportunidade. Nao desperdice nenhuma.",
    "Consistencia vence talento quando o talento e inconsistente.",
    "Seu cliente nao compra produto. Compra resultado.",
    "Pequenas otimizacoes diarias constroem grandes resultados mensais.",
    "Quem domina os dados, domina o mercado.",
    "O medo de errar e mais caro que o erro em si.",
    "Invista no que traz retorno. Corte o que drena.",
    "Um bom anuncio nao vende — ele conecta pessoas a solucoes.",
    "A diferenca entre fracasso e sucesso e uma campanha bem ajustada.",
    "Quem acorda cedo para olhar os dados, dorme tranquilo a noite.",
    "Nao existe formula magica. Existe teste, analise e escala.",
    "Seu concorrente tambem esta acordado. A diferenca e o que voce faz com isso.",
    "Foco no processo. Os resultados sao consequencia.",
    "Trafego pago e o acelerador. Estrategia e o motor.",
    "Cada real investido precisa trabalhar por voce.",
    "Nao venda produto. Venda transformacao.",
    "O sucesso do cliente e o seu maior ativo.",
    "Dados nao mentem. Ouca o que os numeros estao dizendo.",
    "Campanha parada e dinheiro perdido. Analise e ajuste sempre.",
    "Quem entende o comportamento do consumidor, controla o jogo.",
    "Escalar um negocio e ciencia, nao aposta.",
    "O melhor momento para otimizar foi ontem. O segundo melhor e agora.",
    "Sem clareza de meta, qualquer resultado parece suficiente.",
    "Audiencia certa, mensagem certa, hora certa. Simples assim.",
    "Todo grande negocio comecou com alguem que nao desistiu no terceiro mes.",
    "Seu proximo cliente esta a um anuncio de distancia.",
    "Trabalhe nos detalhes. Eles fazem a diferenca nos resultados.",
    "Crescimento e desconforto tolerado com proposito.",
    "Nao espere condicoes perfeitas. Crie resultados nas condicoes que tem.",
    "A meta de hoje e o ponto de partida de amanha.",
    "Quem testa mais, aprende mais. Quem aprende mais, ganha mais.",
    "Empreender e resolver problemas que outros evitam.",
    "CPR baixo e sinal de mensagem certa para a pessoa certa.",
    "Um bom criativo pode mudar o destino de uma campanha inteira.",
    "O que nao e medido nao pode ser melhorado.",
    "Cada rejeicao no mercado e um redirecionamento para algo melhor.",
    "Resultados extraordinarios vem de habitos ordinarios mantidos.",
    "Quem controla o funil, controla o faturamento.",
    "Nao e sobre trabalhar mais. E sobre trabalhar no que importa.",
    "O mercado recompensa quem entrega valor de verdade.",
    "Visao sem execucao e ilusao. Execute hoje.",
    "Cada crise e uma oportunidade disfarcada de problema.",
    "Negocio saudavel tem meta, processo e execucao. Todos os dias.",
    "O cliente que volta e mais valioso que dez novos clientes.",
    "Criatividade com dados e a combinacao mais poderosa do marketing.",
    "Nao construa campanhas. Construa relacionamentos escalaveis.",
    "Quem domina a atencao do cliente, domina o mercado.",
    "Hoje e o dia de fazer o que amanha vai parecer facil.",
    "Ganhar dinheiro e a consequencia de gerar valor genuino.",
    "Cuide dos detalhes e os grandes numeros cuidarao de si mesmos.",
    "Cada anuncio e uma conversa com um potencial cliente. Fale bem.",
    "O melhor investimento e aquele que traz clientes recorrentes.",
    "Quem analisa o passado, constroi um futuro melhor.",
    "Nao existe concorrencia quando voce domina sua expertise.",
    "Pausa para ajuste nao e fraqueza. E inteligencia estrategica.",
    "Sua marca e a percepcao que o cliente tem. Cuide bem dela.",
    "O primeiro passo e sempre o mais dificil. Mas o mais importante.",
    "Quem sabe escalar sabe quando pausar e quando acelerar.",
    "Resultados sao criados antes das campanhas, no planejamento.",
    "Nao existe vento favoravel para quem nao sabe para onde vai.",
    "O mercado pune a inercia e recompensa a acao.",
    "Seja o gestor que os numeros respeitam.",
    "Toda grande conta comecou com uma primeira campanha bem feita.",
    "Disciplina financeira e o alicerce de qualquer escala.",
    "Quem entende de pessoas, entende de vendas.",
    "O segredo do crescimento e reinvestir nos acertos.",
    "Campanha boa nao e a que gasta mais. E a que retorna mais.",
    "Trabalhe com dados, pense com estrategia, aja com coragem.",
    "O sucesso e uma serie de decisoes certas tomadas sob pressao.",
    "Cada BM bem gerenciada e uma maquina de resultados.",
    "Nao tenha medo do erro. Tenha medo de nao aprender com ele.",
    "Quem domina o pixel, domina a conversao.",
    "Crescimento sustentavel vem de processos bem executados.",
    "O cliente certo para a oferta certa muda o jogo.",
    "Analise semanal evita surpresa mensal.",
    "Quem nao inova, estagna. Quem estagna, perde mercado.",
    "O faturamento e o resultado de muitas pequenas decisoes certas.",
    "Cada teste A/B e uma conversa com o mercado. Ouca.",
    "Empreender e ter a coragem de apostar no proprio potencial.",
    "Quando os dados falam, a opiniao cala.",
    "O melhor anuncio e aquele que parece uma conversa natural.",
    "Quem gerencia bem uma conta, pode gerenciar qualquer negocio.",
    "Faturamento alto com margem baixa nao e sucesso. Revise o modelo.",
    "Cada real economizado na campanha e lucro na operacao.",
    "A escalada comeca quando o processo vira rotina.",
    "Nao espere inspiracao. Crie sistemas que gerem resultados.",
    "Quem conhece o cliente melhor que o proprio cliente, vende mais.",
    "A persistencia transforma campanhas medianas em casos de sucesso.",
    "Otimize o que funciona. Elimine o que drena.",
    "O mercado recompensa quem age antes de estar pronto.",
    "Cada objeccao do cliente e uma oportunidade de conexao.",
    "Nao existe campanha perfeita. Existe campanha em constante melhoria.",
    "Quem pensa longo prazo constroi negocios. Quem pensa curto, corre atras.",
    "Um criativo que converte vale mais que mil seguidores.",
    "Seu posicionamento determina seu preco. Posicione-se bem.",
    "Dados diarios constroem decisoes mensais acertadas.",
    "O diferencial nao e o produto. E a experiencia que ele proporciona.",
    "Quem tem clareza de publico, tem clareza de resultado.",
    "Cada cliente satisfeito e um vendedor gratuito do seu negocio.",
    "O mercado nao paga pelo esforco. Paga pelo resultado entregue.",
    "Automatize o repetitivo. Humanize o estrategico.",
    "Crescimento sem controle vira caos. Cresca com estrutura.",
    "Quem investe em aprendizado colhe resultados exponenciais.",
    "A consistencia de 90 dias supera qualquer talento de 30.",
    "Nao venda para todo mundo. Venda para quem precisa de verdade.",
    "Estrategia sem execucao e poesia. Execute hoje.",
    "O maior erro e parar quando os resultados comecam a aparecer.",
    "Quem sabe ler relatorio, sabe onde esta o dinheiro escondido.",
    "Foco e a habilidade mais valiosa no mundo das distracoes.",
    "Campanha ativa sem monitoramento e dinheiro jogado fora.",
    "A virada acontece quando voce para de reagir e comeca a planejar.",
    "Cada ponto percentual de ROAS a mais representa lucro real.",
    "Quem cuida da retencao, nao precisa correr tanto pela aquisicao.",
    "O mercado muda. Quem se adapta primeiro, leva vantagem.",
    "Resultados extraordinarios sao consequencia de dias ordinarios bem vividos.",
    "Nao construa apenas campanhas. Construa funis completos.",
    "O sucesso nao e um destino. E um habito cultivado todo dia.",
    "Quem testa hipoteses com rapidez aprende mais rapido que os concorrentes.",
    "Cada segmentacao errada e dinheiro sendo dado a concorrencia.",
    "A melhor estrategia e a que voce consegue executar todos os dias.",
    "Negocio bom e aquele que funciona mesmo quando o dono nao esta.",
    "Nao meca apenas o que e facil medir. Meca o que importa.",
    "O cliente compra quando a dor supera o custo da solucao.",
    "Quem cria valor genuino nao precisa vender com desconto.",
    "Cada crise de campanha resolvida e expertise acumulada.",
    "A diferenca entre bom e excelente esta nos detalhes ignorados.",
    "Quem domina o remarketing, recupera dinheiro que ja foi investido.",
    "Planejamento sem execucao e so papel. Execute.",
    "O mercado digital nao dorme. Mas quem se prepara dorme tranquilo.",
    "Resultado consistente vem de processo consistente.",
    "Quem aprende com os dados de outros economiza meses de teste.",
    "A qualidade do seu servico determina a qualidade dos seus clientes.",
    "Nao espere o momento perfeito. Faca o momento ser perfeito.",
    "Quem sabe gerenciar expectativas, sabe fidelizar clientes.",
    "O crescimento nao e linear. Mas a disciplina precisa ser.",
    "Invista no que voce pode medir. Corte o que nao tem retorno.",
    "Cada cliente novo custa mais que manter um antigo. Pense nisso.",
    "Nao existe atalho para o resultado consistente. Existe processo.",
    "A campanha que converte e a que fala a lingua do cliente.",
    "Crescimento real comeca quando voce para de terceirizar a responsabilidade.",
    "Cada metrica tem uma historia. Aprenda a ouvi-las.",
    "O empresario que aprende nunca fica obsoleto.",
    "Quem sabe precificar, sabe crescer com saude financeira.",
    "Nao construa para o curto prazo. Construa para durar.",
    "O maior diferencial competitivo e a velocidade de aprendizado.",
    "Quem cuida do fluxo de caixa cuida do futuro do negocio.",
    "Resultados aparecem para quem nao desiste na terceira semana.",
    "O mercado recompensa a clareza de posicionamento.",
    "Cada decisao de hoje e o resultado de amanha.",
    "Quem age com dados tem confianca. Quem age com achismo, tem sorte.",
    "A excelencia nao e um evento. E uma escolha feita todos os dias.",
    "Nao espere o mercado mudar. Seja a mudanca que o mercado precisa.",
    "Cada meta batida e o combustivel para a proxima meta maior.",
    "O caminho para o extraordinario passa pelo ordinario bem feito.",
    "Quem investe em criativo investe em conversao.",
    "Dinheiro parado e oportunidade perdida. Faca ele trabalhar.",
    "O lucro real comeca quando o processo e replicavel.",
    "Cada cliente bem atendido e um contrato renovado.",
    "Nao espere chegar ao topo para acreditar no caminho.",
    "Quem domina sua niche domina seus resultados.",
    "A mentalidade certa abre portas que o mercado fecha.",
]


def gerar_frase_motivacional() -> str:
    dia_do_ano = datetime.now().timetuple().tm_yday
    indice = dia_do_ano % len(FRASES_MOTIVACIONAIS)
    return FRASES_MOTIVACIONAIS[indice]


def enviar_motivacional():
    cfg     = carregar_config()
    cfg_wpp = cfg["whatsapp"]
    grupo   = cfg_wpp["numeros_destino"][0]
    frase   = gerar_frase_motivacional()
    agora   = datetime.now().strftime("%d/%m/%Y")
    mensagem = (
        f"BOB cita:\n\n"
        f"Bora time, vamos fechar o dia com tudo!\n\n"
        f"{frase}\n\n"
        f"Que hoje seja um dia de grandes resultados!\n"
        f"{agora}"
    )
    log.info("Enviando mensagem motivacional do dia")
    ok = enviar_whatsapp(cfg_wpp, grupo, mensagem)
    if ok:
        log.info("Mensagem motivacional enviada!")
    else:
        log.error("Falha ao enviar mensagem motivacional")



# ── Comparativo de performance (relatorio interno da equipe) ─────

def analisar_comparativo():
    """Compara semana atual vs semana passada e alerta quedas de performance.
    Relatorio combinado enviado para o grupo interno da equipe — nao mexe
    no cadastro de clientes (veja enviar_comparativo_individual para isso)."""
    from datetime import datetime, timedelta, date

    hoje = date.today()
    dia_semana = hoje.weekday()  # 0=seg, 2=qua, 4=sex

    # Roda apenas segunda (0), quarta (2) e sexta (4)
    if dia_semana not in (0, 2, 4):
        return

    cfg         = carregar_config()
    token       = cfg["meta"]["contas"][0]["access_token"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp     = cfg["whatsapp"]
    grupo       = cfg_wpp["numeros_destino"][0]

    CONTAS_FOOD = [
        ("Rosa Sul Nova",          "act_2523170184768797"),
        ("Dia de Pizza Dourados",  "act_723575425785405"),
        ("IH Campo Grande",        "act_1131240581799095"),
        ("Mollinari Pizzaria",     "act_459274303920372"),
        ("MrGabs",                 "act_728296823243425"),
        ("IH Dourados",            "act_831936562721815"),
        ("Villa Grano Pizzaria",   "act_909424425271250"),
        ("Brados Pizzaria",        "act_972023765779926"),
        ("Berlim Pizzaria",        "act_836447545843342"),
        ("A Favorita",             "act_969681458906352"),
        ("Brava Pizza",            "act_4279801688941861"),
        ("Pavao Lanchonete",       "act_1759603645448352"),
        ("Fornalha Pizzaria",      "act_1618084519451450"),
        ("CA- Leni ADS 02",        "act_1569287454130140"),
        ("CA RJK SHOP",            "act_297417165372711"),
        ("CA - Miotto Construtora","act_213109970735074"),
        ("CA - ICGP",              "act_360815898753195"),
        ("CA - Miotto Backup",     "act_533683308259417"),
        ("CA - Monaco Agency",     "act_732966175219099"),
        ("BRUNA MACHADO - DOTCON", "act_1102427261426373"),
        ("CA - AMK Estetica",      "act_590117117342811"),
        ("JS - UNIFORME",          "act_1452225369942067"),
        ("SH Tijolos",             "act_3858259327816511"),
    ]

    # Periodos
    fim_atual    = hoje - timedelta(days=1)
    ini_atual    = fim_atual - timedelta(days=6)
    fim_anterior = ini_atual - timedelta(days=1)
    ini_anterior = fim_anterior - timedelta(days=6)

    def fmt_date(d): return d.strftime("%Y-%m-%d")
    def fmt_br(d): return d.strftime("%d/%m")

    def buscar_insights(account_id, since, until):
        time_range = '{' + f'"since":"{since}","until":"{until}"' + '}'
        url = (f"https://graph.facebook.com/{api_version}/{account_id}/insights"
               f"?fields=spend,actions,action_values,impressions,clicks"
               f"&time_range={time_range}"
               f"&access_token={token}")
        try:
            r = requests.get(url, timeout=20)
            data = r.json()
            if not data.get("data"):
                return {"gasto": 0, "pedidos": 0, "fat": 0, "cpr": 0, "leads": 0, "clicks": 0}
            ins = data["data"][0]
            gasto   = float(ins.get("spend", 0))
            actions = ins.get("actions", [])
            av      = ins.get("action_values", [])
            pedidos = int(next((a["value"] for a in actions if a["action_type"] == "purchase"), 0))
            fat     = float(next((a["value"] for a in av if a["action_type"] == "purchase"), 0))
            leads   = int(next((a["value"] for a in actions if a["action_type"] == "lead"), 0))
            clicks  = int(ins.get("clicks", 0))
            cpr     = gasto / pedidos if pedidos > 0 else 0
            cpl     = gasto / leads if leads > 0 else 0
            return {"gasto": gasto, "pedidos": pedidos, "fat": fat, "cpr": cpr, "leads": leads, "cpl": cpl, "clicks": clicks}
        except Exception as e:
            log.error(f"Erro insights comparativo [{account_id}]: {e}")
            return {"gasto": 0, "pedidos": 0, "fat": 0, "cpr": 0, "leads": 0, "cpl": 0, "clicks": 0}

    THRESHOLD = 0.10  # 10%

    alertas = []
    melhorias = []

    log.info("Iniciando analise comparativa de performance...")

    for nome_bm, account_id in CONTAS_FOOD:
        atual    = buscar_insights(account_id, fmt_date(ini_atual),    fmt_date(fim_atual))
        anterior = buscar_insights(account_id, fmt_date(ini_anterior), fmt_date(fim_anterior))

        # Pular contas sem dados nos dois periodos
        if atual["gasto"] == 0 and anterior["gasto"] == 0:
            continue

        problemas = []
        melhs = []

        # Comparar pedidos
        if anterior["pedidos"] > 0 and atual["pedidos"] > 0:
            var_ped = (atual["pedidos"] - anterior["pedidos"]) / anterior["pedidos"]
            if var_ped <= -THRESHOLD:
                problemas.append(f"  Pedidos: {anterior['pedidos']} → {atual['pedidos']} ({var_ped*100:.1f}%)")
            elif var_ped >= THRESHOLD:
                melhs.append(f"  Pedidos: {anterior['pedidos']} → {atual['pedidos']} (+{var_ped*100:.1f}%)")

        # Comparar CPR
        if anterior["cpr"] > 0 and atual["cpr"] > 0:
            var_cpr = (atual["cpr"] - anterior["cpr"]) / anterior["cpr"]
            if var_cpr >= THRESHOLD:
                problemas.append(f"  CPR: {fmt_brl(anterior['cpr'])} → {fmt_brl(atual['cpr'])} (+{var_cpr*100:.1f}%)")
            elif var_cpr <= -THRESHOLD:
                melhs.append(f"  CPR: {fmt_brl(anterior['cpr'])} → {fmt_brl(atual['cpr'])} ({var_cpr*100:.1f}%)")

        # Comparar leads
        if anterior["leads"] > 0 and atual["leads"] > 0:
            var_leads = (atual["leads"] - anterior["leads"]) / anterior["leads"]
            if var_leads <= -THRESHOLD:
                problemas.append(f"  Leads: {anterior['leads']} → {atual['leads']} ({var_leads*100:.1f}%)")
            elif var_leads >= THRESHOLD:
                melhs.append(f"  Leads: {anterior['leads']} → {atual['leads']} (+{var_leads*100:.1f}%)")

        # Comparar CPL
        if anterior["cpl"] > 0 and atual["cpl"] > 0:
            var_cpl = (atual["cpl"] - anterior["cpl"]) / anterior["cpl"]
            if var_cpl >= THRESHOLD:
                problemas.append(f"  CPL: {fmt_brl(anterior['cpl'])} → {fmt_brl(atual['cpl'])} (+{var_cpl*100:.1f}%)")
            elif var_cpl <= -THRESHOLD:
                melhs.append(f"  CPL: {fmt_brl(anterior['cpl'])} → {fmt_brl(atual['cpl'])} ({var_cpl*100:.1f}%)")

        # Comparar faturamento
        if anterior["fat"] > 0 and atual["fat"] > 0:
            var_fat = (atual["fat"] - anterior["fat"]) / anterior["fat"]
            if var_fat <= -THRESHOLD:
                problemas.append(f"  Faturamento: {fmt_brl(anterior['fat'])} → {fmt_brl(atual['fat'])} ({var_fat*100:.1f}%)")

        if problemas:
            alertas.append({"bm": nome_bm, "problemas": problemas})
        if melhs:
            melhorias.append({"bm": nome_bm, "melhs": melhs})

    if not alertas and not melhorias:
        log.info("Comparativo: nenhuma variacao significativa detectada.")
        return

    periodo_txt = f"{fmt_br(ini_atual)} - {fmt_br(fim_atual)}"
    anterior_txt = f"{fmt_br(ini_anterior)} - {fmt_br(fim_anterior)}"
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    linhas = [
        f"Analise de Performance — BOB",
        f"Monaco Agency | {agora_str}",
        f"",
        f"Periodo atual:   {periodo_txt}",
        f"Periodo anterior: {anterior_txt}",
        f"Variacao minima: 10%",
        f"",
    ]

    if alertas:
        linhas.append(f"ATENCAO — Queda de performance ({len(alertas)} conta(s))")
        linhas.append("")
        for a in alertas:
            linhas.append(f"  {a['bm']}")
            linhas += a["problemas"]
            linhas.append("")

    if melhorias:
        linhas.append(f"MELHORIA — Evolucao positiva ({len(melhorias)} conta(s))")
        linhas.append("")
        for m in melhorias:
            linhas.append(f"  {m['bm']}")
            linhas += m["melhs"]
            linhas.append("")

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append(f"Resumo: {len(alertas)} alerta(s) | {len(melhorias)} melhoria(s)")

    mensagem = "\n".join(linhas)
    ok = enviar_whatsapp(cfg_wpp, grupo, mensagem)
    if ok:
        log.info(f"Comparativo enviado: {len(alertas)} alertas, {len(melhorias)} melhorias")
    else:
        log.error("Falha ao enviar comparativo")

# ── Loop principal ────────────────────────────────────────────────

def rodar_loop():
    cfg          = carregar_config()
    horario_alvo = cfg["alertas"].get("horario_verificacao", "15:00")

    # Horarios em UTC (Railway usa UTC — BRT = UTC-3)
    # 07:00 BRT = 10:00 UTC — motivacional
    # 08:00 BRT = 11:00 UTC — encerramentos
    # 09:00 BRT = 12:00 UTC — comparativo interno (seg/qua/sex)
    # 10:00 BRT = 13:00 UTC — comparativo individual por cliente (seg/qua/sex)
    # 12:00 BRT = 15:00 UTC — saldo
    # 15:00 BRT = 18:00 UTC — relatorio de performance por cliente
    horario_motivacional  = "10:00"  # 07:00 BRT
    horario_encerramentos = "11:00"  # 08:00 BRT
    horario_comparativo   = "12:00"  # 09:00 BRT — seg, qua, sex
    horario_comp_indiv    = "13:00"  # 10:00 BRT — seg, qua, sex
    horario_performance   = "18:00"  # 15:00 BRT — diario

    log.info("Monitor de BMs iniciado")
    log.info(f"  Motivacional:        {horario_motivacional} UTC (07:00 BRT)")
    log.info(f"  Encerramentos:       {horario_encerramentos} UTC (08:00 BRT)")
    log.info(f"  Comparativo interno: {horario_comparativo} UTC (09:00 BRT) — seg/qua/sex")
    log.info(f"  Comparativo cliente: {horario_comp_indiv} UTC (10:00 BRT) — seg/qua/sex")
    log.info(f"  Saldo:               {horario_alvo} UTC (12:00 BRT)")
    log.info(f"  Performance cliente: {horario_performance} UTC (15:00 BRT)")
    log.info(f"  Contas:              {len(cfg['meta']['contas'])}")
    log.info(f"  Limite critico:      {fmt_brl(cfg['alertas']['limite_critico'])}")
    log.info(f"  Limite baixo:        {fmt_brl(cfg['alertas']['limite_baixo'])}")
    log.info("")

    ultimo_dia_motivacional  = None
    ultimo_dia_encerramentos = None
    ultimo_dia_comparativo   = None
    ultimo_dia_comp_indiv    = None
    ultimo_dia_saldo         = None
    ultimo_dia_performance   = None

    while True:
        agora      = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        hoje       = agora.date()

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

        if hora_atual == horario_comparativo and ultimo_dia_comparativo != hoje:
            ultimo_dia_comparativo = hoje
            try:
                analisar_comparativo()
            except Exception as e:
                log.exception(f"Erro comparativo: {e}")

        if hora_atual == horario_comp_indiv and ultimo_dia_comp_indiv != hoje:
            ultimo_dia_comp_indiv = hoje
            try:
                enviar_comparativo_individual()
            except Exception as e:
                log.exception(f"Erro comparativo individual: {e}")

        if hora_atual == horario_alvo and ultimo_dia_saldo != hoje:
            ultimo_dia_saldo = hoje
            try:
                verificar_e_alertar()
            except Exception as e:
                log.exception(f"Erro saldo: {e}")

        if hora_atual == horario_performance and ultimo_dia_performance != hoje:
            ultimo_dia_performance = hoje
            try:
                enviar_relatorios_performance()
            except Exception as e:
                log.exception(f"Erro performance: {e}")

        h, m = map(int, horario_alvo.split(":"))
        proximo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
        if proximo <= agora:
            proximo += timedelta(days=1)
        falta   = proximo - agora
        horas   = int(falta.total_seconds() // 3600)
        minutos = int((falta.total_seconds() % 3600) // 60)
        log.info(f"Proxima verificacao de saldo em {horas}h {minutos}min")

        time.sleep(60)


if __name__ == "__main__":
    rodar_loop()
