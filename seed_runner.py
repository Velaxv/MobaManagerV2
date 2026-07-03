import urllib.request
import json
import time
import sys

def run_seed():
    max_retries = 5
    for i in range(max_retries):
        try:
            req = urllib.request.Request('http://127.0.0.1:8000/db/seed', data=b'', method='POST')
            res = urllib.request.urlopen(req)
            data = json.loads(res.read().decode())
            print(f"Seed [OK]: {data.get('message', 'Success')}")
            sys.exit(0)
        except Exception as e:
            print(f"Tentativa {i+1}/{max_retries} falhou. Aguardando servidor backend... ({e})")
            time.sleep(3)
    
    print("ERRO: Falha ao conectar com o backend para semear o banco.")
    sys.exit(1)

if __name__ == "__main__":
    run_seed()
