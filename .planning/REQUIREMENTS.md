# Requirements: Moba Manager

**Defined:** 2026-07-17  
**Core Value:** Loop dia → draft → live → consequências legível e com decisões que pesam  
**Milestone:** v1.1 — Depth & Continuity

## v1.0 Requirements (Validated — career MVP)

Já implementados. Mantidos para rastreabilidade; não reabrir sem decisão de produto.

### Core loop

- [x] **LOOP-01**: Jogador inicia carreira (nome + org CBLOL) e chega ao hub
- [x] **LOOP-02**: Avanço de dia aplica burnout/fadiga e agenda match days
- [x] **LOOP-03**: Match day do manager abre draft snake e partida live
- [x] **LOOP-04**: Resultado atualiza standings e retorna ao hub

### Competição

- [x] **COMP-01**: Calendário round-robin determinístico
- [x] **COMP-02**: Playoffs top 6 com séries BO e campeão
- [x] **COMP-03**: Offseason mínimo + novo split
- [x] **COMP-04**: Patch notes + bias de meta no draft

### Gestão

- [x] **MGMT-01**: Elenco, academy promote/demote, forma
- [x] **MGMT-02**: Mercado com oferta/contra e valuation
- [x] **MGMT-03**: Treino, scrim, scouting, staff hire com powers
- [x] **MGMT-04**: Finanças (folha, receita) e board confidence
- [x] **MGMT-05**: Save/load JSON com snapshot Redis de carreira

### Motor / draft

- [x] **ENG-01**: DraftAI backend no fluxo interativo
- [x] **ENG-02**: Live com ticks, Rift state, ratings, win reasons
- [x] **ENG-03**: Champion pool / flex / counter influenciam draft ou early

## v1.1 Requirements (Active)

### Persistência e estabilidade

- [ ] **STAB-01**: Cliente Redis trata qualquer URL `redis://` / `rediss://` como real (Mock só para `mock`/`memory`/vazio)
- [ ] **STAB-02**: Fadiga de match day do time gerenciado aplicada **uma única vez** (calendário XOR resolução de partida)
- [ ] **STAB-03**: Save/load documentado e seguro: aviso se mid-draft/live; ou snapshot opcional de chaves live/draft
- [ ] **STAB-04**: Nova carreira com reseed exige confirmação explícita na UI (não silencioso)

### Decisões de manager

- [ ] **MGMT-06**: Contratos com cláusulas ricas (duração, salário, buyout, role starter promise) — *legado MK-2*
- [ ] **MGMT-07**: Facility com árvore granular (scrim / analytics / recovery) — *legado OR-3*

### Imersão

- [ ] **ART-01**: Key art draft room alinhada a `docs/STYLE_BIBLE.md` e base `menu-hq-base.jpg`
- [ ] **ART-02**: Mapa blueprint / fantasy wireframe no live (sem mapa oficial Riot)

### Qualidade

- [ ] **QA-01**: Vitest cobre store critical paths ou pure helpers adicionais (≥ 20 cases FE no total)
- [ ] **QA-02**: Playtest UAT documentado para fadiga + draft flex (checklist em `.planning/` ou `docs/`)
- [ ] **QA-03**: `pytest` + build FE + Vitest verdes na CI para mudanças da milestone

## v2 Requirements (Deferred)

### Conteúdo

- **TIER-01**: Pool Desafiante (tier-2) como mercado de talentos
- **AUD-01**: Som sutil (lock-in / victory), mute default
- **TUT-01**: Tutorial curto na 1ª carreira (3 tooltips)

### Arquitetura (longo prazo)

- **ARCH-01**: Unificar núcleo batch/live do match engine
- **ARCH-02**: Fatiar `useGameStore.ts` por domínio
- **ARCH-03**: Redis real default documentado no dev via Docker

### Produto futuro

- **WORLD-01**: Multi-liga / Worlds
- **I18N-01**: Localização EN
- **CLOUD-01**: Auth / cloud save

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multiplayer / ranked | Produto single-player local |
| Auth obrigatório | Sem backend multi-usuário |
| Assets oficiais Riot (mapas/logos) | Licença + style bible própria |
| Reescrita FE do zero | UI madura; risco alto, ROI baixo |
| Motor frame-a-frame cliente LoL | Fora do design de simulação |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STAB-01 | Phase 1 | Pending |
| STAB-02 | Phase 1 | Pending |
| STAB-03 | Phase 1 | Pending |
| STAB-04 | Phase 1 | Pending |
| MGMT-06 | Phase 2 | Pending |
| MGMT-07 | Phase 2 | Pending |
| ART-01 | Phase 3 | Pending |
| ART-02 | Phase 3 | Pending |
| QA-01 | Phase 4 | Pending |
| QA-02 | Phase 4 | Pending |
| QA-03 | Phase 4 | Pending |

**Coverage:**
- v1.1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Requirements defined: 2026-07-17*  
*Last updated: 2026-07-17 after GSD brownfield bootstrap*
