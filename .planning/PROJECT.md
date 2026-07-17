# Moba Manager / LoL Manager

## What This Is

Simulador de gestão de esports *League of Legends* no estilo Football Manager, focado no **CBLOL 2026**. O jogador assume o cargo de treinador de uma das 8 organizações oficiais, gerencia calendário, elenco, draft (champion select), partidas ao vivo e pressão de board — em single-player local, sem gacha.

## Core Value

O loop **dia → match day → draft → live → consequências (forma, moral, tabela, finanças)** precisa ser legível e jogável: o manager deve entender *por que* ganhou ou perdeu e sentir que decisões entre jogos importam.

## Current Reality (brownfield)

**Estágio:** protótipo avançado / carreira MVP jogável (sprints A–H em grande parte concluídos).

**Já entregue (validado no código):**
- Seed CBLOL 2026 (8 orgs, elenco, academy, coaches)
- Calendário + round-robin + playoffs BO + offseason
- Snake draft + DraftAI backend + pool/flex/counter
- Match engine live (early 5 roles, map state, ratings, win reasons) + Rift UI
- Carreira: save/load JSON, finanças, treino, scouting, staff powers, board, sponsors
- UI hub FM + draft/live estilo LoL + brand kit orgs + key art menu HQ
- Suite backend ~33 arquivos pytest + Vitest em pure functions (`riftMap`, `orgBrands`, `hubAlerts`)
- CI GitHub Actions; API modular em `src/api/routes/*`

**Gargalo atual:** não é “falta de sistema”, e sim **profundidade, bugs de persistência, acoplamento e polish** — ver `.planning/codebase/CONCERNS.md`.

## Requirements

### Validated

<!-- Shipped career MVP — locked unless product pivot -->

- ✓ Loop core dia → draft → live → standings (CBLOL-first)
- ✓ Liga com round-robin, playoffs top 6, campeão e offseason mínimo
- ✓ Save/load local de carreira (save_version 2 + snapshot Redis career)
- ✓ Gestão: transferências, treino, scouting, academy, staff, finanças, board
- ✓ Draft imersivo + motor live com feedback (ratings, win reason, Rift)
- ✓ Launcher Windows `run_game.bat` + seed CBLOL + UI React madura

### Active

<!-- Milestone v1.1 — Depth & Continuity -->

- [ ] Persistência de sessão confiável (Redis real ou Mock previsível; save sem armadilhas)
- [ ] Bugs de carreira que distorcem playtest (fadiga dupla, heurística Redis)
- [ ] Decisões de manager com trade-off real (cláusulas, facility)
- [ ] Imersão visual alinhada à style bible (draft room, mapa blueprint)
- [ ] Rede de segurança FE expandida + playtest UAT documentado

### Out of Scope

- Multiplayer / ranked / cloud auth — escopo single-player local
- Multi-liga / Worlds — CBLOL-first até carreira local estar sólida
- Motor frame-a-frame estilo cliente LoL — simulação tick é o desenho
- Assets / mapas / marcas oficiais Riot — estilização própria (legal + brand)
- Reescrita total do frontend ou unificação completa batch/live engine nesta milestone
- i18n EN, tutorial longo, som obrigatório — backlog pós v1.1

## Context

- **Stack:** FastAPI + SQLAlchemy async + SQLite (dev) / Postgres+Redis (compose); React 19 + Vite + Tailwind + Zustand
- **Mapa de código:** `.planning/codebase/` (2026-07-17)
- **Docs legados de sprint:** `docs/RELATORIO_*`, `docs/PLANO_*`, `CONTINUIDADE.md`, `docs/HANDOFF_SESSAO.md` — úteis como história; **fonte de verdade de estado** passa a ser `.planning/`
- **Style bible:** `docs/STYLE_BIBLE.md` (cyan/orange/navy; arte sem texto)
- **Remote:** https://github.com/Velaxv/MobaManagerV2.git

## Constraints

- **Tech:** Python 3.12 declarado (alinhar venv local se estiver em 3.11); Node 22 no CI
- **Conteúdo:** seed em `src/shared/cblol_2026_data.py` é a fonte de verdade de orgs/elencos
- **Qualidade:** cada entrega deve manter `pytest tests -q` + `npm run build` (e Vitest no FE quando tocado)
- **Produto:** não quebrar o vertical slice jogável; commits pequenos e jogáveis
- **Legal:** sem assets oficiais Riot; Data Dragon CDN só para campeões genéricos onde já usado

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CBLOL-only seed 2026 | Foco e dados realistas BR | ✓ Good |
| Dual UI language (hub FM + client LoL) | Imersão por contexto | ✓ Good |
| MockRedis default em dev | Zero infra para rodar | ⚠️ Revisit — bugs de URL + perda de estado |
| Live engine separado do batch | UX tick-by-tick vs auto-sim rápido | ⚠️ Revisit longo prazo |
| Save JSON local + Redis snapshot career | Multi-sessão sem cloud | ✓ Good (gaps mid-match) |
| GSD `.planning/` como fonte de verdade | Docs de sprint espalhados e parcialmente stale | ✓ 2026-07-17 |

---
*Last updated: 2026-07-17 after GSD brownfield bootstrap*
