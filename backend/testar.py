"""
Teste de integração — rode isso antes de ligar o monitor completo.
Verifica se a API do Meta e o WhatsApp estão funcionando corretamente.
"""

import json
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

def carregar_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def testar_meta(cfg):
    print("\n🔵 Testando API do Meta...")
    api_version = cfg["meta"]["api_version"]
    contas = cfg["meta"]["contas"]

    if not contas:
        print("  ❌ Nenhuma conta configurada em config.json")
        return

    for conta in contas:
        account_id = conta["account_id"]
        token = conta["access_token"]
        nome = conta["nome"]

        if "SEU_" in account_id or "SEU_" in token:
            print(f"  ⚠️  {nome}: configure o account_id e access_token em config.json")
            continue

        url = f"https://graph.facebook.com/{api_version}/{account_id}"
        params = {
            "fields": "name,balance,spend_cap,currency",
            "access_token": token,
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            data = r.json()
            if "error" in data:
                print(f"  ❌ {nome}: {data['error']['message']}")
            else:
                balance = int(data.get("balance", 0)) / 100
                print(f"  ✅ {nome}: saldo = R$ {balance:,.2f}")
        except Exception as e:
            print(f"  ❌ {nome}: erro de conexão — {e}")

def testar_whatsapp(cfg):
    print("\n🟢 Testando WhatsApp (Evolution API)...")
    wpp = cfg["whatsapp"]

    if "SUA_API_KEY" in wpp.get("api_key", ""):
        print("  ⚠️  Configure api_url, api_key e instancia em config.json")
        return

    numero_teste = wpp["numeros_destino"][0] if wpp["numeros_destino"] else None
    if not numero_teste:
        print("  ⚠️  Nenhum número configurado em numeros_destino")
        return

    url = f"{wpp['api_url']}/message/sendText/{wpp['instancia']}"
    headers = {"apikey": wpp["api_key"], "Content-Type": "application/json"}
    payload = {
        "number": numero_teste,
        "textMessage": {"text": "✅ *Teste do Monitor de BMs*\n\nIntegração funcionando corretamente!\n🤖 Sistema de alertas de saldo ativo."},
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        print(f"  ✅ Mensagem de teste enviada para {numero_teste}")
    except requests.exceptions.HTTPError as e:
        print(f"  ❌ Erro HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  ❌ Erro de conexão: {e}")

def main():
    print("=" * 50)
    print("   Monitor de BMs — Teste de Integração")
    print("=" * 50)

    try:
        cfg = carregar_config()
    except FileNotFoundError:
        print("❌ config.json não encontrado. Rode este script na pasta do projeto.")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Erro no config.json: {e}")
        return

    testar_meta(cfg)
    testar_whatsapp(cfg)

    print("\n" + "=" * 50)
    print("Se tudo mostrou ✅, rode: python monitor.py")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
