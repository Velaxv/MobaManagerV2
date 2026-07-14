# Relatório de Estado Atual — Moba Manager / LoL Manager

**Data do relatório:** 2026-07-14  
**Projeto:** Simulador de gestão de esports *League of Legends* (estilo Football Manager + cliente LoL)  
**Branch:** `main`  
**Versão conceitual da UI:** v1.2 (hub + draft + live polidos)  
**Último commit base conhecido:** `bb78583` — *Integração de Calendário e Fase 3 Completa* (+ alterações locais desta sessão ainda a commitar)

---

## 1. Resumo executivo

O **Moba Manager** é um protótipo jogável de *career mode* focado no **CBLOL 2026** (8 organizações oficiais do Split 1). O jogador assume o papel de treinador, gerencia calendário e elenco, disputa partidas com **snake draft** estilo cliente e acompanha simulação **ao vivo** com coach comms.

| Dimensão | Avaliação | Comentário |
|----------|-----------|------------|
| **Jogabilidade core** | Alta (MVP) | Loop dia → match day → draft → live → standings funciona |
| **Motor de simulação** | Alta | Draft AI, MatchEngine Early/Mid/Late, live ticks, testes unitários |
| **Dados / seed** | Alta | CBLOL 2026 realista (8 times, elenco, coaches) |
| **UI / imersão** | Alta | Hub FM + draft/live estilo LoL + wizard de carreira |
| **Profundidade de gestão** | Média-baixa | Transferências MVP; sem save, scouting, finanças profundas |
| **Arquitetura / produção** | Média | Monólito de rotas; SQLite+MockRedis em dev; Postgres/Redis preparados |
| **Testes** | Média | 15 testes backend; frontend sem suite automatizada de UI |

**Conclusão:** o projeto está em estágio de **protótipo avançado / vertical slice jogável**, com forte ênfase em motor + apresentação. Ainda não é um produto completo de temporada, mas já entrega a fantasia central de “manager de LoL no Brasil”.

---

## 2. O que o jogo é hoje

### 2.1 Premissa
- Gestão de time de LoL no **CBLOL 2026**
- Sem gacha; foco em dados, calendário, draft e simulação
- Um treinador (nome + time) por sessão (sem persistência de save)

### 2.2 Loop principal (jogável)
```
Menu principal
  → Wizard (nome + org CBLOL)
  → Hub (Painel FM)
       → Avançar dia (burnout, calendário, match day)
       → Se o time joga: Draft (Champion Select)
       → Live match (ticks + coach comms)
       → Vitória / standings / retorno ao hub
  → Mercado (contratar de outras orgs)
  → Elenco / Tabela em qualquer momento
```

### 2.3 Organizações no seed (8)
| Tag | Time | Notas |
|-----|------|--------|
| RED | RED Canids Kalunga | Academy |
| FUR | FURIA Esports | Academy |
| VKS | Vivo Keyd Stars | Academy |
| LOS | LØS | Guest, sem academy full |
| FX7 | Fluxo W7M | Academy |
| LLL | LOUD | Academy |
| PNG | paiN Gaming | Academy |
| LEV | Leviatán | Academy |

Removidos do circuito 2026 no seed: KaBuM, INTZ, Liberty e times estrangeiros (G2, T1, etc.).

---

## 3. Stack e infraestrutura

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 async, Pydantic Settings, Alembic |
| Frontend | React 19, TypeScript, Vite 8, Tailwind 3, Zustand, Lucide |
| Dev local | **SQLite** (`lol_manager.db`) + **MockRedis** em memória |
| Produção (preparado) | PostgreSQL 16 + Redis 7 (`docker-compose.yml`) |
| Assets de campeões | Data Dragon CDN (Riot) — retratos, splash, loading |
| Launcher Windows | `run_game.bat` (pytest → build FE → uvicorn → seed → Vite) |

**Arquivos de configuração relevantes:** `.env` / `.env.example`, `pyproject.toml`, `frontend/package.json`, `alembic.ini`.

---

## 4. Arquitetura de software

### 4.1 Backend (`src/`)
```
src/
  main.py                 # API monolítica (rotas + seed grande)
  core/                   # config, database, redis_client (mock/real)
  models/                 # Player, Team, Contract, League, Match, Champion, Patch, Staff
  modules/
    calendar/             # State machine, burnout, advance day, auto-sim de outros jogos
    draft/                # Snake draft, DraftAI, analyzer/penalties
    simulation/           # MatchEngine batch + MatchEngineService live + strategies
  shared/                 # enums, math_utils, champions_data, cblol_2026_data
tests/                    # 5 arquivos · 15 testes unitários
```

### 4.2 Frontend (`frontend/src/`)
```
screens/
  MainMenu, NewGameWizard
  Dashboard, Squad, Standings, TransferMarket
  TacticsDraft, MatchSimulation
components/
  GameShell, ChampionImage, RoleIcon, DataGrid
store/useGameStore.ts     # estado global Zustand
services/api.ts           # cliente HTTP → :8000
lib/champions.ts          # Data Dragon IDs/URLs
```

### 4.3 APIs expostas (principais)
| Método | Rota | Função |
|--------|------|--------|
| GET | `/` | Health |
| POST | `/db/seed` | Recria DB + seed CBLOL 2026 |
| GET/POST | `/calendar`, `/calendar/advance` | Estado e avanço (+ `managed_team_id`) |
| GET | `/teams`, `/teams/{id}/players` | Times e elenco |
| GET | `/leagues`, `/leagues/{id}/standings` | Liga e tabela |
| GET | `/champions` | Pool de campeões |
| GET | `/market/players` | Mercado |
| POST | `/transfers/sign` | Contratação |
| POST | `/matches/simulate` | Simulação batch (IA full) |
| POST/GET | `/matches/live/*` | Partida ao vivo + coach comm |

