# Handoff de sessão — SALVO 2026-07-15

**Status:** Sprint G commitado (após push E+F).  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  

---

## Jogar agora

```bat
run_game.bat
```

Seed **seguro** por padrão (não apaga DB se já semeado).  
Reseed destrutivo: `set SEED_FORCE=1` ou `seed_runner.py --force`.

---

## O que está no jogo

| Sprint | Feature |
|--------|---------|
| Base–S4 | CBLOL, draft, live, playoffs, finanças, treino, scouting, scrim/VOD, board |
| **E** | Motor profundo, Rift, ratings, win reasons |
| **F** | Forma, bench, staff powers, board semanal, pool penalty |
| **G** | Save Redis completo · seed seguro · Vitest · IA mercado · patch mid-split |

### Sprint G — detalhes
- **IN-1** Save v2 grava moral/org/form/treino/scouting/practice/patch no JSON  
- **IN-4** `GET /db/seed/status` · `POST /db/seed?force=true` · runner não-destrutivo  
- **IN-3** Vitest: `frontend/src/lib/riftMap.test.ts` (`npm test`)  
- **MK-1** Rivais fazem até 2 moves/semana na janela (Redis idempotente)  
- **DR-5** Transição de patch no advance (`patch_transition` + feed do board)  

---

## Próximo (Sprint H — polish / conteúdo)
- Brand kit orgs, narração rica, Desafiante, tutorial, som  
- ME-6 coach mid/late · DR-2 counter-pick · OR-2 sponsors com metas  

Plano: [`docs/PLANO_MELHORIAS_SISTEMAS.md`](PLANO_MELHORIAS_SISTEMAS.md)

---

## Armadilhas

| Item | Detalhe |
|------|---------|
| Seed force | `force=true` / `SEED_FORCE=1` **apaga DB** e invalida saves |
| MockRedis | Restart uvicorn perde estado **não salvo** |
| Saves | Pasta `saves/` — v2 inclui career Redis; load restaura chaves |
| Série BO | Avance o dia entre maps da série |

---

## Testes

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q
cd frontend && npm test
```

---

*Retomar: este arquivo + `CONTINUIDADE.md` + `run_game.bat`.*
