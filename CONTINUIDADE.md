# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-15 — War Room passada 3 (heatmap real + sede + microanimações)  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Estado:** Heatmap pós-jogo de eventos reais; facility LED+scanlines; panel-enter/scan-bar; 28 FE tests  

### Retomar
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md)  
2. [`docs/PLANO_FADIGA_E_DRAFT_FLEX.md`](docs/PLANO_FADIGA_E_DRAFT_FLEX.md)  
3. `run_game.bat`  

### Entregue
S1–S4 + E + F + G + H + ME-7  
+ **Sprint FADIGA:** recovery diário com nuance (forma/moral/board/staff/intensidade); banco recupera em match day  
+ **Sprint DRAFT-FLEX:** IA escolhe (champ, role) aberta; FE permite pick em qualquer role livre  

### Não feito (de propósito)
- Coach mid/late  
- Tutorial  
- Som / i18n / Desafiante  

### Como rodar
```bat
run_game.bat
```

### Stack
Backend FastAPI + SQLite + MockRedis · Frontend React/Vite/Tailwind · seed CBLOL 2026  