---

## 5. Sistemas de gameplay — status

### 5.1 Calendário e burnout — **Integrado**
- State machine de fases (regular season etc.)
- Avanço diário com burnout por tipo de dia
- Match day: pareamento aleatório; jogos do manager ficam para a UI; demais auto-simulam
- Patch cache (serviço + modificadores no seed)

### 5.2 Draft — **Integrado + UI polida**
- Ordem snake oficial (20 ações)
- IA no oponente no frontend (com lock-in visual)
- Backend DraftAI / penalties / snake_draft
- UI: splash, role icons, lock-in/ban overlay, grid com fotos Data Dragon

### 5.3 Motor de partida — **Integrado + UI polida**
- Batch: Early/Mid/Late strategies (numpy/estocástico)
- Live: ticks ~2s/min, ouro, kills, objetivos, logs, standings ao fim
- Coach comms no early game (sucesso/falha/confusão)
- UI: scoreboard, gold bar, feed, victory overlay, lineup

### 5.4 Gestão de elenco — **Parcial**
- Atributos CA/PA, mentais, fadiga, pool por role no seed
- Tela de elenco completa (titulares + academy)
- Transferências reais no backend (taxa fixa €250k, budget no DB)
- Sem negociação multi-oferta, salário dinâmico ou free agents globais

### 5.5 Liga / standings — **Funcional básico**
- Atualização em auto-sim e live match
- Tela de tabela com zona de playoffs (top 6)
- Sem calendário fixo de confrontos (shuffle por match day)

### 5.6 Carreira / meta-progressão — **Mínimo**
- Wizard de nova carreira (3 passos, preview de elenco)
- Sem save/load, sem multi-season, sem offseason completo

---

## 6. UI / UX — estado

### Telas e maturação visual
| Tela | Maturação | Notas |
|------|-----------|--------|
| Main Menu | Alta | Splash, branding CBLOL |
| New Game Wizard | Alta | 3 steps, cards, preview API |
| GameShell (hub) | Alta | Sidebar Gestão/Competição, KPIs no top |
| Dashboard | Alta | KPIs, calendário, titulares, mini-tabela |
| Squad | Alta | Cards splash + reservas filtráveis |
| Standings | Alta | Zona playoffs, destaque do clube |
| Transfer Market | Alta | Filtros, fotos, DataGrid |
| Tactics Draft | Muito alta | Champion Select imersivo |
| Match Simulation | Muito alta | Live + victory overlay |

### Identidade visual
- **Hub:** Football Manager (sidebar, painéis, abas)
- **Competição:** Cliente LoL (void/hextech/gold, blue/red side)
- Fontes: Cinzel (display), Inter, JetBrains Mono
- Tokens Tailwind `lol-*`

---

## 7. Qualidade e operação

### Testes
- Backend: **15 passed** (`tests/test_draft_*`, `test_match_engine*`, `test_math_utils`)
- Frontend: **build TypeScript OK**; sem E2E/Jest/Vitest no momento
- `run_game.bat` roda pytest + build FE como gate local

### Dívida técnica conhecida
1. `src/main.py` monolítico (seed + todas as rotas)
2. MockRedis: estado live some ao reiniciar uvicorn
3. Live match demora ~80s (2s × ~40 min)
4. Warnings Pydantic v2 (`.dict()`, `Config` class)
5. Calendário visual semanal ainda é template (não 100% gerado pela SM)
6. Draft FE controla também turns do RED (IA local, não a DraftAI do backend no fluxo interativo)
7. Sem autenticação / multi-usuário
8. Seed `drop_all` destrutivo

### Documentação existente
| Arquivo | Conteúdo |
|---------|----------|
| `CONTINUIDADE.md` | Log de sessões e como rodar |
| `docs/RELATORIO_ESTADO_ATUAL.md` | Este relatório |
| `docs/RELATORIO_MELHORIAS_CONTINUIDADE.md` | Roadmap de melhorias |

---

## 8. Como rodar (estado atual)

```bat
run_game.bat
```

Ou manualmente:
1. Backend: `PYTHONPATH=. venv\Scripts\python -m uvicorn src.main:app --port 8000`
2. Seed: `python seed_runner.py` ou `POST /db/seed`
3. Frontend: `cd frontend && npm run dev` → http://localhost:5173  
4. API docs: http://127.0.0.1:8000/docs  

**Requisitos:** rede para imagens Data Dragon; seed após mudanças de schema/dados.

---

## 9. Maturidade por “definição de pronto”

| Critério de produto | Status |
|---------------------|--------|
| Vertical slice jogável (1 split, 1 liga) | **Sim** |
| Identidade visual coerente | **Sim** |
| Dados regionais corretos (CBLOL 2026) | **Sim** |
| Temporada completa (playoffs → offseason → renovação) | Não |
| Persistência de carreira | Não |
| Balanceamento competitivo auditado | Parcial (motor existe; tuning contínuo) |
| Multiplataforma / release | Não (dev local Windows-first) |
| Cobertura de testes de integração API+UI | Não |

---

## 10. Veredito

O jogo **está em bom estado para demonstração e continuação de desenvolvimento**:

- **Forte:** motor matemático, seed CBLOL, loop de carreira, UI imersiva draft/live/hub  
- **Frágil:** persistência, calendário competitivo formal, profundidade de gestão, modularização  
- **Próximo salto de valor:** fechar temporada (playoffs + offseason) e save/load  

Ver `docs/RELATORIO_MELHORIAS_CONTINUIDADE.md` para o plano priorizado de evolução.
