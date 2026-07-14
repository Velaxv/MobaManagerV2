# Handoff de sessão — 2026-07-14

**Status:** trabalho salvo localmente (commit em `main`).  
**Pode fechar a sessão com segurança.**

---

## Ao reabrir (checklist de 2 minutos)

1. Abrir a pasta do projeto  
2. Ler este arquivo + `CONTINUIDADE.md`  
3. Roadmap: `docs/RELATORIO_MELHORIAS_CONTINUIDADE.md`  
4. Estado do jogo: `docs/RELATORIO_ESTADO_ATUAL.md`  
5. Rodar:
   ```bat
   run_game.bat
   ```
   ou backend + seed + `cd frontend && npm run dev`

6. Verificar: `pytest` deve dar **40 passed**

---

## O que foi entregue nesta jornada (resumo)

### Backend
- Seed **CBLOL 2026 Split 1** (8 times oficiais) em `src/shared/cblol_2026_data.py`
- API players/mercado/transferências/calendário/`managed_team_id`
- Live match: standings + **burnout** nos titulares ao fim
- **Velocidade live** 1x / 2x / 4x / instant (`POST /matches/live/{id}/speed`)
- **Round-robin** determinístico (`src/shared/round_robin.py`)
- Auto-sim de jogos de terceiros no match day

### Frontend
- Hub estilo Football Manager (`GameShell` + Painel/Elenco/Tabela/Mercado)
- Draft estilo cliente LoL (splash, lock-in, role icons, Data Dragon)
- Live match polida (scoreboard, victory, speed controls)
- New Game Wizard em 3 passos com preview de elenco
- Menu principal imersivo

### Docs
- `CONTINUIDADE.md` — como rodar + log
- `docs/RELATORIO_ESTADO_ATUAL.md` — como o jogo está
- `docs/RELATORIO_MELHORIAS_CONTINUIDADE.md` — backlog P0–P4
- Este handoff

### Testes
- **36 passed** (unitários backend)

### P1-1 Playoffs (sessão atual)
- `src/modules/calendar/playoff_service.py` — bracket top 6
- `GET/POST /leagues/{id}/playoffs` (+ `/start` forçado para playtest)
- Standings com seed/placement; Dashboard banner + chave na Tabela

---

## Próxima sessão (prioridade)

1. **P1-2** — Offseason mínimo  
2. **P1-4** — Draft AI backend no fluxo interativo  
3. **P1-3** — ✅ Save/Load (`saves/*.json`, não rode seed entre save e load)  
4. **P1-6 / P1-1** — ✅  
5. Commit local + **push para origin** se quiser backup remoto:
   ```bat
   git push origin main
   ```

---

## Comandos úteis

```bat
:: Testes
set PYTHONPATH=.
venv\Scripts\python -m pytest tests -q

:: Backend
set PYTHONPATH=.
venv\Scripts\python -m uvicorn src.main:app --port 8000

:: Seed (APAGA o SQLite e recria)
venv\Scripts\python seed_runner.py

:: Frontend
cd frontend
npm run dev
```

---

*Sessão encerrada em estado jogável e documentado.*
