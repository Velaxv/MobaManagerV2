# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-14 — **SESSÃO SALVA**  
**Branch:** `main` (= `origin/main`)  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Último commit:** `651f1f9`  
**Estado:** limpo · push OK · pronto para playtest  

### Retomar
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md)  
2. `run_game.bat`  

### Entregue nesta jornada
S1 mercado/staff · S2 playoffs BO · S3 scrim/VOD/moral · S4 board/sponsors/facility  
+ draft scout · CI · 127 testes  

### Como rodar
```bat
run_game.bat
```

### Stack
Backend FastAPI + SQLite + MockRedis · Frontend React/Vite/Tailwind · seed CBLOL 2026  

### Aviso seed
`seed_runner.py` / `POST /db/seed` **apaga o SQLite** e quebra saves antigos.  
