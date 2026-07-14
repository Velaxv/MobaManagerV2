# Handoff de sessão — 2026-07-14

**Status:** sessão encerrada com segurança — tudo commitado em `main` (local).  
**Working tree:** limpa.  
**Branch:** `main` **ahead of origin by 13** (após este handoff).

---

## Ao reabrir (checklist de 2 minutos)

1. Abrir a pasta do projeto  
2. Ler este arquivo + `CONTINUIDADE.md`  
3. Roadmap: `docs/RELATORIO_MELHORIAS_CONTINUIDADE.md`  
4. Rodar testes: deve dar **92 passed, 0 warnings**
   ```bat
   set PYTHONPATH=.
   venv\Scripts\python -m pytest tests -q
   ```
5. Jogar:
   ```bat
   run_game.bat
   ```
   ou backend + seed + `cd frontend && npm run dev`

6. **Opcional (backup remoto):**
   ```bat
   git push origin main
   ```

---

## O que está pronto (jornada 2026-07-14)

| ID | Entrega | Commit (ref) |
|----|---------|--------------|
| P0-3 | Calendário visual com adversário RR | `a9f00b2` + fix UUID |
| P1-1 | Playoffs top 6 + campeão | `6fb1f27` |
| P1-6 | Resultados da rodada + ver log | `67b685f` |
| P1-3 | Save/Load JSON (`saves/`) | `0d923ce` |
| P1-2 | Offseason renovar/liberar + novo split | `39a8c9a` |
| P1-4 | Draft AI backend no oponente | `e3a3470` |
| P1-5 | Táticas pré-partida | `7b2f3cb` |
| — | Fotos reais + silhueta | `b6dd6cf` |
| P2-1 | Finanças (folha/receita/tick 28d) | `6590620` |
| P2-2 | Negociação transferência | `19dd0fc` |

### Stack / como rodar
- Backend: FastAPI + SQLite + MockRedis  
- Frontend: React/Vite/Tailwind  
- Seed: `POST /db/seed` ou `seed_runner.py` (**apaga DB e invalida saves**)  
- Save/load: pasta `saves/` — não rode seed entre save e load  

### Armadilhas
| Item | Detalhe |
|------|---------|
| Seed | Recria UUIDs → saves quebram |
| MockRedis | Live/calendário/playoffs em memória somem se reiniciar uvicorn mid-session |
| Fotos | 42/45 OK; Ayu, Curse, Envy = silhueta |

---

## Próxima sessão (prioridade)

1. **P3-6** — CI GitHub Actions  
2. **P3-3** — Testes frontend (Vitest)  
3. Push remoto se ainda não fez: `git push origin main`

### Feito nesta retomada
| ID | Entrega | Notas |
|----|---------|-------|
| P3-1 | Modularizar `main.py` | `src/api/` — schemas, serializers, routes por domínio; `main.py` ~70 linhas |
| P2-3 | Treino / CA→PA | `TrainingService`, plano foco/intensidade, XP em treino+partida, UI no Painel |
| P2-4 | Scouting | Consistência/BMA/PA mascarados; assignment + progresso diário; UI Elenco/Mercado/Painel |
| P2-5 | Academy | `is_starter`, promote/demote, cláusulas rookie na UI, seções Elenco |
| P2-6 | Patches | Notas 16.1/16.2, tela Patch, badges no draft, bias na DraftAI |
| P3-2 | Integração API | httpx ASGI + SQLite temp: seed→advance→standings + academy/patch |
| P3-4 | Pydantic v2 + lifespan | `SettingsConfigDict`, `lifespan=`, `model_dump`; 0 warnings |

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

:: Fotos (regerar mapa)
venv\Scripts\python scripts\fetch_player_photos.py --missing
```

---

*Pode fechar a sessão. Retomar por `CONTINUIDADE.md` → este handoff.*
