# Handoff de sessão — SALVO 2026-07-14

**Status:** tudo commitado e no GitHub.  
**Branch:** `main` = `origin/main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Último commit:** `651f1f9` — S4 org (board, sponsors, facility)  
**Testes:** **127 passed** (`pytest tests -q`)

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

## O que está no jogo (S1–S4)

| Sprint | Feature |
|--------|---------|
| Base | CBLOL 2026, draft, live, playoffs, save/load, finanças, treino, scouting, patches, CI |
| Scout | Dicas ban/pick no draft (patch, maestria, meta, estrelas) |
| **S1** | Janela de mercado, free agents, contratar/demitir staff |
| **S2** | Playoffs BO3/BO5 multi-map, fearless, momentum |
| **S3** | Scrims, VOD, moral/chemistry no hub |
| **S4** | Board, sponsors, facility 3 níveis, demissão |

### Painel — o que olhar
- **Organização** — board, sponsors, upgrade sede  
- **Moral / Scrim / VOD** — prática da semana  
- **Comissão técnica** — staff  
- **Offseason** — renovar/liberar + mercado FA  

### Calendário regular
`SEG/TER treino · QUA match · QUI scrim · SEX VOD · SAB match · DOM rest`

---

## Armadilhas

| Item | Detalhe |
|------|---------|
| Seed | `seed_runner` / `POST /db/seed` **apaga DB** e invalida saves |
| MockRedis | Reiniciar uvicorn perde live/calendário/playoffs em memória |
| Saves | Pasta `saves/` — mesmo seed/DB em que salvou |
| Série BO | Avance o dia entre maps da série |

---

## Testes

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q
```

---

## Notas de playtest (cole aqui)

```
( ) 
( ) 
( ) 
```

---

*Pode fechar a sessão. Retomar: este arquivo + `CONTINUIDADE.md` + `run_game.bat`.*
