# Roadmap: Moba Manager

## Overview

O career MVP (v1.0) já está jogável: liga CBLOL, draft, live, gestão e save. O marco **v1.1 — Depth & Continuity** foca em tornar a carreira **confiável entre sessões**, decisões de manager com **trade-off real**, **imersão visual** alinhada à style bible, e **rede de qualidade** para não regredir o vertical slice.

Fonte de análise: `.planning/codebase/*` + docs legados em `docs/` e `CONTINUIDADE.md`.

## Milestones

| Milestone | Nome | Status |
|-----------|------|--------|
| v1.0 | Career MVP (sprints A–H) | ✅ Shipped (código em `main`) |
| **v1.1** | **Depth & Continuity** | 🔄 Active |
| v2.0 | Conteúdo & arquitetura (Desafiante, unificação engine, i18n) | ⏸ Deferred |

## Phases (v1.1)

- [ ] **Phase 1: Estabilidade de carreira** — Redis, fadiga, save seguro, confirmação de reseed
- [ ] **Phase 2: Decisões com trade-off** — cláusulas de contrato + facility tree
- [ ] **Phase 3: Imersão visual** — draft room + mapa blueprint (style bible)
- [ ] **Phase 4: Qualidade e UAT** — Vitest expandido, playtest fadiga/draft flex, gates verdes

## Phase Details

### Phase 1: Estabilidade de carreira
**Goal**: Sessão de carreira sobrevive a restart e playtest sem bugs que distorcem fadiga/progresso  
**Depends on**: Nothing (first active phase)  
**Requirements**: STAB-01, STAB-02, STAB-03, STAB-04  
**Success Criteria** (what must be TRUE):
  1. Com `REDIS_URL=redis://localhost:6379` (ou host Docker correto), o app usa Redis real — não cai em Mock por substring
  2. Após um match day live do manager, burnout/fadiga dos titulares reflete **uma** aplicação de carga de partida (mensurável em teste)
  3. Tentar save durante draft/live mostra aviso claro **ou** restaura o estado ao load
  4. “Nova carreira” com wipe de DB exige confirmação explícita na UI
**Plans**: TBD (via `/gsd:plan-phase 1`)

Plans:
- [ ] 01-01: Corrigir heurística Mock vs Redis real + testes
- [ ] 01-02: Eliminar fadiga dupla no path manager live
- [ ] 01-03: Save mid-match/draft policy (warn e/ou snapshot)
- [ ] 01-04: UI confirma reseed em nova carreira

### Phase 2: Decisões com trade-off
**Goal**: Contratos e facility criam escolhas difíceis entre splits, não só labels  
**Depends on**: Phase 1 (carreira estável para playtest de mercado/org)  
**Requirements**: MGMT-06, MGMT-07  
**Success Criteria** (what must be TRUE):
  1. Negociação de transferência/renovação expõe duração, salário, buyout e promise de titular
  2. Facility tem ramos distintos (ex.: scrim / analytics / recovery) com efeitos jogáveis
  3. Pelo menos um teste por cláusula crítica e por efeito de facility
**Plans**: TBD

Plans:
- [ ] 02-01: Modelo + API de cláusulas ricas (MK-2)
- [ ] 02-02: UI de negociação/renovação com cláusulas
- [ ] 02-03: Facility tree granular (OR-3) backend + hub

### Phase 3: Imersão visual
**Goal**: Draft e live visualmente no mesmo nível do menu HQ  
**Depends on**: Phase 1 (não bloqueante estrito; pode paralelizar após 1 se arte-only)  
**Requirements**: ART-01, ART-02  
**Success Criteria** (what must be TRUE):
  1. Tela de draft usa key art própria (sem texto/logos na arte; UI em React)
  2. Live/Rift usa visual blueprint fantasy, sem mapa oficial Riot
  3. Assets versionados em `frontend/public/art/` e referenciados no código
**Plans**: TBD

Plans:
- [ ] 03-01: Draft room art (base→edit a partir de menu-hq-base) + integração TacticsDraft
- [ ] 03-02: Mapa blueprint art + integração SummonersRiftMap / MatchSimulation

### Phase 4: Qualidade e UAT
**Goal**: Rede de segurança e evidência de playtest para fechar v1.1  
**Depends on**: Phases 1–3 (ou subset shipped)  
**Requirements**: QA-01, QA-02, QA-03  
**Success Criteria** (what must be TRUE):
  1. Vitest ≥ 20 cases em pure functions / helpers críticos
  2. Checklist UAT fadiga + draft flex preenchido após playtest real
  3. CI (pytest + FE build + vitest) verde no branch da milestone
**Plans**: TBD

Plans:
- [ ] 04-01: Expandir Vitest (store slices / helpers)
- [ ] 04-02: UAT documentado + correções P0 do playtest
- [ ] 04-03: Gate final v1.1 (verify-work / audit)

## Progress

| Phase | Plans complete | Status |
|-------|----------------|--------|
| 1 Estabilidade | 0 / TBD | Not started |
| 2 Trade-offs | 0 / TBD | Not started |
| 3 Imersão | 0 / TBD | Not started |
| 4 Qualidade | 0 / TBD | Not started |

## Legacy sprint map (v1.0 history)

Não reexecutar; referência apenas:

| Sprint | Tema | Status |
|--------|------|--------|
| A–D | Liga, playoffs, save, gestão base | ✅ |
| E | Partida que conta (ME-*) | ✅ |
| F | Manager de verdade (forma, staff, board, pool) | ✅ |
| G | Carreira estável (save Redis, Vitest, seed seguro, market AI, patch) | ✅ |
| H | Brand, narração, counters, sponsors | ✅ parcial |

---
*Roadmap created: 2026-07-17 (GSD brownfield bootstrap)*  
*Next: `/gsd:discuss-phase 1` ou `/gsd:plan-phase 1`*
