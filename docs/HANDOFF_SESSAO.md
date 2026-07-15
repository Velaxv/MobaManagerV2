# Handoff de sessão — SALVO 2026-07-15

**Status:** Fadiga + Draft flex + UI HQ + **nova carreira do zero** implementados.  
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
| **FADIGA** | Recovery com nuance; banco em match day; alertas somem após REST |
| **DRAFT-FLEX** | Pick = campeão + qualquer role livre (IA + jogador) |

### Feature A — Fadiga / restauração
- Módulo puro: `src/modules/calendar/fatigue_recovery.py`
- `BurnoutService` usa recovery_mult (forma, moral, board, staff, intensidade)
- REST / treino LIGHT-NORMAL / mídia recuperam; HARD e SCRIM carregam
- MATCH: titulares +carga; banco **recupera** levemente
- Eventos: `FATIGUE_RECOVERY`, `POOR_RECOVERY`, `MATCH_DAY_FATIGUE`, `BENCH_RECOVERY`
- Testes: `tests/test_fatigue_recovery.py`

### Feature B — Draft flex
- `score_flex_options` + `_decide_pick` em `draft_ai.py` (não força TOP→…→SUP)
- Scout scoreia roles abertas (melhor par champ/role)
- FE `TacticsDraft`: roles já pickadas desabilitadas; lock em qualquer role livre
- Testes: flex em `tests/test_draft_ai.py`

### Nova carreira do zero
- Endpoint `POST /career/new` — limpa Redis + `force` reseed CBLOL (semana 1/dia 1)
- Wizard chama `startNewCareer(nome, abreviação)` — IDs de time são remapeados
- Zera store FE (partida ativa, draft, standings, finanças em cache, etc.)
- Saves em disco (`saves/`) **não** são apagados automaticamente

### UI HQ (design PDF — `dashboard mobamanager.pdf`)
- Tokens: `lol-hq-cyan` / `lol-hq-orange`, painéis glass, hub ambient sede
- **Elenco:** botão Análise / clique no card → `PlayerProfilePanel` (radar + pool + coach notes)
- **Draft:** `CompositionSynergy` (Manager Analytics · Engage/Poke/Disengage)
- **Pós-jogo:** `PostMatchAnalysis` (timeline · gold differential · heatmap · ratings)
- **Rift:** shell holográfico blue/orange

### Explicitamente **fora** (pedido)
- Coach mid/late  
- Tutorial interativo  
- Desafiante / i18n / som  

---

## Próximas ideias (backlog livre)
- MK-2 cláusulas ricas  
- OR-3 facility tree granular  
- Som sutil (mute default)  
- Desafiante tier-2  
- Playtest UAT fadiga (2 match + REST) e draft flex visual  

---

## Testes

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q
cd frontend && npm test && npm run build
```

Última corrida: **168** backend + **26** frontend OK.

---

*Retomar: este arquivo + `CONTINUIDADE.md` + `run_game.bat`.*
