# Handoff de sessão — SALVO 2026-07-15

**Status:** Sprint E + Sprint F no working tree (commit desta sessão).  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  

---

## Jogar agora

```bat
run_game.bat
```

Ou manual:
```bat
set PYTHONPATH=.
venv\Scripts\python -m uvicorn src.main:app --port 8000
venv\Scripts\python seed_runner.py
cd frontend && npm run dev
```

---

## O que está no jogo

| Sprint | Feature |
|--------|---------|
| Base–S4 | CBLOL 2026, draft, live, playoffs BO, save, finanças, treino, scouting, patches, scrim/VOD/moral, board/sponsors/facility |
| **E** | Motor com profundidade: chemistry, torres/lanes no BE, early 5 roles, ratings 0–10, win reasons, Rift map |
| **F** | Forma (last 5), bench discontent, staff powers jogáveis, board review semanal, champion pool penalty |

### Painel — o que olhar
- **Organização** — board semanal, sponsors, upgrade sede  
- **Moral / Scrim / VOD** — prática da semana  
- **Elenco** — forma recente + discontent de reserva  
- **Comissão técnica** — poderes (Head Coach comms, Strategic draft, Performance recovery)  
- **Draft** — pool/comfort + staff meta  
- **Live** — ratings e motivo de vitória no overlay  

### Calendário regular
`SEG/TER treino · QUA match · QUI scrim · SEX VOD · SAB match · DOM rest`

---

## Próximo (Sprint G — carreira estável)

1. **IN-1** Save inclui snapshots Redis (moral, org, form)  
2. **IN-3** Vitest (store + riftMap)  
3. **IN-4** Seed não destrutivo / new career explícito  
4. **MK-1** IA de mercado (rivais)  
5. **DR-5** Patch mid-split  

Plano detalhado: [`docs/PLANO_MELHORIAS_SISTEMAS.md`](PLANO_MELHORIAS_SISTEMAS.md)

---

## Armadilhas

| Item | Detalhe |
|------|---------|
| Seed | `seed_runner` / `POST /db/seed` **apaga DB** e invalida saves |
| MockRedis | Reiniciar uvicorn perde live/calendário/playoffs/form/org em memória |
| Saves | Pasta `saves/` — mesmo seed/DB em que salvou; form/org ainda não 100% no JSON |
| Série BO | Avance o dia entre maps da série |

---

## Testes

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q
```

---

*Retomar: este arquivo + `CONTINUIDADE.md` + `run_game.bat`.*
