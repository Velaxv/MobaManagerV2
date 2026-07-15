# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-15 — Sprint E+F commitados  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Estado:** limpo após commit E+F · 140 testes · próximo = Sprint G  


### Retomar
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md)  
2. [`docs/PLANO_MELHORIAS_SISTEMAS.md`](docs/PLANO_MELHORIAS_SISTEMAS.md)  
3. `run_game.bat`  

### Entregue nesta jornada
S1–S4 + Rift + Sprint E  
+ **Sprint F:** TR-1 forma · TR-5 bench · MK-3 staff powers · OR-1 board semanal · DR-1 pool penalty  

### Como rodar
```bat
run_game.bat
```

### Stack
Backend FastAPI + SQLite + MockRedis · Frontend React/Vite/Tailwind · seed CBLOL 2026  

### Aviso seed
`seed_runner.py` / `POST /db/seed` **apaga o SQLite** e quebra saves antigos.  
