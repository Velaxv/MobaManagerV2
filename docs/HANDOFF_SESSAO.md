# Handoff de sessão — SALVO 2026-07-15

**Status:** Tudo commitado e no GitHub. Working tree limpa.  
**Branch:** `main` (up to date com origin)  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Commit:** `06e0439` — `feat: fatigue recovery, flex draft, new career, and War Room UI`

---

## Jogar agora

```bat
run_game.bat
```

Seed seguro por padrão. Reseed: `SEED_FORCE=1` ou `seed_runner.py --force`.

---

## O que está no remote

| Área | Conteúdo |
|------|----------|
| Base–S4 + E–H + ME-7 | CBLOL, draft, live, playoffs, finanças, treino, scouting, brand kit, Rift UI |
| **FADIGA** | `fatigue_recovery.py` + BurnoutService nuance; REST limpa alertas; banco recupera |
| **DRAFT-FLEX** | IA e jogador escolhem (champ, role) livre; FE slots flex |
| **Nova carreira** | `POST /career/new` + wizard `startNewCareer` |
| **War Room UI** | Design system HQ (cyan/orange/glass), facility blur, blueprint draft, radar, PostMatch + heatmap real |

### Explicitamente fora (pedido)
- Coach mid/late · Tutorial · Desafiante / i18n / som  

---

## Backlog livre
- MK-2 cláusulas ricas  
- OR-3 facility tree granular  
- Som sutil (mute default)  
- Desafiante tier-2  
- Playtest UAT fadiga (2 match + REST) e draft flex visual  

---

## Testes (última corrida da sessão UI)

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q
cd frontend && npm test && npm run build
```

Frontend: **28** testes OK + build production.

---

*Retomar: este arquivo + `CONTINUIDADE.md` + `run_game.bat`.*
