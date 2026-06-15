(function() {
  const TOKEN_KEY = 'monaco_meta_token';
  const API_VERSION = 'v19.0';

  const CONTAS = [
    { nome: 'CA - ROSA SUL NOVA', id: 'act_2523170184768797' },
    { nome: 'Dia de Pizza - Dourados', id: 'act_723575425785405' },
    { nome: 'IH CAMPO GRANDE MS', id: 'act_1131240581799095' },
    { nome: 'Mollinari Pizzaria', id: 'act_459274303920372' },
    { nome: 'MrGabs', id: 'act_728296823243425' },
    { nome: 'IH DOURADOS', id: 'act_831936562721815' },
    { nome: 'Villa Grano Pizzaria', id: 'act_909424425271250' },
    { nome: 'Brados Pizzaria', id: 'act_972023765779926' },
    { nome: 'Berlim Pizzaria', id: 'act_836447545843342' },
    { nome: 'A FAVORITA', id: 'act_969681458906352' },
    { nome: 'CA - BRAVA PIZZA', id: 'act_4279801688941861' },
    { nome: 'Pavao Lanchonete', id: 'act_1759603645448352' },
    { nome: 'Fornalha Pizzaria', id: 'act_1618084519451450' },
  ];

  const fmt = v => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const fmtN = v => Number(v).toLocaleString('pt-BR');

  // ── CSS ───────────────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #bob-fab { position:fixed; bottom:24px; right:24px; width:56px; height:56px; border-radius:50%; background:linear-gradient(135deg,#059669,#3b82f6); border:none; cursor:pointer; font-size:26px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 20px rgba(5,150,105,.4); z-index:9998; transition:transform .2s; }
    #bob-fab:hover { transform:scale(1.08); }

    #bob-panel { position:fixed; bottom:90px; right:24px; width:360px; max-height:560px; background:#161a24; border:1px solid #2a2d3a; border-radius:16px; box-shadow:0 8px 40px rgba(0,0,0,.5); z-index:9997; display:none; flex-direction:column; overflow:hidden; font-family:'Segoe UI',system-ui,sans-serif; }
    #bob-panel.open { display:flex; animation:bob-in .2s ease; }
    @keyframes bob-in { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }

    #bob-header { background:#111318; padding:12px 16px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #2a2d3a; flex-shrink:0; }
    #bob-header .bh-left { display:flex; align-items:center; gap:10px; }
    #bob-header .bh-av { width:34px; height:34px; border-radius:50%; background:linear-gradient(135deg,#059669,#3b82f6); display:flex; align-items:center; justify-content:center; font-size:17px; }
    #bob-header .bh-name { font-size:13px; font-weight:600; color:#fff; }
    #bob-header .bh-sub { font-size:11px; color:#6b7280; }
    #bob-close { background:none; border:none; color:#6b7280; font-size:18px; cursor:pointer; }
    #bob-close:hover { color:#fff; }

    #bob-msgs { flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }
    #bob-msgs::-webkit-scrollbar { width:4px; }
    #bob-msgs::-webkit-scrollbar-thumb { background:#2a2d3a; border-radius:2px; }

    .bm { display:flex; gap:8px; }
    .bm.user { flex-direction:row-reverse; }
    .bb { max-width:82%; padding:9px 13px; border-radius:12px; font-size:13px; line-height:1.7; word-break:break-word; }
    .bm.user .bb { background:#1d4ed8; color:#fff; border-bottom-right-radius:3px; }
    .bm.bot .bb { background:#1e2130; border:1px solid #2a2d3a; color:#e8e8e8; border-bottom-left-radius:3px; }
    .bav { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; margin-top:2px; }
    .bm.bot .bav { background:linear-gradient(135deg,#059669,#3b82f6); }
    .bm.user .bav { background:#1d4ed8; font-size:10px; color:#fff; font-weight:700; }

    .bdots { display:inline-flex; gap:3px; }
    .bdots span { width:5px; height:5px; border-radius:50%; background:#6b7280; animation:bd 1.2s infinite; }
    .bdots span:nth-child(2){animation-delay:.2s} .bdots span:nth-child(3){animation-delay:.4s}
    @keyframes bd { 0%,80%,100%{transform:scale(.8);opacity:.5} 40%{transform:scale(1);opacity:1} }

    #bob-chips { padding:8px 14px 0; display:flex; flex-wrap:wrap; gap:5px; flex-shrink:0; }
    .bchip { padding:4px 10px; border-radius:99px; font-size:11px; background:#111318; border:1px solid #2a2d3a; color:#9ca3af; cursor:pointer; transition:all .15s; white-space:nowrap; }
    .bchip:hover { border-color:#059669; color:#34d399; }

    #bob-bottom { padding:10px 14px 14px; border-top:1px solid #2a2d3a; flex-shrink:0; margin-top:8px; }
    #bob-row { display:flex; gap:8px; }
    #bob-input { flex:1; background:#111318; border:1px solid #2a2d3a; border-radius:8px; padding:8px 12px; font-size:13px; color:#e8e8e8; outline:none; }
    #bob-input:focus { border-color:#059669; }
    #bob-send { width:38px; height:38px; border-radius:50%; border:none; cursor:pointer; font-size:16px; background:#059669; color:#fff; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    #bob-send:hover { background:#047857; }
    #bob-no-token { padding:10px 14px; font-size:12px; color:#f87171; background:rgba(248,113,113,.08); border-bottom:1px solid #2a2d3a; text-align:center; display:none; flex-shrink:0; }
  `;
  document.head.appendChild(style);

  // ── HTML ──────────────────────────────────────────────────────────
  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <button id="bob-fab" title="BOB — Assistente">🤖</button>
    <div id="bob-panel">
      <div id="bob-header">
        <div class="bh-left">
          <div class="bh-av">🤖</div>
          <div><div class="bh-name">BOB</div><div class="bh-sub">Assistente Monaco Agency</div></div>
        </div>
        <button id="bob-close">✕</button>
      </div>
      <div id="bob-no-token">⚠️ Salve o token do Meta primeiro para eu buscar os dados!</div>
      <div id="bob-msgs">
        <div class="bm bot"><div class="bav">🤖</div><div class="bb">Oi! Sou o BOB 👋<br>Pergunte sobre desempenho, saldos, encerramentos ou qualquer dado das campanhas!</div></div>
      </div>
      <div id="bob-chips">
        <span class="bchip" onclick="window._bobCmd('geral7d')">📊 Geral 7d</span>
        <span class="bchip" onclick="window._bobCmd('criticas')">🚨 Críticas</span>
        <span class="bchip" onclick="window._bobCmd('saldos')">💰 Saldos</span>
        <span class="bchip" onclick="window._bobCmd('encerramentos')">⏰ Encerram</span>
        <span class="bchip" onclick="window._bobCmd('top')">🏆 Top BMs</span>
        <span class="bchip" onclick="window._bobCmd('geral30d')">📅 30 dias</span>
      </div>
      <div id="bob-bottom">
        <div id="bob-row">
          <input type="text" id="bob-input" placeholder="Digite sua pergunta..." onkeydown="if(event.key==='Enter')window._bobEnviar()">
          <button id="bob-send" onclick="window._bobEnviar()">➤</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(wrap);

  let processando = false;

  document.getElementById('bob-fab').onclick = () => {
    document.getElementById('bob-panel').classList.toggle('open');
    if (!localStorage.getItem(TOKEN_KEY)) {
      document.getElementById('bob-no-token').style.display = 'block';
    }
    scroll();
  };
  document.getElementById('bob-close').onclick = () => {
    document.getElementById('bob-panel').classList.remove('open');
  };

  window._bobEnviar = () => {
    const txt = document.getElementById('bob-input').value.trim();
    if (!txt || processando) return;
    document.getElementById('bob-input').value = '';
    interpretarTexto(txt);
  };

  window._bobCmd = (cmd) => processar(cmd);

  function interpretarTexto(txt) {
    const t = txt.toLowerCase();
    if (t.includes('saldo') || t.includes('recarga')) return processar('saldos');
    if (t.includes('encerr') || t.includes('prazo') || t.includes('venc')) return processar('encerramentos');
    if (t.includes('critica') || t.includes('crítica') || t.includes('roas baixo') || t.includes('sem result')) return processar('criticas');
    if (t.includes('top') || t.includes('melhor') || t.includes('performer')) return processar('top');
    if (t.includes('30 dia') || t.includes('mês') || t.includes('mes')) return processar('geral30d');
    if (t.includes('14 dia')) return processar('geral14d');
    if (t.includes('ontem')) return processar('geralyesterday');
    if (t.includes('hoje')) return processar('geraltoday');
    return processar('geral7d');
  }

  function addMsg(tipo, html) {
    const el = document.createElement('div');
    el.className = 'bm ' + tipo;
    el.innerHTML = `<div class="bav">${tipo === 'bot' ? '🤖' : 'VC'}</div><div class="bb">${html}</div>`;
    document.getElementById('bob-msgs').appendChild(el);
    scroll();
    return el;
  }

  function scroll() {
    const el = document.getElementById('bob-msgs');
    setTimeout(() => { el.scrollTop = el.scrollHeight; }, 60);
  }

  // ── Buscar dados ──────────────────────────────────────────────────
  async function buscarInsights(preset) {
    const token = localStorage.getItem(TOKEN_KEY) || '';
    if (!token) return null;
    const res = [];
    for (const c of CONTAS) {
      try {
        const r = await fetch(`https://graph.facebook.com/${API_VERSION}/${c.id}/insights?fields=spend,actions,action_values&date_preset=${preset}&access_token=${token}`);
        const d = await r.json();
        const ins = d.data && d.data[0];
        const gasto = parseFloat(ins?.spend || 0);
        const actions = ins?.actions || [];
        const av = ins?.action_values || [];
        const pedidos = parseInt(actions.find(a => a.action_type === 'purchase')?.value || 0);
        const fat = parseFloat(av.find(a => a.action_type === 'purchase')?.value || 0);
        const roas = gasto > 0 && fat > 0 ? fat / gasto : 0;
        const cpr = pedidos > 0 ? gasto / pedidos : 0;
        res.push({ nome: c.nome, gasto, pedidos, fat, roas, cpr });
      } catch(e) { res.push({ nome: c.nome, gasto:0, pedidos:0, fat:0, roas:0, cpr:0 }); }
    }
    return res;
  }

  async function buscarSaldos() {
    const token = localStorage.getItem(TOKEN_KEY) || '';
    if (!token) return null;
    const res = [];
    for (const c of CONTAS) {
      try {
        const r = await fetch(`https://graph.facebook.com/${API_VERSION}/${c.id}?fields=name,balance,spend_cap,amount_spent&access_token=${token}`);
        const d = await r.json();
        const sc = parseInt(d.spend_cap || 0) / 100;
        const amt = parseInt(d.amount_spent || 0) / 100;
        const bal = sc > 0 ? sc - amt : parseInt(d.balance || 0) / 100;
        res.push({ nome: c.nome, saldo: bal });
      } catch(e) { res.push({ nome: c.nome, saldo: 0 }); }
    }
    return res;
  }

  async function buscarEncerramentos() {
    const token = localStorage.getItem(TOKEN_KEY) || '';
    if (!token) return null;
    const hoje = new Date(); hoje.setHours(0,0,0,0);
    const itens = [];
    for (const c of CONTAS) {
      try {
        const r = await fetch(`https://graph.facebook.com/${API_VERSION}/${c.id}/campaigns?fields=name,effective_status,stop_time&limit=50&access_token=${token}`);
        const d = await r.json();
        for (const camp of (d.data || [])) {
          if (camp.stop_time) {
            const dt = new Date(camp.stop_time); dt.setHours(0,0,0,0);
            const dias = Math.round((dt - hoje) / 86400000);
            if (dias >= 0 && dias <= 14) itens.push({ bm: c.nome, camp: camp.name, dias, status: camp.effective_status });
          }
        }
      } catch(e) {}
    }
    return itens.sort((a,b) => a.dias - b.dias);
  }

  // ── Montar respostas ──────────────────────────────────────────────
  function montarRelatorio(dados, periodo) {
    const tg = dados.reduce((s,d) => s+d.gasto, 0);
    const tp = dados.reduce((s,d) => s+d.pedidos, 0);
    const tf = dados.reduce((s,d) => s+d.fat, 0);
    const rm = tg > 0 && tf > 0 ? tf/tg : 0;
    const cm = tp > 0 ? tg/tp : 0;

    let html = `📊 <strong>Relatório — ${periodo}</strong><br><br>`;
    html += `💰 Investido: <strong>${fmt(tg)}</strong><br>`;
    html += `📦 Pedidos: <strong>${fmtN(tp)}</strong><br>`;
    html += `🛒 Faturamento: <strong>${fmt(tf)}</strong><br>`;
    html += `🚀 ROAS médio: <strong>${rm.toFixed(2)}x</strong><br>`;
    html += `📉 CPR médio: <strong>${cm > 0 ? fmt(cm) : '—'}</strong><br><br>`;

    const comDados = dados.filter(d => d.gasto > 0).sort((a,b) => b.roas - a.roas);
    if (comDados.length) {
      html += `<strong>Por BM:</strong><br>`;
      comDados.forEach(d => {
        const ic = d.roas >= 3 ? '✅' : d.roas >= 1.5 ? '⚠️' : d.pedidos === 0 ? '🚨' : '🔴';
        html += `${ic} ${d.nome}<br>&nbsp;&nbsp;${fmt(d.gasto)} | ${d.pedidos} pedidos | ROAS ${d.roas.toFixed(2)}x<br>`;
      });
    }
    const sem = dados.filter(d => d.gasto === 0);
    if (sem.length) {
      html += `<br>⚫ Sem dados: ${sem.map(d => d.nome).join(', ')}`;
    }
    return html;
  }

  function montarCriticas(dados) {
    const criticas = dados.filter(d => d.gasto > 0 && (d.pedidos === 0 || d.roas < 1.5));
    const atencao = dados.filter(d => d.gasto > 0 && d.roas >= 1.5 && d.roas < 3);

    let html = `🚨 <strong>Análise de campanhas críticas</strong><br><br>`;

    if (criticas.length) {
      html += `🔴 <strong>Crítico (${criticas.length})</strong><br>`;
      criticas.forEach(d => {
        const motivo = d.pedidos === 0 ? 'Gasto sem retorno' : `ROAS crítico (${d.roas.toFixed(2)}x)`;
        html += `• ${d.nome}<br>&nbsp;&nbsp;${motivo} | Investido: ${fmt(d.gasto)}<br>`;
      });
      html += '<br>';
    }

    if (atencao.length) {
      html += `⚠️ <strong>Atenção (${atencao.length})</strong><br>`;
      atencao.forEach(d => {
        html += `• ${d.nome}<br>&nbsp;&nbsp;ROAS ${d.roas.toFixed(2)}x | CPR ${fmt(d.cpr)}<br>`;
      });
      html += '<br>';
    }

    if (!criticas.length && !atencao.length) {
      html += `✅ Nenhuma campanha crítica no momento! Tudo saudável.`;
    } else {
      html += `Total: ${criticas.length} crítica(s) | ${atencao.length} atenção`;
    }
    return html;
  }

  function montarTop(dados) {
    const top = dados.filter(d => d.gasto > 0 && d.roas > 0).sort((a,b) => b.roas - a.roas).slice(0, 5);
    let html = `🏆 <strong>Top Performers (últimos 7 dias)</strong><br><br>`;
    if (!top.length) return html + 'Sem dados disponíveis.';
    top.forEach((d, i) => {
      const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '⭐';
      html += `${medal} <strong>${d.nome}</strong><br>&nbsp;&nbsp;ROAS ${d.roas.toFixed(2)}x | ${d.pedidos} pedidos | ${fmt(d.fat)} fat<br>`;
    });
    return html;
  }

  // ── Processar comando ─────────────────────────────────────────────
  async function processar(cmd) {
    if (processando) return;

    const token = localStorage.getItem(TOKEN_KEY) || '';
    if (!token) {
      addMsg('bot', '⚠️ Salve o token do Meta primeiro na barra de configuração da dashboard!');
      return;
    }

    processando = true;

    // Label para o usuário
    const labels = {
      geral7d: 'Desempenho geral — 7 dias',
      geral14d: 'Desempenho geral — 14 dias',
      geral30d: 'Desempenho geral — 30 dias',
      geraltoday: 'Desempenho de hoje',
      geralyesterday: 'Desempenho de ontem',
      criticas: 'Campanhas críticas',
      top: 'Top performers',
      saldos: 'Saldo das contas',
      encerramentos: 'Encerramentos próximos',
    };
    addMsg('user', labels[cmd] || cmd);
    const loading = addMsg('bot', '<div class="bdots"><span></span><span></span><span></span></div>');

    try {
      let resposta = '';

      if (cmd === 'saldos') {
        const saldos = await buscarSaldos();
        if (!saldos) throw new Error('sem token');
        let html = `💰 <strong>Saldo das contas</strong><br><br>`;
        const ordenados = saldos.sort((a,b) => a.saldo - b.saldo);
        ordenados.forEach(s => {
          const ic = s.saldo <= 50 ? '🔴' : s.saldo <= 100 ? '⚠️' : '✅';
          html += `${ic} ${s.nome}: <strong>${fmt(s.saldo)}</strong><br>`;
        });
        resposta = html;

      } else if (cmd === 'encerramentos') {
        const itens = await buscarEncerramentos();
        if (!itens) throw new Error('sem token');
        let html = `⏰ <strong>Encerramentos próximos (14 dias)</strong><br><br>`;
        if (!itens.length) {
          html += '✅ Nenhuma campanha encerrando nos próximos 14 dias!';
        } else {
          itens.forEach(i => {
            const ic = i.dias === 0 ? '🔴' : i.dias <= 2 ? '🔴' : i.dias <= 7 ? '⚠️' : '📅';
            const label = i.dias === 0 ? 'HOJE' : i.dias === 1 ? 'amanhã' : `em ${i.dias} dias`;
            html += `${ic} <strong>${i.bm}</strong><br>&nbsp;&nbsp;${i.camp} — encerra ${label}<br>`;
          });
        }
        resposta = html;

      } else {
        // Insights
        const presetMap = { geral7d:'last_7d', geral14d:'last_14d', geral30d:'last_30d', geraltoday:'today', geralyesterday:'yesterday', criticas:'last_7d', top:'last_7d' };
        const periodoMap = { geral7d:'7 dias', geral14d:'14 dias', geral30d:'30 dias', geraltoday:'Hoje', geralyesterday:'Ontem', criticas:'7 dias', top:'7 dias' };
        const preset = presetMap[cmd] || 'last_7d';
        const dados = await buscarInsights(preset);
        if (!dados) throw new Error('sem token');

        if (cmd === 'criticas') resposta = montarCriticas(dados);
        else if (cmd === 'top') resposta = montarTop(dados);
        else resposta = montarRelatorio(dados, periodoMap[cmd] || '7 dias');
      }

      loading.remove();
      addMsg('bot', resposta);

    } catch(e) {
      loading.remove();
      addMsg('bot', '❌ Erro ao buscar dados. Verifique o token do Meta.');
    }

    processando = false;
  }

})();
