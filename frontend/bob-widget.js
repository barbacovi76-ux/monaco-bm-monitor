(function() {
  const TOKEN_KEY = 'monaco_meta_token';
  const ANTHROPIC_KEY = 'monaco_anthropic_key';
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

    #bob-cfg { background:#0f1117; border-bottom:1px solid #2a2d3a; padding:10px 14px; display:flex; gap:8px; flex-shrink:0; }
    #bob-cfg input { background:#1e2130; border:1px solid #2a2d3a; border-radius:6px; padding:6px 10px; font-size:12px; color:#e8e8e8; outline:none; flex:1; }
    #bob-cfg button { padding:6px 12px; border-radius:6px; font-size:12px; background:#059669; color:#fff; border:none; cursor:pointer; white-space:nowrap; }

    #bob-msgs { flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }
    #bob-msgs::-webkit-scrollbar { width:4px; }
    #bob-msgs::-webkit-scrollbar-thumb { background:#2a2d3a; border-radius:2px; }

    .bm { display:flex; gap:8px; }
    .bm.user { flex-direction:row-reverse; }
    .bb { max-width:82%; padding:9px 13px; border-radius:12px; font-size:13px; line-height:1.6; word-break:break-word; }
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

    #bob-bottom { padding:10px 14px 14px; border-top:1px solid #2a2d3a; flex-shrink:0; }
    #bob-row { display:flex; gap:8px; margin-top:8px; }
    #bob-input { flex:1; background:#111318; border:1px solid #2a2d3a; border-radius:8px; padding:8px 12px; font-size:13px; color:#e8e8e8; outline:none; }
    #bob-input:focus { border-color:#059669; }
    #bob-send { width:38px; height:38px; border-radius:50%; border:none; cursor:pointer; font-size:16px; background:#059669; color:#fff; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    #bob-send:hover { background:#047857; }
  `;
  document.head.appendChild(style);

  const wrap = document.createElement('div');
  wrap.innerHTML = `
    <button id="bob-fab" title="Falar com BOB">🤖</button>
    <div id="bob-panel">
      <div id="bob-header">
        <div class="bh-left">
          <div class="bh-av">🤖</div>
          <div><div class="bh-name">BOB</div><div class="bh-sub">Assistente Monaco Agency</div></div>
        </div>
        <button id="bob-close">✕</button>
      </div>
      <div id="bob-cfg">
        <input type="password" id="bob-ak" placeholder="Anthropic API Key (sk-ant-...)">
        <button onclick="window._bobSalvar()">Salvar</button>
      </div>
      <div id="bob-msgs">
        <div class="bm bot"><div class="bav">🤖</div><div class="bb">Oi! Sou o BOB 👋<br>Pergunte sobre desempenho, saldos, encerramentos ou qualquer dado das campanhas!</div></div>
      </div>
      <div id="bob-chips">
        <span class="bchip" onclick="window._bobCmd('Desempenho geral últimos 7 dias')">📊 Geral 7d</span>
        <span class="bchip" onclick="window._bobCmd('Campanhas críticas com ROAS baixo')">🚨 Críticas</span>
        <span class="bchip" onclick="window._bobCmd('Saldo das contas')">💰 Saldos</span>
        <span class="bchip" onclick="window._bobCmd('Campanhas encerrando em breve')">⏰ Encerram</span>
        <span class="bchip" onclick="window._bobCmd('Top performers da semana')">🏆 Top BMs</span>
        <span class="bchip" onclick="window._bobCmd('Desempenho últimos 30 dias')">📅 30 dias</span>
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
    scroll();
  };
  document.getElementById('bob-close').onclick = () => {
    document.getElementById('bob-panel').classList.remove('open');
  };

  window._bobSalvar = () => {
    const ak = document.getElementById('bob-ak').value.trim();
    if (ak) localStorage.setItem(ANTHROPIC_KEY, ak);
    document.getElementById('bob-cfg').style.display = 'none';
  };

  if (localStorage.getItem(ANTHROPIC_KEY)) {
    document.getElementById('bob-cfg').style.display = 'none';
  }

  window._bobEnviar = () => {
    const txt = document.getElementById('bob-input').value.trim();
    if (!txt || processando) return;
    document.getElementById('bob-input').value = '';
    processar(txt);
  };

  window._bobCmd = (cmd) => processar(cmd);

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

  async function buscarDados(preset) {
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
            if (dias >= 0 && dias <= 14) itens.push({ bm: c.nome, camp: camp.name, dias });
          }
        }
      } catch(e) {}
    }
    return itens.sort((a,b) => a.dias - b.dias);
  }

  async function processar(texto) {
    if (processando) return;
    processando = true;
    addMsg('user', texto);
    const loading = addMsg('bot', '<div class="bdots"><span></span><span></span><span></span></div>');

    const cmd = texto.toLowerCase();
    let preset = 'last_7d';
    if (cmd.includes('30 dias') || cmd.includes('mês') || cmd.includes('mes')) preset = 'last_30d';
    else if (cmd.includes('14 dias')) preset = 'last_14d';
    else if (cmd.includes('ontem')) preset = 'yesterday';
    else if (cmd.includes('hoje')) preset = 'today';

    let dados = null, saldos = null, encerramentos = null;

    if (cmd.includes('saldo') || cmd.includes('recarga')) {
      saldos = await buscarSaldos();
    } else if (cmd.includes('encerr') || cmd.includes('prazo') || cmd.includes('venc')) {
      encerramentos = await buscarEncerramentos();
    } else {
      dados = await buscarDados(preset);
    }

    let ctx = `Você é o BOB, assistente de tráfego pago da Monaco Agency. Responda em português brasileiro, de forma direta e objetiva. Use no máximo 250 palavras. Use emojis com moderação.\n\nPergunta: "${texto}"\n\n`;

    if (dados) {
      const tg = dados.reduce((s,d) => s+d.gasto, 0);
      const tp = dados.reduce((s,d) => s+d.pedidos, 0);
      const tf = dados.reduce((s,d) => s+d.fat, 0);
      const rm = tg > 0 && tf > 0 ? tf/tg : 0;
      const cm = tp > 0 ? tg/tp : 0;
      ctx += `RESUMO GERAL (${preset}): investido=${fmt(tg)}, pedidos=${fmtN(tp)}, faturamento=${fmt(tf)}, ROAS=${rm.toFixed(2)}x, CPR=${fmt(cm)}\n\nDETALHE POR BM:\n`;
      dados.filter(d => d.gasto > 0).sort((a,b) => b.roas - a.roas).forEach(d => {
        const status = d.roas >= 3 ? '✅' : d.roas >= 1.5 ? '⚠️' : d.pedidos === 0 ? '🚨' : '🔴';
        ctx += `${status} ${d.nome}: ${fmt(d.gasto)} invest, ${d.pedidos} pedidos, ${fmt(d.fat)} fat, ROAS ${d.roas.toFixed(2)}x, CPR ${fmt(d.cpr)}\n`;
      });
      const sem = dados.filter(d => d.gasto === 0).map(d => d.nome);
      if (sem.length) ctx += `\nSem dados: ${sem.join(', ')}\n`;
    }

    if (saldos) {
      ctx += `\nSALDOS:\n`;
      saldos.forEach(s => ctx += `- ${s.nome}: ${fmt(s.saldo)}\n`);
    }

    if (encerramentos) {
      ctx += `\nENCERRAMENTOS (próx 14 dias):\n`;
      if (!encerramentos.length) ctx += 'Nenhum.\n';
      else encerramentos.forEach(e => ctx += `- ${e.bm} / ${e.camp}: ${e.dias === 0 ? 'HOJE' : 'em '+e.dias+' dia(s)'}\n`);
    }

    const ak = localStorage.getItem(ANTHROPIC_KEY) || '';
    if (!ak) {
      loading.remove();
      addMsg('bot', '⚠️ Configure a Anthropic API Key no campo acima para eu poder responder!');
      processando = false;
      document.getElementById('bob-cfg').style.display = 'flex';
      return;
    }

    try {
      const r = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'x-api-key': ak, 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 500, messages: [{ role: 'user', content: ctx }] })
      });
      if (!r.ok) throw new Error(r.status);
      const data = await r.json();
      const resposta = data.content[0].text.trim();
      loading.remove();
      addMsg('bot', resposta.replace(/\n/g, '<br>'));
    } catch(e) {
      loading.remove();
      addMsg('bot', '❌ Erro ao conectar com a IA. Verifique a API Key.');
    }

    processando = false;
  }

})();
