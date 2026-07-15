"""
Chama POST /db/seed no backend.

IN-4: por padrão NÃO força reseed se o banco já tiver dados.
Defina SEED_FORCE=1 no ambiente (ou passe --force) para drop+recreate.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _get(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode())


def _post(url: str) -> dict:
    req = urllib.request.Request(url, data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read().decode())


def run_seed():
    force = (
        "--force" in sys.argv
        or os.environ.get("SEED_FORCE", "").strip() in ("1", "true", "yes")
    )
    base = "http://127.0.0.1:8000"
    max_retries = 5

    for i in range(max_retries):
        try:
            # Status primeiro (não destrutivo)
            try:
                st = _get(f"{base}/db/seed/status")
                if st.get("seeded") and not force:
                    print(
                        f"Seed [SKIP]: banco já semeado "
                        f"({st.get('team_count')} times, liga={st.get('league_name')})."
                    )
                    print(
                        "  Dica: use SEED_FORCE=1 ou seed_runner.py --force "
                        "para recriar (apaga progresso)."
                    )
                    sys.exit(0)
            except Exception:
                # Endpoint antigo / schema ausente — tenta seed normal
                pass

            url = f"{base}/db/seed"
            if force:
                url += "?force=true"
                print("Seed [FORCE]: recriando banco (destrutivo)...")
            data = _post(url)
            if data.get("skipped"):
                print(f"Seed [SKIP]: {data.get('message', 'already seeded')}")
            else:
                print(f"Seed [OK]: {data.get('message', 'Success')}")
                if data.get("warning"):
                    print(f"  Aviso: {data['warning']}")
            sys.exit(0)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace") if e.fp else str(e)
            print(f"Tentativa {i + 1}/{max_retries} HTTP {e.code}: {body[:200]}")
            time.sleep(3)
        except Exception as e:
            print(
                f"Tentativa {i + 1}/{max_retries} falhou. "
                f"Aguardando servidor backend... ({e})"
            )
            time.sleep(3)

    print("ERRO: Falha ao conectar com o backend para semear o banco.")
    sys.exit(1)


if __name__ == "__main__":
    run_seed()
