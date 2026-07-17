# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-07-17)

**Core value:** Loop dia → draft → live → consequências legível e com decisões que pesam  
**Current focus:** Phase 1 — Estabilidade de carreira (v1.1)

## Current Position

Phase: 1 of 4 (Estabilidade de carreira)  
Plan: — (ainda não planejado)  
Status: **Ready to plan**  
Last activity: 2026-07-17 — Bootstrap GSD: map-codebase (7 docs) + PROJECT/REQUIREMENTS/ROADMAP/STATE

Progress: [░░░░░░░░░░] 0% of v1.1

## Performance Metrics

**Velocity:**
- Total plans completed (v1.1): 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- GSD `.planning/` é a fonte de verdade; `docs/*` e `CONTINUIDADE.md` são histórico + handoff de arte
- Milestone ativa = v1.1 Depth & Continuity; v1.0 career MVP tratado como Validated
- Não reescrever FE/motor por completo nesta milestone
- Prioridade Phase 1 = bugs/persistência antes de feature nova de mercado

### Pending Todos

Nenhum em `.planning/todos/pending/` ainda.

### Blockers/Concerns

Do map 2026-07-17 (`.planning/codebase/CONCERNS.md`):

1. **Redis mock heuristic** — URLs sem substring `localhost` viram Mock
2. **Fadiga dupla** possível no match day do manager
3. **Save** não cobre mid-live/draft
4. **God modules** — `useGameStore.ts`, `match_engine_service.py`, `calendar_service.py` (dívida, não Phase 1 full rewrite)
5. **Dual match engines** batch vs live (dívida longo prazo)

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Content | Desafiante tier-2 | Deferred v2 | 2026-07-17 |
| Content | Som / i18n / tutorial longo | Deferred v2 | 2026-07-17 |
| Arch | Unificar batch/live engine | Deferred v2 | 2026-07-17 |
| Arch | Split Zustand store | Deferred v2 | 2026-07-17 |
| Product | Multi-liga / Worlds / auth | Out of scope | 2026-07-17 |

## Session Continuity

Last session: 2026-07-17  
Stopped at: GSD bootstrap completo (codebase map + project planning files). **Próximo passo:** `/gsd:discuss-phase 1` ou `/gsd:plan-phase 1`.

### Handoff legado (arte)

Última sessão de produto (2026-07-15): key art menu HQ + `docs/STYLE_BIBLE.md`. Assets em `frontend/public/art/menu-hq-*.jpg`. Continuação de arte mapeada na **Phase 3**.

### Como rodar

```bat
run_game.bat
```

### Comandos GSD úteis

| Comando | Quando |
|---------|--------|
| `/gsd:progress` | Ver onde estamos |
| `/gsd:discuss-phase 1` | Alinhar detalhes antes de planejar |
| `/gsd:plan-phase 1` | Criar PLAN.md da Phase 1 |
| `/gsd:execute-phase 1` | Executar planos da phase |
| `/gsd:map-codebase` | Atualizar mapa após mudanças grandes |

---
*State initialized: 2026-07-17*
