# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-14 (S1–S3 salvos; S4 em implementação)  
**Branch:** `main` (= `origin/main`)  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Estado:** **salvo** — working tree limpa no handoff; pode jogar com `run_game.bat`

### Leitura na retomada (ordem)
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md) — checklist + o que testar  
2. Este arquivo  
3. Notas de playtest  

### Entregue (commits recentes)
| Commit | Tema |
|--------|------|
| `93115c0` | S3 scrims, VOD, moral/chemistry |
| `84eaa38` | S2 playoffs BO3/BO5 fearless momentum |
| `0523079` | S1 janela FA + staff |
| `4128a18` / `9e291c5` | Draft scout + refinamentos |

**Testes:** 120+ passed · push GitHub OK  

### Próximo
- **S4** dono da org: sponsors, board, facility  
- Playtest manual + notas  

```bat
run_game.bat
```

---

## O que é o projeto

Simulador de gestão de esports LoL (estilo Football Manager), seed **CBLOL 2026**.  
Backend matemático (draft + match engine + calendário + burnout) + UI React.

### Stack
| Camada | Tech |
|--------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Alembic |
| Frontend | React 19, Vite 8, TS, Tailwind, Zustand |
| Dev local | SQLite (`lol_manager.db`) + MockRedis (`REDIS_URL=mock`) |
| Full | Postgres + Redis via `docker-compose.yml` |

### Como rodar
```bat
run_game.bat
```
Ou:
1. `PYTHONPATH=. venv\Scripts\python -m uvicorn src.main:app --port 8000`
2. `python seed_runner.py` (ou `POST /db/seed`)
3. `cd frontend && npm run dev` → http://localhost:5173  
API docs: http://127.0.0.1:8000/docs

### Seed oficial CBLOL 2026
Arquivo: `src/shared/cblol_2026_data.py` · **Seed apaga o SQLite e invalida saves**

### Fluxo de carreira
```
Menu → New Game → Hub
  → Avançar dia (treino / scrim / VOD / match day)
  → Draft (+ scout) → Live → standings / série playoff
  → Offseason: contratos, FA, staff → novo split
```

### Sistemas S1–S3 (resumo)
- **Mercado:** janela por fase; FA pool; staff hire/fire  
- **Playoffs:** BO3/BO5 multi-map; fearless; momentum gold  
- **Prática:** SCRIM + MEDIA VOD; moral/chemistry no Dashboard  

### Armadilhas
| Item | Detalhe |
|------|---------|
| Seed | drop_all — salva só com mesmo DB |
| MockRedis | estado some com restart uvicorn |
| Série | avance dia entre maps |

### Checklist retomada
1. Ler handoff  
2. `git pull` se outra máquina  
3. `run_game.bat`  
4. pytest se for codar  
