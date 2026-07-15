# Handoff de sessão — SALVO 2026-07-15

**Status:** Sprint H (polish seletivo) commitado.  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  

---

## Jogar agora

```bat
run_game.bat
```

Seed seguro por padrão. Reseed: `SEED_FORCE=1` ou `seed_runner.py --force`.

---

## Sprints entregues

| Sprint | Feature |
|--------|---------|
| Base–S4 | CBLOL, draft, live, playoffs, finanças, treino, scouting, scrim/VOD, board |
| **E** | Motor profundo, Rift, ratings, win reasons |
| **F** | Forma, bench, staff powers, board semanal, pool |
| **G** | Save Redis, seed seguro, Vitest, IA mercado, patch mid-split |
| **H** | Brand kit orgs · narração · counter-pick early · sponsors com metas |
| **ME-7** | Rift UI refinada — HP de torre, contest bar, mini-feed, pressão |

### Sprint H — o que entrou
- **Brand kit** — cores/crest por org no hub, tabela e wizard  
- **Narração** — templates PT-BR por tipo de evento (live feed)  
- **DR-2** — counter lane → mult de duelo early + relatório no start da live  
- **OR-2** — sponsors com meta de ranking + vitórias; payout sobe/desce  

### ME-7 — Rift UI refinada
- Barras de HP em torres/inhib sob siege (via `lane_pressure`)  
- Contest bar Dragão/Baron/Arauto no poço  
- Mini-feed no canto do minimapa  
- Setas de pressão de lane  


### Explicitamente **fora** deste sprint (pedido)
- Coach mid/late (não faz sentido em LoL real)  
- Tutorial interativo  
- Desafiante / i18n / som  

---

## Próximas ideias (backlog livre)
- ME-7 UI Rift refinada (contest bar / HP torre)  
- DR-3 flex picks DraftAI  
- MK-2 cláusulas ricas  
- OR-3 facility tree granular  
- Som sutil (mute default)  
- Desafiante tier-2  

---

## Testes

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q
cd frontend && npm test && npm run build
```

---

*Retomar: este arquivo + `CONTINUIDADE.md` + `run_game.bat`.*
