"""
Gera o relatório HTML de auditoria estilo CEO
Rode depois do auditoria_coletar.py
"""
import json
from datetime import date

with open("auditoria_dados.json", encoding="utf-8") as f:
    raw = json.load(f)

dados = raw["dados"]
periodo = raw["periodo"]
gerado = raw["gerado_em"]

def fmt(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def fmtN(v): return f"{int(v):,}".replace(",",".")

# Classificar risco de cancelamento
def risco(d):
    t = d["total"]
    if t["gasto"] == 0: return "alto", "⛔ Sem atividade"
    if t["pedidos"] == 0: return "alto", "🔴 Gasto sem retorno"
    if t["roas"] < 1.5: return "alto", "🔴 ROAS crítico"
    if t["roas"] < 3: return "medio", "🟡 ROAS abaixo do ideal"
    m1, m2 = d["m1"], d["m2"]
    if m1.get("roas",0) > 0 and m2.get("roas",0) > 0:
        queda = (m1["roas"] - m2["roas"]) / m1["roas"] * 100 if m1["roas"] > 0 else 0
        if queda > 30: return "medio", "🟡 Queda de performance"
    return "baixo", "🟢 Saudável"

# Ordenar por risco e ROAS
ordem_risco = {"alto": 0, "medio": 1, "baixo": 2}
dados_sorted = sorted(dados, key=lambda d: (ordem_risco[risco(d)[0]], -d["total"].get("gasto", 0)))

# Calcular totais
total_gasto = sum(d["total"]["gasto"] for d in dados)
total_pedidos = sum(d["total"]["pedidos"] for d in dados)
total_fat = sum(d["total"]["fat"] for d in dados)
roas_geral = total_fat / total_gasto if total_gasto > 0 else 0
cpr_geral = total_gasto / total_pedidos if total_pedidos > 0 else 0

alto_risco = [d for d in dados if risco(d)[0] == "alto"]
medio_risco = [d for d in dados if risco(d)[0] == "medio"]
baixo_risco = [d for d in dados if risco(d)[0] == "baixo"]

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Auditoria 60 Dias — Monaco Agency</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; }}
.cover {{ background: linear-gradient(135deg, #0f1117 0%, #1e3a5f 100%); color: #fff; padding: 60px 48px; }}
.cover-logo {{ font-size: 13px; color: rgba(255,255,255,.5); margin-bottom: 20px; letter-spacing: 2px; text-transform: uppercase; }}
.cover-title {{ font-size: 36px; font-weight: 700; margin-bottom: 8px; }}
.cover-sub {{ font-size: 16px; color: rgba(255,255,255,.6); margin-bottom: 32px; }}
.cover-meta {{ display: flex; gap: 32px; flex-wrap: wrap; }}
.cover-meta-item {{ }}
.cover-meta-label {{ font-size: 11px; color: rgba(255,255,255,.4); text-transform: uppercase; letter-spacing: 1px; }}
.cover-meta-val {{ font-size: 18px; font-weight: 600; color: #60a5fa; margin-top: 4px; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 40px 32px; }}
.section-title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin: 40px 0 16px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 32px; }}
.card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 18px; }}
.card-label {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }}
.card-val {{ font-size: 22px; font-weight: 700; color: #0f172a; }}
.card-val.green {{ color: #059669; }}
.card-val.red {{ color: #dc2626; }}
.card-val.blue {{ color: #2563eb; }}
.risk-summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 32px; }}
.risk-card {{ border-radius: 12px; padding: 18px 20px; }}
.risk-card.alto {{ background: #fef2f2; border: 1px solid #fecaca; }}
.risk-card.medio {{ background: #fffbeb; border: 1px solid #fde68a; }}
.risk-card.baixo {{ background: #f0fdf4; border: 1px solid #bbf7d0; }}
.risk-num {{ font-size: 36px; font-weight: 800; }}
.risk-card.alto .risk-num {{ color: #dc2626; }}
.risk-card.medio .risk-num {{ color: #d97706; }}
.risk-card.baixo .risk-num {{ color: #059669; }}
.risk-label {{ font-size: 13px; font-weight: 600; margin-top: 4px; }}
.risk-card.alto .risk-label {{ color: #991b1b; }}
.risk-card.medio .risk-label {{ color: #92400e; }}
.risk-card.baixo .risk-label {{ color: #065f46; }}
.risk-desc {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
.client-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; }}
.client-card.alto {{ border-left: 4px solid #dc2626; }}
.client-card.medio {{ border-left: 4px solid #d97706; }}
.client-card.baixo {{ border-left: 4px solid #059669; }}
.client-header {{ display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }}
.client-name {{ font-size: 16px; font-weight: 700; color: #0f172a; }}
.client-id {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}
.risk-badge {{ font-size: 11px; padding: 4px 10px; border-radius: 99px; font-weight: 600; }}
.risk-badge.alto {{ background: #fee2e2; color: #991b1b; }}
.risk-badge.medio {{ background: #fef3c7; color: #92400e; }}
.risk-badge.baixo {{ background: #d1fae5; color: #065f46; }}
.metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin-bottom: 14px; }}
.metric {{ background: #f8fafc; border-radius: 8px; padding: 10px 12px; }}
.metric-label {{ font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }}
.metric-val {{ font-size: 14px; font-weight: 700; color: #0f172a; }}
.metric-val.green {{ color: #059669; }}
.metric-val.red {{ color: #dc2626; }}
.metric-val.amber {{ color: #d97706; }}
.evolucao {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }}
.evo-card {{ background: #f8fafc; border-radius: 8px; padding: 10px 14px; }}
.evo-title {{ font-size: 11px; color: #94a3b8; margin-bottom: 6px; }}
.evo-row {{ display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }}
.evo-key {{ color: #64748b; }}
.evo-val {{ font-weight: 600; color: #0f172a; }}
.delta {{ font-size: 11px; padding: 1px 6px; border-radius: 4px; }}
.delta-up {{ background: #d1fae5; color: #065f46; }}
.delta-dn {{ background: #fee2e2; color: #991b1b; }}
.diagnostico {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; font-size: 13px; color: #78350f; line-height: 1.6; }}
.caminhos {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.caminho {{ border-radius: 8px; padding: 12px 14px; font-size: 12px; line-height: 1.6; }}
.caminho.conservador {{ background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }}
.caminho.agressivo {{ background: #fdf4ff; border: 1px solid #e9d5ff; color: #6b21a8; }}
.caminho-title {{ font-weight: 700; margin-bottom: 6px; font-size: 13px; }}
.funil {{ display: flex; gap: 8px; align-items: center; font-size: 12px; color: #64748b; margin: 8px 0; flex-wrap: wrap; }}
.funil-step {{ background: #f1f5f9; padding: 3px 8px; border-radius: 4px; }}
.funil-arrow {{ color: #94a3b8; }}
.page-break {{ page-break-before: always; }}
@media print {{
  .client-card {{ page-break-inside: avoid; }}
  body {{ background: #fff; }}
}}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-logo">Monaco Agency — Confidencial</div>
  <div class="cover-title">Auditoria de Performance<br>Meta Ads — 60 Dias</div>
  <div class="cover-sub">Análise estratégica para tomada de decisão executiva</div>
  <div class="cover-meta">
    <div class="cover-meta-item"><div class="cover-meta-label">Período</div><div class="cover-meta-val">{periodo}</div></div>
    <div class="cover-meta-item"><div class="cover-meta-label">Gerado em</div><div class="cover-meta-val">{gerado}</div></div>
    <div class="cover-meta-item"><div class="cover-meta-label">Clientes analisados</div><div class="cover-meta-val">{len(dados)}</div></div>
    <div class="cover-meta-item"><div class="cover-meta-label">Investimento total</div><div class="cover-meta-val">{fmt(total_gasto)}</div></div>
  </div>
</div>

<div class="container">

  <div class="section-title">📊 Visão Executiva — Portfólio</div>
  <div class="cards">
    <div class="card"><div class="card-label">💰 Investimento</div><div class="card-val">{fmt(total_gasto)}</div></div>
    <div class="card"><div class="card-label">🛒 Faturamento</div><div class="card-val green">{fmt(total_fat)}</div></div>
    <div class="card"><div class="card-label">📦 Pedidos</div><div class="card-val">{fmtN(total_pedidos)}</div></div>
    <div class="card"><div class="card-label">🚀 ROAS Geral</div><div class="card-val {"green" if roas_geral >= 3 else "red"}">{roas_geral:.2f}x</div></div>
    <div class="card"><div class="card-label">📉 CPR Médio</div><div class="card-val">{fmt(cpr_geral)}</div></div>
    <div class="card"><div class="card-label">🎫 Ticket Médio</div><div class="card-val blue">{fmt(total_fat/total_pedidos) if total_pedidos > 0 else "—"}</div></div>
  </div>

  <div class="section-title">⚠️ Mapa de Risco — Probabilidade de Cancelamento</div>
  <div class="risk-summary">
    <div class="risk-card alto">
      <div class="risk-num">{len(alto_risco)}</div>
      <div class="risk-label">🔴 Alto Risco</div>
      <div class="risk-desc">Sem resultado ou ROAS abaixo de 1.5x. Cancelamento iminente se não houver intervenção.</div>
    </div>
    <div class="risk-card medio">
      <div class="risk-num">{len(medio_risco)}</div>
      <div class="risk-label">🟡 Risco Médio</div>
      <div class="risk-desc">Performance abaixo do ideal ou em queda. Requer atenção nos próximos 15 dias.</div>
    </div>
    <div class="risk-card baixo">
      <div class="risk-num">{len(baixo_risco)}</div>
      <div class="risk-label">🟢 Saudável</div>
      <div class="risk-desc">ROAS acima de 3x com estabilidade. Foco em escala.</div>
    </div>
  </div>

  <div class="section-title">🔍 Análise Individual por Cliente</div>
"""

for d in dados_sorted:
    t = d["total"]
    m1 = d.get("m1", {})
    m2 = d.get("m2", {})
    nivel, motivo = risco(d)

    roas_color = "green" if t["roas"] >= 3 else "amber" if t["roas"] >= 1.5 else "red"
    cpr_color = "green" if t["cpr"] > 0 and t["cpr"] <= 15 else "amber" if t["cpr"] <= 30 else "red"

    # Calcular delta entre períodos
    def delta_html(v1, v2, higher_better=True):
        if not v1 or not v2: return ""
        pct = (v2 - v1) / v1 * 100 if v1 > 0 else 0
        up = pct > 0
        good = up if higher_better else not up
        cls = "delta-up" if good else "delta-dn"
        return f'<span class="delta {cls}">{"+" if up else ""}{pct:.0f}%</span>'

    # Diagnóstico personalizado
    diag = ""
    if t["gasto"] == 0:
        diag = "⛔ Conta sem nenhum investimento nos últimos 60 dias. Campanhas inativas ou sem orçamento. Risco muito alto de perda do cliente por falta de resultados visíveis."
    elif t["pedidos"] == 0:
        diag = f"🚨 Investimento de {fmt(t['gasto'])} sem nenhuma venda registrada. O pixel pode estar mal configurado, os criativos não estão convertendo ou o público está errado. Situação crítica."
    elif t["roas"] < 1.5:
        diag = f"📉 ROAS de {t['roas']:.2f}x indica que a campanha está no prejuízo — para cada R$ 1 investido, retorna apenas R$ {t['roas']:.2f}. Com ticket médio de {fmt(t['ticket'])}, a operação não se sustenta."
    elif t["roas"] < 3:
        diag = f"⚠️ ROAS de {t['roas']:.2f}x está abaixo do mínimo recomendado de 3x para delivery food. Com {t['pedidos']} pedidos e CPR de {fmt(t['cpr'])}, há espaço para otimização significativa."
    else:
        queda_roas = ""
        if m1.get("roas", 0) > 0 and m2.get("roas", 0) > 0:
            delta = (m1["roas"] - m2["roas"]) / m1["roas"] * 100
            if delta > 20:
                queda_roas = f" Atenção: ROAS caiu {delta:.0f}% no segundo mês ({m1['roas']:.2f}x → {m2['roas']:.2f}x) — sinal de saturação de público ou criativo."
        diag = f"✅ Performance positiva com ROAS {t['roas']:.2f}x e {t['pedidos']} pedidos. Ticket médio de {fmt(t['ticket'])} é saudável.{queda_roas} Foco em escalar o que está funcionando."

    # Dois caminhos
    if nivel == "alto":
        c1 = f"""<div class="caminho-title">🔵 Caminho 1 — Diagnóstico e reconstrução (7-14 dias)</div>
1. Auditar pixel e eventos de conversão — verificar se purchase está disparando corretamente<br>
2. Pausar todos os conjuntos com CPA acima de {fmt(t['cpr']*1.5 if t['cpr'] > 0 else 50)}<br>
3. Criar 1 campanha limpa com público amplo (mulher 25-44, raio 5km) e 2-3 criativos novos<br>
4. Orçamento mínimo R$ 30/dia para coleta de dados sem pressão<br>
5. Revisão em 7 dias para decidir escala"""
        c2 = f"""<div class="caminho-title">🟣 Caminho 2 — Intervenção urgente (48h)</div>
1. Reunião imediata com o cliente para alinhar expectativas e evitar cancelamento<br>
2. Apresentar diagnóstico técnico com dados concretos<br>
3. Propor período de teste de 15 dias com nova estrutura de campanha<br>
4. Definir meta clara: mínimo 10 pedidos com CPA abaixo de R$ 25<br>
5. Check-in semanal para mostrar evolução"""
    elif nivel == "medio":
        c1 = f"""<div class="caminho-title">🔵 Caminho 1 — Otimização gradual (15-30 dias)</div>
1. Identificar o conjunto com melhor ROAS e aumentar orçamento em 20%<br>
2. Pausar criativos com CTR abaixo de 1% e frequência acima de 3x<br>
3. Inserir 2 novos criativos (1 vídeo + 1 estático) a cada 2 semanas<br>
4. Ativar retargeting para visitantes do cardápio sem compra<br>
5. Meta: atingir ROAS 4x em 30 dias"""
        c2 = f"""<div class="caminho-title">🟣 Caminho 2 — Reestruturação de público (7-15 dias)</div>
1. Criar lookalike 1% baseado nos compradores existentes<br>
2. Testar segmentação por interesses específicos (delivery, pizza, fast food)<br>
3. Separar campanhas por dia da semana (qui-dom têm maior conversão)<br>
4. Testar oferta de entrada: frete grátis ou combo especial para novos clientes<br>
5. Analisar horários de pico e concentrar verba das 18h às 22h"""
    else:
        c1 = f"""<div class="caminho-title">🔵 Caminho 1 — Escala controlada (30 dias)</div>
1. Aumentar orçamento do melhor conjunto em 30% a cada semana<br>
2. Duplicar conjuntos vencedores com público lookalike 2% e 3%<br>
3. Criar campanha de reconhecimento para ampliar audiência<br>
4. Testar novos criativos para evitar fadiga (renovar a cada 3 semanas)<br>
5. Meta: dobrar volume de pedidos mantendo ROAS acima de 5x"""
        c2 = f"""<div class="caminho-title">🟣 Caminho 2 — Diversificação de canais (30-60 dias)</div>
1. Criar campanha de Instagram Stories com formato vertical nativo<br>
2. Testar Reels ads com vídeos curtos (15s) mostrando o processo de preparo<br>
3. Ativar campanha de fidelização para clientes que já compraram (lista de clientes)<br>
4. Expandir raio geográfico gradualmente (+1km por semana)<br>
5. Criar oferta sazonal (fim de semana, data comemorativa) para picos de conversão"""

    funil = ""
    if t["lp"] > 0:
        funil = f"""
    <div class="funil">
      <span class="funil-step">👁 {fmtN(t['impr'])} imp.</span>
      <span class="funil-arrow">→</span>
      <span class="funil-step">🖱 {fmtN(t['clicks'])} cliques ({t['ctr']:.1f}%)</span>
      <span class="funil-arrow">→</span>
      <span class="funil-step">📄 {fmtN(t['lp'])} LP</span>
      <span class="funil-arrow">→</span>
      <span class="funil-step">🛒 {fmtN(t['cart'])} carrinho</span>
      <span class="funil-arrow">→</span>
      <span class="funil-step">✅ {fmtN(t['pedidos'])} compras ({t['conv_lp']:.1f}%)</span>
    </div>"""

    html += f"""
  <div class="client-card {nivel}">
    <div class="client-header">
      <div>
        <div class="client-name">{d['nome']}</div>
        <div class="client-id">{d['id']}</div>
      </div>
      <span class="risk-badge {nivel}">{motivo}</span>
    </div>

    <div class="metrics-grid">
      <div class="metric"><div class="metric-label">💰 Investido</div><div class="metric-val">{fmt(t['gasto'])}</div></div>
      <div class="metric"><div class="metric-label">📦 Pedidos</div><div class="metric-val {"green" if t["pedidos"] > 20 else "red" if t["pedidos"] == 0 else ""}">{fmtN(t['pedidos'])}</div></div>
      <div class="metric"><div class="metric-label">🛒 Faturamento</div><div class="metric-val green">{fmt(t['fat']) if t["fat"] > 0 else "—"}</div></div>
      <div class="metric"><div class="metric-label">🚀 ROAS</div><div class="metric-val {roas_color}">{t['roas']:.2f}x if {t['roas'] > 0} else "—"</div></div>
      <div class="metric"><div class="metric-label">📉 CPR</div><div class="metric-val {cpr_color}">{fmt(t['cpr']) if t["cpr"] > 0 else "—"}</div></div>
      <div class="metric"><div class="metric-label">🎫 Ticket</div><div class="metric-val">{fmt(t['ticket']) if t["ticket"] > 0 else "—"}</div></div>
      <div class="metric"><div class="metric-label">👥 Alcance</div><div class="metric-val">{fmtN(t['reach'])}</div></div>
      <div class="metric"><div class="metric-label">🔁 Frequência</div><div class="metric-val {"red" if t["freq"] > 3 else ""}">{t['freq']:.2f}x</div></div>
    </div>
    {funil}
    <div class="evolucao">
      <div class="evo-card">
        <div class="evo-title">📅 Mês 1 (30-60 dias atrás)</div>
        <div class="evo-row"><span class="evo-key">Investido</span><span class="evo-val">{fmt(m1.get("gasto",0))}</span></div>
        <div class="evo-row"><span class="evo-key">Pedidos</span><span class="evo-val">{fmtN(m1.get("pedidos",0))}</span></div>
        <div class="evo-row"><span class="evo-key">ROAS</span><span class="evo-val">{m1.get("roas",0):.2f}x</span></div>
      </div>
      <div class="evo-card">
        <div class="evo-title">📅 Mês 2 (últimos 30 dias) {delta_html(m1.get("roas",0), m2.get("roas",0))}</div>
        <div class="evo-row"><span class="evo-key">Investido</span><span class="evo-val">{fmt(m2.get("gasto",0))}</span></div>
        <div class="evo-row"><span class="evo-key">Pedidos</span><span class="evo-val">{fmtN(m2.get("pedidos",0))}</span></div>
        <div class="evo-row"><span class="evo-key">ROAS</span><span class="evo-val">{m2.get("roas",0):.2f}x</span></div>
      </div>
    </div>

    <div class="diagnostico">💡 <strong>Diagnóstico do Gestor:</strong> {diag}</div>

    <div class="caminhos">
      <div class="caminho conservador">{c1}</div>
      <div class="caminho agressivo">{c2}</div>
    </div>
  </div>
"""

html += """
</div>
</body>
</html>"""

with open("auditoria_relatorio.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Relatório gerado: auditoria_relatorio.html")
print("Abra o arquivo no navegador ou imprima como PDF!")
