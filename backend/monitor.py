"""
Monitor de Saldo de BMs do Meta
Consulta saldo via API do Meta e dispara alertas via WhatsApp (Evolution API)
"""

import json
import time
import logging
import requests
from datetime import datetime, date, timedelta
from pathlib import Path

# ── Configuração de log ──────────────────────────────────────────────────────
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


# ── Helpers ──────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    import os
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    # GitHub Actions — usar variaveis de ambiente
    return {
        "meta": {
            "api_version": "v19.0",
            "contas": [{"nome": "Monaco", "account_id": "", "access_token": os.getenv("META_TOKEN", "")}]
        },
        "alertas": {
            "limite_critico": 50,
            "limite_baixo": 100,
            "horario_verificacao": "12:00",
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


# ── API do Meta ──────────────────────────────────────────────────────────────

def consultar_saldo(account_id: str, token: str, api_version: str) -> dict | None:
    """
    Consulta saldo e limite de gasto de uma conta de anúncios do Meta.
    Retorna dict com name, balance, spend_cap ou None em caso de erro.
    """
    url = f"https://graph.facebook.com/{api_version}/{account_id}"
    params = {
        "fields": "name,balance,spend_cap,amount_spent,currency,account_status",
        "access_token": token,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            log.error(f"Erro API Meta [{account_id}]: {data['error'].get('message')}")
            return None

        # A API retorna valores em centavos
        raw_balance = int(data.get("balance", 0))
        raw_spend_cap = int(data.get("spend_cap", 0))
        raw_amount_spent = int(data.get("amount_spent", 0))

        # balance retorna apenas o saldo residual do dia (não o total real)
        # O saldo real é: spend_cap - amount_spent
        spend_cap = raw_spend_cap / 100
        amount_spent = raw_amount_spent / 100

        if spend_cap > 0 and amount_spent >= 0:
            balance = spend_cap - amount_spent
        else:
            balance = raw_balance / 100

        return {
            "account_id": account_id,
            "nome": data.get("name", account_id),
            "balance": balance,
            "spend_cap": spend_cap,
            "currency": data.get("currency", "BRL"),
            "status": data.get("account_status", 1),
        }

    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao consultar [{account_id}]: {e}")
        return None


# ── WhatsApp (Evolution API) ─────────────────────────────────────────────────

def enviar_whatsapp(cfg_wpp: dict, numero: str, mensagem: str) -> bool:
    """
    Envia mensagem via Evolution API.
    Adapte o endpoint se usar Z-API ou outra solução.
    """
    url = f"{cfg_wpp['api_url']}/message/sendText/{cfg_wpp['instancia']}"
    headers = {
        "apikey": cfg_wpp["api_key"],
        "Content-Type": "application/json",
    }
    payload = {
        "number": numero,
        "textMessage": {"text": mensagem},
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        log.info(f"✅ Alerta enviado para {numero}")
        return True
    except requests.exceptions.RequestException as e:
        log.error(f"Falha ao enviar WhatsApp para {numero}: {e}")
        return False


def montar_mensagem(conta: dict, nivel: str, limite: float) -> str:
    emoji = "🚨" if nivel == "critico" else "⚠️"
    label = "CRÍTICO" if nivel == "critico" else "BAIXO"
    linhas = [
        f"{emoji} *Alerta de Saldo {label}*",
        "",
        f"📊 *BM:* {conta['nome']}",
        f"💰 *Saldo atual:* {fmt_brl(conta['balance'])}",
        f"📉 *Limite de alerta:* {fmt_brl(limite)}",
    ]
    if conta["spend_cap"] > 0:
        linhas.append(f"🔝 *Limite de gasto:* {fmt_brl(conta['spend_cap'])}")
    linhas += [
        "",
        "_Recarregue o saldo para evitar interrupções nas campanhas._",
        f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    ]
    return "\n".join(linhas)


# ── Lógica principal ─────────────────────────────────────────────────────────

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

    log.info(f"=== Iniciando verificação — {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")

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

        # Determinar nível do alerta
        if balance <= limite_critico:
            nivel = "critico"
            limite_ref = limite_critico
        elif balance <= limite_baixo:
            nivel = "baixo"
            limite_ref = limite_baixo
        else:
            log.info(f"  Status: OK ✓")
            # Resetar flag do dia se saldo voltou ao normal
            if account_id in alertas_enviados:
                del alertas_enviados[account_id]
                salvar_alertas_enviados(alertas_enviados)
            continue

        # Verificar deduplicação
        if uma_vez_por_dia:
            ultimo = alertas_enviados.get(account_id, {})
            if ultimo.get("data") == hoje and ultimo.get("nivel") == nivel:
                log.info(f"  Alerta já enviado hoje para {nome} ({nivel}) — pulando")
                continue

        # Montar e enviar alertas
        mensagem = montar_mensagem(conta, nivel, limite_ref)
        log.info(f"  🔔 Disparando alerta [{nivel.upper()}] para {len(numeros)} número(s)")

        enviou = False
        for numero in numeros:
            ok = enviar_whatsapp(cfg_wpp, numero, mensagem)
            if ok:
                enviou = True

        if enviou:
            alertas_enviados[account_id] = {
                "data": hoje,
                "nivel": nivel,
                "balance": balance,
                "hora": datetime.now().strftime("%H:%M"),
                "nome": nome,
            }
            salvar_alertas_enviados(alertas_enviados)

    log.info("=== Verificação concluída ===\n")


def consultar_insights(account_id: str, token: str, api_version: str, since: str, until: str) -> dict:
    """Consulta métricas de performance de uma conta para um período."""
    url = f"https://graph.facebook.com/{api_version}/{account_id}/insights"
    params = {
        "fields": "spend,actions,action_values",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "access_token": token,
    }
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


def enviar_relatorio_segunda():
    """Gera e envia o relatório de final de semana (sex/sab/dom) toda segunda às 09h."""
    cfg = carregar_config()
    token = cfg["meta"]["contas"][0]["access_token"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp = cfg["whatsapp"]

    # Calcular sexta, sabado e domingo anteriores
    hoje = date.today()
    domingo = hoje - timedelta(days=1)   # ontem = domingo
    sabado  = hoje - timedelta(days=2)
    sexta   = hoje - timedelta(days=3)
    since = sexta.strftime("%Y-%m-%d")
    until = domingo.strftime("%Y-%m-%d")
    periodo_label = f"{sexta.strftime('%d/%m/%Y')} até {domingo.strftime('%d/%m/%Y')}"

    log.info(f"📊 Gerando relatório de final de semana ({periodo_label})")

    total_gasto = 0
    total_pedidos = 0
    total_fat = 0
    otimos = []
    atencao = []
    criticos = []
    sem_dados = []

    for conta in cfg["meta"]["contas"]:
        # Só food (exclui contas de outros segmentos)
        outros = ["act_297417165372711","act_213109970735074","act_360815898753195",
                  "act_533683308259417","act_732966175219099","act_1102427261426373",
                  "act_590117117342811","act_1288527439639093","act_1452225369942067",
                  "act_3858259327816511","act_105301940058633"]
        if conta["account_id"] in outros:
            continue

        ins = consultar_insights(conta["account_id"], token, api_version, since, until)
        total_gasto += ins["gasto"]
        total_pedidos += ins["pedidos"]
        total_fat += ins["faturamento"]

        nome = conta["nome"]
        if ins["gasto"] == 0:
            sem_dados.append(nome)
        elif ins["roas"] >= 10 or ins["cpr"] <= 15:
            otimos.append((nome, ins))
        elif ins["roas"] >= 1.5 or ins["cpr"] <= 40:
            atencao.append((nome, ins))
        else:
            criticos.append((nome, ins))

    roas_medio = total_fat / total_gasto if total_gasto > 0 else 0
    cpr_medio = total_gasto / total_pedidos if total_pedidos > 0 else 0

    def fmt(v): return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    linhas = [
        f"📊 *Relatório de Final de Semana*",
        f"Monaco Agency | {periodo_label}",
        "",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"💰 Investimento total: *{fmt(total_gasto)}*",
        f"🛒 Faturamento total: *{fmt(total_fat)}*",
        f"📦 Pedidos totais: *{total_pedidos}*",
        f"🚀 ROAS médio: *{roas_medio:.2f}x*",
        f"📉 CPR médio: *{fmt(cpr_medio)}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if otimos:
        linhas.append("🏆 *TOP PERFORMERS*")
        for nome, ins in sorted(otimos, key=lambda x: x[1]["roas"], reverse=True):
            linhas.append(f"  ✅ {nome}")
            linhas.append(f"      Pedidos: {ins['pedidos']} | Fat: {fmt(ins['faturamento'])} | ROAS: {ins['roas']:.2f}x | CPR: {fmt(ins['cpr'])}")
        linhas.append("")

    if atencao:
        linhas.append("⚠️ *ATENÇÃO*")
        for nome, ins in atencao:
            linhas.append(f"  🟡 {nome}")
            linhas.append(f"      Pedidos: {ins['pedidos']} | Fat: {fmt(ins['faturamento'])} | ROAS: {ins['roas']:.2f}x | CPR: {fmt(ins['cpr'])}")
        linhas.append("")

    if criticos:
        linhas.append("🔴 *CRÍTICO / SEM RESULTADO*")
        for nome, ins in criticos:
            linhas.append(f"  ❌ {nome}")
            linhas.append(f"      Gasto: {fmt(ins['gasto'])} | Pedidos: {ins['pedidos']} | ROAS: {ins['roas']:.2f}x")
        linhas.append("")

    if sem_dados:
        linhas.append("⚫ *SEM DADOS NO PERÍODO*")
        for nome in sem_dados:
            linhas.append(f"  • {nome}")

    mensagem = "\n".join(linhas)
    grupo = cfg_wpp["numeros_destino"][0]

    log.info(f"📤 Enviando relatório para {grupo}")
    ok = enviar_whatsapp(cfg_wpp, grupo, mensagem)
    if ok:
        log.info("✅ Relatório de segunda enviado com sucesso!")
    else:
        log.error("❌ Falha ao enviar relatório de segunda")


def rodar_agente_automatico():
    """Analisa todas as campanhas das BMs food e envia alertas críticos/atenção no grupo."""
    cfg = carregar_config()
    token = cfg["meta"]["contas"][0]["access_token"]
    api_version = cfg["meta"]["api_version"]
    cfg_wpp = cfg["whatsapp"]
    grupo = cfg_wpp["numeros_destino"][0]

CONTAS_FOOD = [
    ("Rosa Sul Nova", "act_2523170184768797"),
    ("Dia de Pizza Dourados", "act_723575425785405"),
    ("IH Campo Grande", "act_1131240581799095"),
    ("Mollinari", "act_459274303920372"),
    ("MrGabs", "act_728296823243425"),
    ("IH Dourados", "act_831936562721815"),
    ("Villa Grano", "act_909424425271250"),
    ("Brados", "act_972023765779926"),
    ("Berlim", "act_836447545843342"),
    ("A Favorita", "act_969681458906352"),
    ("Brava Pizza", "act_4279801688941861"),
    ("Pavão", "act_1759603645448352"),
    ("Fornalha", "act_1618084519451450"),
]
    log.info("🤖 BOB iniciado — analisando campanhas...")

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

                # Dias restantes
                dias_rest = None
                if camp.get("stop_time"):
                    stop = datetime.fromisoformat(camp["stop_time"].replace("Z", "+00:00")).date()
                    dias_rest = (stop - hoje).days

                # Orçamento
                lifetime = float(camp.get("lifetime_budget", 0)) / 100
                remaining = float(camp.get("budget_remaining", 0)) / 100
                pct_gasto = ((lifetime - remaining) / lifetime * 100) if lifetime > 0 else 0

                camp_info = {
                    "bm": nome_bm,
                    "camp": camp["name"],
                    "gasto": gasto,
                    "pedidos": pedidos,
                    "roas": roas,
                    "dias_rest": dias_rest,
                    "ads_ativos": len(ads_ativos),
                }

                # Classificar alertas
                if status == "ACTIVE":
                    if gasto > 0 and pedidos == 0:
                        camp_info["motivo"] = "🚨 Gasto sem retorno"
                        alertas_criticos.append(camp_info)
                    elif gasto > 0 and roas < 1.5:
                        camp_info["motivo"] = f"📉 ROAS crítico ({roas:.2f}x)"
                        alertas_criticos.append(camp_info)
                    elif pct_gasto > 90:
                        camp_info["motivo"] = f"💸 Orçamento {pct_gasto:.0f}% esgotado"
                        alertas_criticos.append(camp_info)
                    elif dias_rest is not None and 0 < dias_rest <= 2:
                        camp_info["motivo"] = f"⏰ Encerra em {dias_rest} dia(s)"
                        alertas_criticos.append(camp_info)
                    elif gasto > 0 and 1.5 <= roas < 3:
                        camp_info["motivo"] = f"⚠️ ROAS abaixo do ideal ({roas:.2f}x)"
                        alertas_atencao.append(camp_info)
                    elif pct_gasto > 70:
                        camp_info["motivo"] = f"💰 Orçamento {pct_gasto:.0f}% gasto"
                        alertas_atencao.append(camp_info)
                    elif dias_rest is not None and 2 < dias_rest <= 7:
                        camp_info["motivo"] = f"📅 Encerra em {dias_rest} dias"
                        alertas_atencao.append(camp_info)

        except Exception as e:
            log.error(f"Erro agente [{nome_bm}]: {e}")

    if not alertas_criticos and not alertas_atencao:
        log.info("✅ Agente: nenhum alerta encontrado — tudo saudável!")
        return

    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = [
        f"🤖 *Relatório do BOB — Agente de Tráfego*",
        f"Monaco Agency | {agora_str}",
        "",
    ]

    if alertas_criticos:
        linhas.append(f"🔴 *CRÍTICO ({len(alertas_criticos)} alerta(s))*")
        for a in alertas_criticos:
            linhas.append(f"  ❗ *{a['bm']}*")
            linhas.append(f"  📢 {a['camp']}")
            linhas.append(f"  {a['motivo']}")
            if a['dias_rest'] is not None:
                linhas.append(f"  ⏰ {a['dias_rest']} dia(s) para encerrar")
            linhas.append("")

    if alertas_atencao:
        linhas.append(f"⚠️ *ATENÇÃO ({len(alertas_atencao)} alerta(s))*")
        for a in alertas_atencao:
            linhas.append(f"  ⚠ *{a['bm']}*")
            linhas.append(f"  📢 {a['camp']}")
            linhas.append(f"  {a['motivo']}")
            if a['dias_rest'] is not None:
                linhas.append(f"  ⏰ {a['dias_rest']} dia(s) para encerrar")
            linhas.append("")

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append(f"Total: {len(alertas_criticos)} crítico(s) | {len(alertas_atencao)} atenção")

    mensagem = "\n".join(linhas)
    ok = enviar_whatsapp(cfg_wpp, grupo, mensagem)
    if ok:
        log.info(f"✅ BOB: relatório enviado — {len(alertas_criticos)} críticos, {len(alertas_atencao)} atenção")
    else:
        log.error("❌ BOB: falha ao enviar relatório")


def rodar_loop():
    cfg = carregar_config()
    horario_alvo = cfg["alertas"].get("horario_verificacao", "12:00")

    log.info("🚀 Monitor de BMs iniciado")
    log.info(f"   Horário de verificação: {horario_alvo} (diário)")
    log.info(f"   Contas monitoradas: {len(cfg['meta']['contas'])}")
    log.info(f"   Limite crítico: {fmt_brl(cfg['alertas']['limite_critico'])}")
    log.info(f"   Limite baixo: {fmt_brl(cfg['alertas']['limite_baixo'])}")
    log.info("")

    ultimo_dia_executado = None

    while True:
        agora = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        hoje = agora.date()

        if hora_atual == horario_alvo and ultimo_dia_executado != hoje:
            ultimo_dia_executado = hoje
            try:
                verificar_e_alertar()
            except Exception as e:
                log.exception(f"Erro inesperado na verificação: {e}")
        else:
            h, m = map(int, horario_alvo.split(":"))
            proximo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
            if proximo <= agora:
                proximo += timedelta(days=1)
            falta = proximo - agora
            horas = int(falta.total_seconds() // 3600)
            minutos = int((falta.total_seconds() % 3600) // 60)
            log.info(f"⏳ Próxima verificação às {horario_alvo} (faltam {horas}h {minutos}min)")

        time.sleep(60)


if __name__ == "__main__":
    rodar_loop()


