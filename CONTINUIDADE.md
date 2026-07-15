# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-15 — Sprint G (carreira estável)  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Estado:** E+F+G · save Redis · seed seguro · Vitest · market AI · patch mid-split  

### Retomar
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md)  
2. [`docs/PLANO_MELHORIAS_SISTEMAS.md`](docs/PLANO_MELHORIAS_SISTEMAS.md)  
3. `run_game.bat`  

### Entregue nesta jornada
S1–S4 + Rift + Sprint E + Sprint F  
+ **Sprint G:** IN-1 save Redis · IN-3 Vitest · IN-4 seed seguro · MK-1 IA mercado · DR-5 patch mid-split  

### Como rodar
```bat
run_game.bat
```

Reseed destrutivo (opcional):
```bat
set SEED_FORCE=1
venv\Scripts\python seed_runner.py --force
```

### Stack
Backend FastAPI + SQLite + MockRedis · Frontend React/Vite/Tailwind · seed CBLOL 2026  

### Aviso seed
`POST /db/seed?force=true` **apaga o SQLite** e quebra saves antigos.  
Sem `force`, o seed **pula** se o banco já tiver a liga.  
