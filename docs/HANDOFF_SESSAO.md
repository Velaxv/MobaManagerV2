# Handoff de sessão — 2026-07-14 (playtest)

**Status:** sessão salva — working tree limpa; `main` = `origin/main`.  
**Remote:** `https://github.com/Velaxv/MobaManagerV2.git`  
**Último commit:** `1b734fb` — CI GitHub Actions (P3-6)  
**CI:** configurado e validado no GitHub Actions  

---

## Ao reabrir (checklist de 2 minutos)

1. Abrir a pasta do projeto  
2. Ler este arquivo + `CONTINUIDADE.md`  
3. Colar/anotar melhorias do playtest (abaixo ou novo arquivo)  
4. Opcional — testes: deve dar **92 passed**
   ```bat
   set PYTHONPATH=.
   venv\Scripts\python -m pytest tests -q
   ```
5. Jogar:
   ```bat
   run_game.bat
   ```
   ou backend + seed + `cd frontend && npm run dev`

---

## O que está pronto (jornada 2026-07-14)

| ID | Entrega |
|----|---------|
| P0 | Calendário RR, burnout, velocidade live |
| P1 | Playoffs, resultados, save/load, offseason, DraftAI, táticas |
| P2 | Finanças, transferências, treino CA→PA, scouting, academy, patches |
| P3 | API modular, integração httpx, Pydantic v2 + lifespan, **CI** |
| — | Fotos reais + silhueta; seed CBLOL 2026 |

### Stack / como rodar
- Backend: FastAPI + SQLite + MockRedis  
- Frontend: React/Vite/Tailwind  
- Seed: `POST /db/seed` ou `seed_runner.py` (**apaga DB e invalida saves**)  
- Save/load: pasta `saves/` — não rode seed entre save e load  
- Repo: https://github.com/Velaxv/MobaManagerV2  

### Armadilhas
| Item | Detalhe |
|------|---------|
| Seed | Recria UUIDs → saves quebram |
| MockRedis | Live/calendário/playoffs em memória somem se reiniciar uvicorn mid-session |
| Fotos | Alguns jogadores = silhueta (ex.: Ayu, Curse, Envy) |

---

## Playtest em andamento

O usuário vai jogar e anotar melhorias **na mão**.

**Ao voltar:** trazer a lista de notas → priorizar e implementar.

### Espaço para colar notas (opcional)
```
( ) 
( ) 
( ) 
```

---

## Próxima sessão (após playtest)

1. Revisar anotações de melhorias  
2. Priorizar 1–3 itens (bugs > UX > features)  
3. Opcional: P3-3 Vitest / polish P4  

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

:: Jogo completo
run_game.bat
```

---

*Pode fechar a sessão. Retomar por `CONTINUIDADE.md` → este handoff + notas de playtest.*
