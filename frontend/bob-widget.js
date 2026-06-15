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

  // ── Injetar CSS ───────────────────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    #bob-fab { position:fixed; bottom:24px; right:24px; width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg,#059669,#3b82f6); border:none; cursor:pointer; font-size:28px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 20px rgba(5,150,105,.4); z-index:9998; transition:transform .2s; }
    #bob-fab:hover { transform:scale(1.1); }
    #bob-fab.ouvindo { animation:bob-pulse 1.5s infinite; }
    @keyframes bob-pulse { 0%{box-shadow:0 0 0 0 rgba(5,150,105,.7)} 70%{box-shadow:0 0 0 16px rgba(5,150,105,0)} 100%{box-shadow:0 0 0 0 rgba(5,150,105,0)} }
    #bob-fab.falando { animation:bob-pulse-blue 1.5s infinite; }
    @keyframes bob-pulse-blue { 0%{box-shadow:0 0 0 0 rgba(59,130,246,.7)} 70%{box-shadow:0 0 0 16px rgba(59,130,246,0)} 100%{box-shadow:0 0 0 0 rgba(59,130,246,0)} }

    #bob-panel { position:fixed; bottom:96px; right:24px; width:360px; max-height:580px; background:#161a24; border:1px solid #2a2d3a; border-radius:16px; box-shadow:0 8px 40px rgba(0,0,0,.5); z-index:9997; display:none; flex-direction:column; overflow:hidden; font-family:'Segoe UI',system-ui,sans-serif; }
    #bob-panel.open { display:flex; animation:bob-slide-in .2s ease; }
    @keyframes bob-slide-in { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }

    #bob-panel-header { background:#111318; padding:14px 16px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #2a2d3a; flex-shrink:0; }
    #bob-panel-header .bob-title { display:flex; align-items:center; gap:10px; }
    #bob-panel-header .bob-avatar-sm { width:36px; height:36px; border-radius:50%; background:linear-gradient(135deg,#059669,#3b82f6); display:flex; align-items:center; justify-content:center; font-size:18px; }
    #bob-panel-header .bob-name { font-size:14px; font-weight:600; color:#fff; }
    #bob-panel-header .bob-sub { font-size:11px; color:#6b7280; }
    #bob-close-btn { background:none; border:none; color:#6b7280; font-size:18px; cursor:pointer; padding:4px; }
    #bob-close-btn:hover { color:#fff; }

    #bob-config-bar { background:#0f1117; border-bottom:1px solid #2a2d3a; padding:10px 14px; display:flex; gap:8px; align-items:center; flex-shrink:0; }
    #bob-config-bar input { background:#1e2130; border:1px solid #2a2d3a; border-radius:6px; padding:5px 10px; font-size:12px; color:#e8e8e8; outline:none; flex:1; }
    #bob-config-bar button { padding:5px 10px; border-radius:6px; font-size:12px; background:#059669; color:#fff; border:none; cursor:pointer; white-space:nowrap; }
    #bob-config-ok { padding:8px 14px; font-size:12px; color:#34d399; display:none; }

    #bob-msgs { flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }
    #bob-msgs::-webkit-scrollbar { width:4px; }
    #bob-msgs::-webkit-scrollbar-track { background:#111318; }
    #bob-msgs::-webkit-scrollbar-thumb { background:#2a2d3a; border-radius:2px; }

    .bob-msg { display:flex; gap:8px; }
    .bob-msg.user { flex-direction:row-reverse; }
    .bob-bubble { max-width:82%; padding:9px 13px; border-radius:12px; font-size:13px; line-height:1.6; }
    .bob-msg.user .bob-bubble { background:#1d4ed8; color:#fff; border-bottom-right-radius:3px; }
    .bob-msg.bot .bob-bubble { background:#1e2130; border:1px solid #2a2d3a; color:#e8e8e8; border-bottom-left-radius:3px; }
    .bob-av { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; flex-shrink:0; }
    .bob-msg.bot .bob-av { background:linear-gradient(135deg,#059669,#3b82f6); }
    .bob-msg.user .bob-av { background:#1d4ed8; font-size:10px; color:#fff; font-weight:700; }

    .bob-dots { display:inline-flex; gap:3px; padding:4px 0; }
    .bob-dots span { width:5px; height:5px; border-radius:50%; background:#6b7280; animation:bob-bounce 1.2s infinite; }
    .bob-dots span:nth-child(2){animation-delay:.2s} .bob-dots span:nth-child(3){animation-delay:.4s}
    @keyframes bob-bounce { 0%,80%,100%{transform:scale(.8);opacity:.5} 40%{transform:scale(1);opacity:1} }

    #bob-bottom { padding:10px 14px; border-top:1px solid #2a2d3a; flex-shrink:0; }
    #bob-status-txt { font-size:11px; color:#6b7280; text-align:center; margin-bottom:8px; min-height:16px; }
    #bob-status-txt.ativo { color:#34d399; }
    #bob-status-txt.falando { color:#60a5fa; }
    #bob-status-txt.proc { color:#fbbf24; }

    #bob-controls { display:flex; gap:8px; align-items:center; }
    #bob-input { flex:1; background:#111318; border:1px solid #2a2d3a; border-radius:8px; padding:8px 12px; font-size:13px; color:#e8e8e8; outline:none; }
    #bob-input:focus { border-color:#059669; }
    #bob-mic-btn { width:40px; height:40px; border-radius:50%; border:none; cursor:pointer; font-size:18px; background:#1e2130; border:1px solid #2a2d3a; display:flex; align-items:center; justify-content:center; transition:all .2s; flex-shrink:0; }
    #bob-mic-btn:hover { border-color:#059669; }
    #bob-mic-btn.ouvindo { background:#059669; border-color:#059669; animation:bob-pulse 1.5s infinite; }
    #bob-send-btn { width:40px; height:40px; border-radius:50%; border:none; cursor:pointer; font-size:16px; background:#059669; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
    #bob-send-btn:hover { background:#047857; }

    #bob-cmds { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px; }
    .bob-cmd-chip { padding:4px 10px; border-radius:99px; font-size:11px; background:#111318; border:1px solid #2a2d3a; color:#9ca3af; cursor:pointer; transition:all .15s; white-space:nowrap; }
    .bob-cmd-chip:hover { border-color:#059669; color:#34d399; }
  `;
  document.head.appendChild(style);

  // ── Injetar HTML ──────────────────────────────────────────────────
  const wrapper = document.createElement('div');
  wrapper.innerHTML = `
    <button id="bob-fab" title="Falar com BOB">🤖</button>

    <div id="bob-panel">
      <div id="bob-panel-header">
        <div class="bob-title">
          <div class="bob-avatar-sm">🤖</div>
          <div>
            <div class="bob-name">BOB</div>
            <div class="bob-sub">Assistente Monaco Agency</div>
          </div>
        </div>
        <button id="bob-close-btn">✕</button>
      </div>

      <div id="bob-config-bar">
        <input type="password" id="bob-ak-input" placeholder="Anthropic API Key (sk-ant-...)">
        <button onclick="window._bobSalvarKey()">Salvar</button>
      </div>
      <div id="bob-config-ok">✅ Pronto! BOB está ativo.</div>

      <div id="bob-msgs">
        <div class="bob-msg bot">
          <div class="bob-av">🤖</div>
          <div class="bob-bubble">Oi! Sou o BOB 👋 Posso te ajudar com relatórios, saldos, encerramentos e análise das campanhas. Fale ou digite seu comando!</div>
        </div>
      </div>

      <div id="bob-bottom">
        <div id="bob-cmds">
          <span class="bob-cmd-chip" onclick="window._bobCmd('Desempenho geral 7 dias')">📊 Geral 7d</span>
          <span class="bob-cmd-chip" onclick="window._bobCmd('Campanhas críticas')">🚨 Críticas</span>
          <span class="bob-cmd-chip" onclick="window._bobCmd('Saldo das contas')">💰 Saldos</span>
          <span class="bob-cmd-chip" onclick="window._bobCmd('Encerramentos próximos')">⏰ Encerram</span>
          <span class="bob-cmd-chip" onclick="window._bobCmd('Top performers da semana')">🏆 Top</span>
          <span class="bob-cmd-chip" onclick="window._bobCmd('ROAS médio geral')">🚀 ROAS</span>
        </div>
        <div id="bob-status-txt">Digite ou clique no microfone</div>
        <div id="bob-controls">
          <input type="text" id="bob-input" placeholder="Digite seu comando..." onkeydown="if(event.key==='Enter')window._bobEnviarTexto()">
          <button id="bob-mic-btn" onclick="window._bobToggleMic()" title="Falar">🎤</button>
          <button id="bob-send-btn" onclick="window._bobEnviarTexto()" title="Enviar">➤</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(wrapper);

  // ── Estado ────────────────────────────────────────────────────────
  let ouvindo = false;
  let processando = false;
  let recognition = null;
  const synth = window.speechSynthesis;

  // ── Abrir/fechar panel ────────────────────────────────────────────
  document.getElementById('bob-fab').onclick = () => {
    const panel = document.getElementById('bob-panel');
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) scrollMsgs();
  };
  document.getElementById('bob-close-btn').onclick = () => {
    document.getElementById('bob-panel').classList.remove('open');
  };

  // ── Salvar key ────────────────────────────────────────────────────
  window._bobSalvarKey = () => {
    const ak = document.getElementById('bob-ak-input').value.trim();
    if (ak) { localStorage.setItem(ANTHROPIC_KEY, ak); }
    document.getElementById('bob-config-bar').style.display = 'none';
    document.getElementById('bob-config-ok').style.display = 'block';
    setTimeout(() => { document.getElementById('bob-config-ok').style.display = 'none'; }, 3000);
  };

  // Verificar se já tem key
  if (localStorage.getItem(ANTHROPIC_KEY)) {
    document.getElementById('bob-config-bar').style.display = 'none';
  }

  // ── Microfone ─────────────────────────────────────────────────────
  window._bobToggleMic = () => {
    if (ouvindo) { pararMic(); return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setStatus('Use Chrome para voz', ''); return; }
    recognition = new SR();
    recognition.lang = 'pt-BR';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onstart = () => {
      ouvindo = true;
      setStatus('Ouvindo...', 'ativo');
      document.getElementById('bob-mic-btn').classList.add('ouvindo');
      document.getElementById('bob-fab').classList.add('ouvindo');
      document.getElementById('bob-input').placeholder = 'Ouvindo...';
    };
    recognition.onresult = (e) => {
      let final = '', interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      document.getElementById('bob-input').value = final || interim;
      if (final) { pararMic(); processar(final.trim()); }
    };
    recognition.onerror = () => pararMic();
    recognition.onend = () => { if (ouvindo) pararMic(); };
    recognition.start();
  };

  function pararMic() {
    ouvindo = false;
    if (recognition) try { recognition.stop(); } catch(e) {}
    document.getElementById('bob-mic-btn').classList.remove('ouvindo');
    document.getElementById('bob-fab').classList.remove('ouvindo');
    document.getElementById('bob-input').placeholder = 'Digite seu comando...';
    if (!processando) setStatus('Digite ou clique no microfone', '');
  }

  // ── Enviar texto ──────────────────────────────────────────────────
  window._bobEnviarTexto = () => {
    const txt = document.getElementById('bob-input').value.trim();
    if (!txt || processando) return;
    document.getElementById('bob-input').value = '';
    processar(txt);
  };

  window._bobCmd = (cmd) => {
    document.getElementById('bob-input').value = cmd;
    processar(cmd);
  };

  // ── Status ────────────────────────────────────────────────────────
  function setStatus(txt, cls) {
    const el = document.getElementById('bob-status-txt');
    el.textContent = txt;
    el.className = cls ? 'ativo' === cls ? 'ativo' : cls : '';
    el.id = 'bob-status-txt';
  }

  // ── Mensagens UI ──────────────────────────────────────────────────
  function addMsg(tipo, html) {
    const msgs = document.getElementById('bob-msgs');
    const div = document.createElement('div');
    div.className = 'bob-msg ' + tipo;
    const av = tipo === 'bot' ? '🤖' : 'VC';
    div.innerHTML = `<div class="bob-av">${av}</div><div class="bob-bubble">${html}</div>`;
    msgs.appendChild(div);
    scrollMsgs();
    return div;
  }

  function scrollMsgs() {
    const el = document.getElementById('bob-msgs');
    setTimeout(() => { el.scrollTop = el.scrollHeight; }, 50);
  }

  function addLoading() {
    return addMsg('bot', '<div class="bob-dots"><span></span><span></span><span></span></div>');
  }

  // ── Buscar dados ──────────────────────────────────────────────────
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
        res.push({ nome: c.nome, saldo: bal, sc });
      } catch(e) { res.push({ nome: c.nome, saldo: 0, sc: 0 }); }
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

  // ── Processar com Claude ──────────────────────────────────────────
  async function processar(texto) {
    if (!texto || processando) return;
    processando = true;
    setStatus('Buscando dados...', 'proc');
    addMsg('user', texto);
    const loadingEl = addLoading();

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

    // Contexto para Claude
    let ctx = `Você é o BOB, assistente de tráfego pago da Monaco Agency. Responda em português, de forma direta e objetiva. Use no máximo 200 palavras. Use emojis com moderação.\n\nComando: "${texto}"\n\n`;

    if (dados) {
      const tg = dados.reduce((s,d) => s+d.gasto, 0);
      const tp = dados.reduce((s,d) => s+d.pedidos, 0);
      const tf = dados.reduce((s,d) => s+d.fat, 0);
      const rm = tg > 0 && tf > 0 ? tf/tg : 0;
      ctx += `DADOS (${preset}): investido=${fmt(tg)}, pedidos=${fmtN(tp)}, faturamento=${fmt(tf)}, ROAS=${rm.toFixed(2)}x\n`;
      ctx += `POR BM:\n`;
      dados.filter(d => d.gasto > 0).forEach(d => {
        ctx += `- ${d.nome}: ${fmt(d.gasto)} investido, ${d.pedidos} pedidos, ${fmt(d.fat)} fat, ROAS ${d.roas.toFixed(2)}x\n`;
      });
      const semDados = dados.filter(d => d.gasto === 0).map(d => d.nome);
      if (semDados.length) ctx += `Sem dados: ${semDados.join(', ')}\n`;
    }

    if (saldos) {
      ctx += `SALDOS:\n`;
      saldos.forEach(s => { ctx += `- ${s.nome}: ${fmt(s.saldo)}\n`; });
    }

    if (encerramentos) {
      ctx += `ENCERRAMENTOS (próx 14 dias):\n`;
      if (!encerramentos.length) ctx += 'Nenhum\n';
      else encerramentos.forEach(e => { ctx += `- ${e.bm} / ${e.camp}: ${e.dias === 0 ? 'hoje' : 'em '+e.dias+' dias'}\n`; });
    }

    const ak = localStorage.getItem(ANTHROPIC_KEY) || '';
    if (!ak) {
      loadingEl.remove();
      addMsg('bot', '⚠️ Configure a Anthropic API Key para eu poder responder!');
      processando = false;
      setStatus('Configure a API Key', '');
      return;
    }

    try {
      setStatus('BOB pensando...', 'proc');
      const r = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'x-api-key': ak, 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 400, messages: [{ role: 'user', content: ctx }] })
      });
      if (!r.ok) throw new Error(r.status);
      const data = await r.json();
      const resposta = data.content[0].text.trim();
      loadingEl.remove();
      addMsg('bot', resposta.replace(/\n/g, '<br>'));
      falar(resposta);
    } catch(e) {
      loadingEl.remove();
      addMsg('bot', '❌ Erro ao conectar com a IA. Verifique a API Key.');
      setStatus('Erro na API', '');
    }

    processando = false;
    document.getElementById('bob-input').value = '';
  }

  // ── Text-to-Speech ────────────────────────────────────────────────
  function falar(texto) {
    if (!synth) return;
    synth.cancel();
    const limpo = texto.replace(/[🤖📊💰🚨⚠️✅❌🏆📅🛒🔴⏰💪🔥]/g, '').replace(/\*\*/g,'').replace(/\*/g,'').replace(/<br>/g,'. ').trim();
    const u = new SpeechSynthesisUtterance(limpo);
    u.lang = 'pt-BR'; u.rate = 1.05;
    const vozes = synth.getVoices();
    const voz = vozes.find(v => v.lang === 'pt-BR') || vozes.find(v => v.lang.startsWith('pt'));
    if (voz) u.voice = voz;
    u.onstart = () => { setStatus('BOB falando...', 'falando'); document.getElementById('bob-fab').classList.add('falando'); };
    u.onend = () => { setStatus('Digite ou clique no microfone', ''); document.getElementById('bob-fab').classList.remove('falando'); };
    synth.speak(u);
  }

  if (synth) { synth.onvoiceschanged = () => synth.getVoices(); synth.getVoices(); }

})();
