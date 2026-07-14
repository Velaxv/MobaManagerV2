# Handoff de sessão — 2026-07-14 (S1–S3 + playtest)

**Status:** salvo — working tree limpa; `main` = `origin/main`.  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  
**Último commit base:** `93115c0` — scrims, VOD, moral/chemistry (S3)  
**Testes:** **120 passed** (pytest)

---

## Ao reabrir (2 minutos)

1. Abrir a pasta do projeto  
2. Ler este arquivo + `CONTINUIDADE.md`  
3. Jogar:
   ```bat
   run_game.bat
   ```
4. Opcional — testes:
   ```bat
   set PYTHONPATH=.
   venv\Scripts\python -m pytest tests -q
   ```

---

## O que está pronto (jornada estendida)

| Bloco | Conteúdo |
|-------|----------|
| P0–P2 | Liga CBLOL, playoffs base, save, finanças, treino, scouting, academy, patches |
| P3 | API modular, integração httpx, Pydantic v2, CI |
| **Draft Scout** | Recomendações ban/pick (maestria, patch, meta seed, estrelas scoutadas) |
| **S1 Offseason** | Janela de mercado (full/FA-only/fechada), free agents, staff hire/fire |
| **S2 Playoffs** | Séries BO3/BO5 multi-map, fearless, momentum, placar no bracket |
| **S3 Prática** | Scrims, VOD/intel, moral + chemistry + sinergias no hub |

### Stack
- Backend: FastAPI + SQLite + MockRedis  
- Frontend: React/Vite/Tailwind + Zustand  
- Seed: `POST /db/seed` ou `seed_runner.py` (**apaga DB e invalida saves**)  
- Save/load: pasta `saves/`  

### Armadilhas
| Item | Detalhe |
|------|---------|
| Seed | Recria UUIDs → saves quebram |
| MockRedis | Live/calendário/playoffs somem se reiniciar uvicorn mid-session |
| Scrim/VOD | Relatório no advance day (não é draft interativo) |
| Série BO | Fecha só com wins_needed; avance o dia para o próximo map |

---

## Como testar features novas

### S1 — Mercado / staff
- Dev: forçar offseason no Painel  
- Mercado: banner da janela + filtros Free agents / Clubes  
- Comissão técnica no Dashboard  

### S2 — Playoffs série
- Forçar playoffs na Tabela  
- Jogar Map 1 → ver placar → avançar dia → Map 2 com fearless  

### S3 — Scrim / VOD / moral
- Avançar até dia **SCRIM** (qui) ou **MEDIA** (sex)  
- Painel: cards Moral · Scrim · VOD  

---

## Calendário regular (S3)

`SEG treino · TER treino · QUA match · QUI scrim · SEX VOD · SAB match · DOM rest`

---

## Próximo (S4 — a implementar / em curso)

**Dono da org (MVP):**
1. Sponsors (receita + metas)  
2. Board confidence (metas do split + risco de demissão)  
3. Facility 3 níveis (custo mensal + bônus scrim/recovery)  

---

## Espaço para notas de playtest

```
( ) 
( ) 
( ) 
```

---

*Retomar: `CONTINUIDADE.md` → este handoff → `run_game.bat`.*
