#!/usr/bin/env python3
"""
Adiciona o usuário monitor-bm como admin nas 10 contas de anúncios
que estão retornando erro de permissão.

Usa a API do Meta com o token de Ads Manager (que tem acesso amplo).
Roda via GitHub Actions.
"""

import os
import sys
import requests

API_VERSION = "v19.0"
TOKEN = os.getenv("ADS_MANAGER_TOKEN", "")

# ID do sistema monitor-bm
MONITOR_BM_USER_ID = "122096456223324445"

# Contas que precisam de acesso + suas BMs
# Formato: (account_id_sem_act_, bm_id, nome)
CONTAS = [
    ("949529443295063", "949529443295063", "Restaurante da Samires 2"),    # BM mesmo ID?
    ("120205099089530533", "716401930498154", "Perché Pizzaria"),
    ("120205100165870533", "716401930498154", "Perché Pizzaria 02"),
    ("1109644918701738", "1109644918701738", "La Reina Restaurante"),       # BM mesmo ID?
    ("2657654867949206", "2657654867949206", "Capivara Urbana"),            # BM mesmo ID?
    ("1537505354710569", "1537505354710569", "Marcelo Burguer"),            # BM mesmo ID?
    ("850252170627582", "850252170627582", "Dot Everton"),                  # BM mesmo ID?
    ("158272603856054", "158272603856054", "CA - IZEE"),                    # BM mesmo ID?
    ("306426857334802", "306426857334802", "Estúdio Vitória Daronch"),      # BM mesmo ID?
]

# IDs corretos das contas de anúncios (act_XXXXXXX)
CONTAS_AD_ACCOUNTS = [
    # (account_id_completo, bm_id, nome)
    ("act_120205099089530533", "716401930498154", "Perché Pizzaria"),
    ("act_120205100165870533", "716401930498154", "Perché Pizzaria 02"),
]

def adicionar_permissao_conta(account_id: str, bm_id: str, nome: str, token: str):
    """Adiciona monitor-bm como admin na conta de anúncios via BM."""
    # Endpoint para adicionar usuário à conta de anúncios via BM
    url = f"https://graph.facebook.com/{API_VERSION}/{account_id}/userpermissions"

    payload = {
        "user": MONITOR_BM_USER_ID,
        "tasks": ["MANAGE", "ADVERTISE", "ANALYZE"],
        "access_token": token,
    }

    try:
        r = requests.post(url, data=payload, timeout=15)
        d = r.json()
        if d.get("success") or d.get("result") == "success":
            print(f"  ✅ {nome}: permissão adicionada com sucesso")
            return True
        elif "error" in d:
            err = d["error"]
            print(f"  ❌ {nome}: {err.get('message', '')} (code {err.get('code', '')})")
            return False
        else:
            print(f"  ⚠️  {nome}: resposta inesperada: {d}")
            return False
    except Exception as e:
        print(f"  ❌ {nome}: exceção: {e}")
        return False


def adicionar_via_bm(account_id: str, bm_id: str, nome: str, token: str):
    """Tenta adicionar via endpoint da BM."""
    # Endpoint alternativo: adicionar conta à BM e depois dar permissão
    url = f"https://graph.facebook.com/{API_VERSION}/{bm_id}/userpermissions"

    payload = {
        "user": MONITOR_BM_USER_ID,
        "role": "ADMIN",
        "access_token": token,
    }

    try:
        r = requests.post(url, data=payload, timeout=15)
        d = r.json()
        if d.get("success"):
            print(f"  ✅ {nome} (via BM): permissão adicionada")
            return True
        elif "error" in d:
            err = d["error"]
            print(f"  ❌ {nome} (via BM): {err.get('message', '')} (code {err.get('code', '')})")
            return False
        else:
            print(f"  ⚠️  {nome} (via BM): {d}")
            return False
    except Exception as e:
        print(f"  ❌ {nome}: exceção: {e}")
        return False


def verificar_contas_erradas(token: str):
    """Lista as contas que ainda retornam erro com o monitor-bm token."""
    print("\n📋 Verificando acesso atual (com token ADS_MANAGER_TOKEN)...")

    # As 10 contas problemáticas identificadas anteriormente
    contas_problematicas = [
        ("act_120205099089530533", "Perché Pizzaria"),
        ("act_120205100165870533", "Perché Pizzaria 02"),
        ("act_949529443295063", "Restaurante da Samires 2"),
        ("act_1109644918701738", "La Reina Restaurante"),
        ("act_2657654867949206", "Capivara Urbana"),
        ("act_1537505354710569", "Marcelo Burguer"),
        ("act_850252170627582", "Dot Everton"),
        ("act_158272603856054", "CA - IZEE"),
        ("act_306426857334802", "Estúdio Vitória Daronch"),
    ]

    sem_acesso = []
    for account_id, nome in contas_problematicas:
        url = (
            f"https://graph.facebook.com/{API_VERSION}/{account_id}"
            f"?fields=name,balance,spend_cap,amount_spent,account_status"
            f"&access_token={token}"
        )
        try:
            r = requests.get(url, timeout=15)
            d = r.json()
            if "error" in d:
                sem_acesso.append((account_id, nome))
                print(f"  ❌ {nome}: {d['error'].get('message','')[:80]}")
            else:
                print(f"  ✅ {nome}: acesso OK")
        except Exception as e:
            print(f"  ⚠️ {nome}: {e}")

    return sem_acesso


def main():
    if not TOKEN:
        print("❌ ADS_MANAGER_TOKEN não definido.")
        sys.exit(1)

    print("=== Adicionando monitor-bm às contas sem acesso ===")
    print(f"Token: {TOKEN[:20]}...")

    # Primeiro verifica quais ainda estão sem acesso
    sem_acesso = verificar_contas_erradas(TOKEN)

    if not sem_acesso:
        print("\n✅ Todas as contas já têm acesso! Nenhuma ação necessária.")
        return

    print(f"\n🔧 Tentando adicionar permissões para {len(sem_acesso)} conta(s)...\n")

    # Mapeamento conta → BM
    bm_map = {
        "act_120205099089530533": ("716401930498154", "Perché Pizzaria"),
        "act_120205100165870533": ("716401930498154", "Perché Pizzaria 02"),
        "act_949529443295063": ("949529443295063", "Restaurante da Samires 2"),
        "act_1109644918701738": ("1109644918701738", "La Reina Restaurante"),
        "act_2657654867949206": ("2657654867949206", "Capivara Urbana"),
        "act_1537505354710569": ("1537505354710569", "Marcelo Burguer"),
        "act_850252170627582": ("850252170627582", "Dot Everton"),
        "act_158272603856054": ("158272603856054", "CA - IZEE"),
        "act_306426857334802": ("306426857334802", "Estúdio Vitória Daronch"),
    }

    sucessos = 0
    for account_id, nome in sem_acesso:
        bm_id, _ = bm_map.get(account_id, ("", nome))
        print(f"→ {nome} ({account_id})")

        # Tenta via conta de anúncios diretamente
        ok = adicionar_permissao_conta(account_id, bm_id, nome, TOKEN)
        if not ok and bm_id:
            # Tenta via BM
            ok = adicionar_via_bm(account_id, bm_id, nome, TOKEN)

        if ok:
            sucessos += 1
        print()

    print(f"=== Resultado: {sucessos}/{len(sem_acesso)} conta(s) com permissão adicionada ===")


if __name__ == "__main__":
    main()
