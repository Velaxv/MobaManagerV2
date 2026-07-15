# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-15 — Checkpoint salvo (commit + push)  
**Branch:** `main` (sync com origin)  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Commit:** `06e0439` — feat: fatigue recovery, flex draft, new career, and War Room UI  

### Retomar
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md)  
2. `run_game.bat`  

### Entregue e no remote
- S1–S4 + E + F + G + H + ME-7  
- **FADIGA** — recovery diário com nuance; banco recupera em match day  
- **DRAFT-FLEX** — pick = campeão + qualquer role livre (IA + jogador)  
- **Nova carreira** — `POST /career/new` reseed + limpa Redis  
- **War Room UI** (3 passadas) — glass tech-noir, sede, draft blueprint, radar, pós-jogo, heatmap real  

### Não feito (de propósito)
- Coach mid/late · Tutorial · Som / i18n · Desafiante  

### Como rodar
```bat
run_game.bat
```

### Stack
Backend FastAPI + SQLite + MockRedis · Frontend React/Vite/Tailwind · seed CBLOL 2026  
