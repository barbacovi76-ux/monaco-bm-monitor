#!/usr/bin/env python3
"""Teste pontual — envia mensagem de exemplo no grupo de operações."""
import os, requests

WPP_URL       = "https://evolution-api-production-2227.up.railway.app"
WPP_KEY       = "monaco123"
WPP_INSTANCIA = "teste"
GRUPO_OPS     = "120363403884174816@g.us"

msg = (
    "🤖 BOB Saldos — Monaco Agency\n"
    "05/11/2026 17:41\n\n"
    "🔴 CRÍTICO (1)\n"
    "  · [TESTE] Conta Exemplo → R$ 12,50\n\n"
    "🟡 BAIXO (1)\n"
    "  · [TESTE] Outra Conta → R$ 87,00\n\n"
    "✅ Integração GitHub Actions → WhatsApp funcionando!\n"
    "Acesse: https://barbacovi76-ux.github.io/monaco-bm-monitor/saldos_dash.html"
)

r = requests.post(
    f"{WPP_URL}/message/sendText/{WPP_INSTANCIA}",
    headers={"apikey": WPP_KEY, "Content-Type": "application/json"},
    json={"number": GRUPO_OPS, "textMessage": {"text": msg}},
    timeout=15
)
print(r.status_code, r.text[:300])
