# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-14 (P3-1 modularização API)  
**Branch:** `main`  
**Estado:** P3-1 feito — `main.py` slim + `src/api/routes/*`  

### Leitura na retomada (ordem)
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md) — checklist de 2 min  
2. [`docs/RELATORIO_MELHORIAS_CONTINUIDADE.md`](docs/RELATORIO_MELHORIAS_CONTINUIDADE.md) — o que fazer a seguir  
3. Este arquivo — stack + como rodar  

### Entregue nesta jornada (fechado)
P0 calendário RR · P1 playoffs/resultados/save/offseason/draftAI/táticas · fotos · P2 finanças + transferências · **P3-1 modularizar API**  
**Testes: 56 passed** · OpenAPI: 35 paths  

### Próxima sessão
1. **P2-3** Treino / CA→PA  
2. **P2-4** Scouting / atributos ocultos  
3. `git push origin main` (backup remoto opcional)  

```bat
run_game.bat
```

---

## O que é o projeto

Simulador de gestão de esports LoL (estilo Football Manager), seed **CBLOL 2026**.  
Backend matemático (draft + match engine + calendário + burnout) + UI React brutalista.

### Stack
| Camada | Tech |
|--------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Alembic |
| Frontend | React 19, Vite 8, TS, Tailwind, Zustand |
| Dev local | SQLite (`lol_manager.db`) + MockRedis (`REDIS_URL=mock`) |
| Full | Postgres + Redis via `docker-compose.yml` |

### Como rodar
```bat
run_game.bat
```
Ou:
1. `PYTHONPATH=. venv\Scripts\python -m uvicorn src.main:app --port 8000`
2. `python seed_runner.py` (ou `POST /db/seed`)
3. `cd frontend && npm run dev` → http://localhost:5173  
API docs: http://127.0.0.1:8000/docs

---

## Seed oficial CBLOL 2026 Split 1 (8 times)

Arquivo: `src/shared/cblol_2026_data.py` · Endpoint: `POST /db/seed`

| Tag | Time | Titulares (T/JG/MID/BOT/SUP) |
|-----|------|------------------------------|
| RED | RED Canids Kalunga | zynts / STEPZ / **Kaze** / Rabelo / frosty |
| FUR | FURIA Esports | Guigo / **Tatu** / Tutsz / **Ayu** / **JoJo** |
| VKS | Vivo Keyd Stars | Wizer / Disamis / Mireu / ceo / Kaiwing |
| LOS | LØS (guest) | **Zest** / Curse / Feisty / Duduhh / Ackerman |
| FX7 | Fluxo W7M | curty / Peach / cody / BAO / Momochi |
| LLL | LOUD | Xyno / YoungJae / Envy / Bull / RedBert |
| PNG | paiN Gaming | Robo / CarioK / Keine / Trigger / Kuri |
| LEV | Leviatán | Devost / Booki / Enga / Snaker / Toplop |

**Removidos do seed:** KaBuM, INTZ, Liberty, e qualquer time de fora (G2, T1, LEC, LPL…).  
**Mercado:** apenas jogadores de outras orgs do CBLOL 2026.  
**Após atualizar o seed:** rode `POST /db/seed` ou `python seed_runner.py` (apaga e recria o SQLite).

---

## UI imersiva (2026-07-14)

### Direção visual
- **Dia a dia:** hub estilo Football Manager — sidebar com abas (Painel, Elenco, Tabela, Mercado, Draft, Partida) + top bar (time, semana, orçamento, match day).
- **Draft / partida:** estética cliente LoL (void/hextech/gold, blue/red side) com **retratos Data Dragon** nos picks, bans e grid de campeões.

### Arquivos-chave UI
| Arquivo | Papel |
|---------|--------|
| `frontend/src/lib/champions.ts` | CDN Data Dragon (portrait/splash) + IDs especiais |
| `frontend/src/components/ChampionImage.tsx` | Componente de imagem de campeão |
| `frontend/src/components/GameShell.tsx` | Shell FM (sidebar + topbar) |
| `frontend/src/screens/TacticsDraft.tsx` | Champion Select estilo LoL |
| `frontend/src/screens/MatchSimulation.tsx` | Scoreboard + picks com fotos |
| `frontend/src/screens/Dashboard.tsx` / `Squad.tsx` / `Standings.tsx` | Hub de gestão |
| `frontend/tailwind.config.js` + `index.css` | Tokens `lol-*`, painéis, botões |

### Draft refinements (fechado)
- Splash de fundo dinâmico (seleção / último pick)
- Ícones de role (TOP/JG/MID/BOT/SUP) estilo cliente
- Overlay **LOCKED IN** / **BANNED** com loading art + barra
- Slots com glow, label Lock, slot ativo piscando
- Barra de progresso 0–20 do snake draft
- Preview splash do campeão selecionado

### Live match refinements (fechado)
- Splash dinâmico do mid do lado na frente
- Scoreboard estilo client (kills pop, gold bar, dragons/barons, timer)
- Chips Early/Mid/Late + barra de fase
- Lineup com fotos + RoleIcon por lado
- Feed com auto-scroll e flash no último evento
- Coach Comms com medidores e pulse
- Overlay **VICTORY** com picks do vencedor
- Store sincroniza minuto, drakes e barons do backend

### Hub FM refinements (fechado)
- GameShell: sidebar Gestão/Competição, crest do time, rank, badges Live/Match Day
- Dashboard: KPIs, calendário, titulares com fotos/roles, standings mini
- Elenco: cards com splash header, pool de champs, filtros de reserva
- Tabela: stats do seu time, zona playoffs, destaque do clube
- Mercado: filtros com RoleIcon, retratos, CA, grid polido
- Main menu: splash Aatrox + tags de features
- New Game Wizard: 3 steps (nome → org → confirmar), cards de time, flavor CBLOL, preview de titulares, splash por org

### Como ver
```bat
cd frontend && npm run dev
```
Backend + seed necessários para times/campeões reais.

---

## O que foi feito nesta sessão (2026-07-14)

### Backend
1. **Players API enriquecida** (`GET /teams/{id}/players`)
   - age, nationality, championPool, hasRookieClause, participationRate, contractExpirySeasons, teamId, monthlySalary
2. **Calendário**
   - `GET /calendar` retorna `week_calendar`, `day_of_week`, `league_id`
   - `POST /calendar/advance?managed_team_id=`  
     - Auto-simula jogos IA vs IA  
     - Mantém partidas do manager em `scheduled_matches` (interativas)
3. **Mercado**
   - `GET /market/players?exclude_team_id=`
   - `POST /transfers/sign` (debita budget, encerra contrato antigo, cria novo)
4. **Ligas**
   - `GET /leagues`
5. **Live match**
   - Logs normalizados com `message` + `severity`
   - Fase final = `COMPLETE` (compatível com FE)
   - Coach comm retorna `message`
   - Persistência atualiza standings + games_played + cláusula rookie
   - Import `select` corrigido; `model_dump` onde aplicável
6. **Bugfix:** `validate_roster_size()` não aceita mais arg inválido

### Frontend
1. Store com `myPlayers`, `marketPlayers`, `leagueId`, `standings`, `lastAutoResults`
2. `loadData` / `refreshRosterAndMarket` sincronizam API real
3. `advanceDay` passa `managed_team_id`, atualiza calendário/standings/burnout
4. Transferências via API (taxa €250k)
5. Dashboard: elenco do time real, tabela de classificação, resultados IA
6. MatchSimulation: sem hardcode G2/Fnatic; `clearActiveMatch`; vencedor exibido
7. TransferMarket: remove filtro legado `g2-`

### Validação
- Backend: **15/15 testes** passando
- Frontend: **`npm run build`** OK

---

## Fluxo de carreira atual (jogável)

```
Menu → New Game (escolhe time) → Dashboard
  → Avançar Dia (burnout + patch + match day)
  → Outros jogos: auto-sim (standings sobem)
  → Seu jogo: activeMatch DRAFT → Táticas → Snake Draft
  → Submit → Live match (ticks) + Coach Comms
  → COMPLETE → Voltar ao Dashboard (standings/elenco refresh)
  → Mercado: contratar de outros times (orçamento real)
```

---

## Arquivos tocados nesta sessão

```
src/main.py
src/modules/calendar/calendar_service.py
src/modules/simulation/match_engine_service.py
frontend/src/services/api.ts
frontend/src/store/useGameStore.ts
frontend/src/screens/Dashboard.tsx
frontend/src/screens/MatchSimulation.tsx
frontend/src/screens/TransferMarket.tsx
CONTINUIDADE.md  (este arquivo)
```

---

## O que ainda falta (próximas sessões)

### P1 — curto prazo
- [x] Gerar calendário semanal com **eventos reais** do manager (não só template Qua/Sáb)
- [x] Pareamento de liga determinístico (round-robin) em vez de shuffle aleatório
- [x] Pós-live-match: aplicar burnout de MATCH_DAY no elenco do manager
- [ ] Draft: auto-fill do lado RED (IA) quando o manager joga BLUE (hoje o FE controla os 20 turns manualmente)
- [ ] Mapear `primary_role` dos champions no FE (draft picker por role real do seed)
- [ ] Exibir standings também após live match sem depender só de clearActiveMatch
- [x] Playoffs top 6
- [x] Save/load

### P2 — médio prazo
- [x] Modularizar `src/main.py` em routers (`src/api/routes/*`) — **P3-1 feito**
- [x] Save/load de carreira (manager name + team + progresso)
- [x] Renovações de contrato / free agents no offseason
- [x] Playoffs e transição de fase completa na UI
- [ ] Treino / desenvolvimento CA→PA (**P2-3** próximo)
- [ ] Scouting / atributos ocultos (**P2-4**)
- [ ] Migrar warnings Pydantic v2 (`ConfigDict`, lifespan)

### P3 — longo prazo
- [ ] Multi-liga / Worlds
- [ ] Scouting e atributos ocultos revelados por staff
- [ ] Auth JWT (já há `SECRET_KEY` no .env.example)
- [ ] Deploy Postgres+Redis “full mode”

---

## Débitos / armadilhas conhecidas

| Item | Detalhe |
|------|---------|
| MockRedis | Estado live some se o processo uvicorn reiniciar mid-match |
| Live match duration | ~2s real × até 40 min de jogo ≈ ~80s por partida |
| Draft FE | Manager joga o próprio lado; oponente usa DraftAI backend (fallback aleatório se API falhar) |
| Seed drop_all | `POST /db/seed` **apaga** o banco SQLite e invalida saves (UUIDs mudam) |
| Save/Load | JSON em `saves/`; exige o **mesmo** DB/seed em que salvou |
| monólito | ✅ Resolvido — rotas em `src/api/routes/` |
| Times sem academy | Roster mínimo 6 (validate_roster_size); academy = 11 |
| Filter age mercado | FE bloqueia &lt;16; label LEC ainda fala 18 |

---

## Checklist rápido ao retomar

1. Ler este arquivo  
2. `git status` / diff se houver commits novos  
3. Subir backend + seed se o DB estiver vazio  
4. Rodar `pytest` + `npm run build` antes de grandes mudanças  
5. Escolher um item P1 da lista acima  

---

## Contato com a análise inicial

| Prioridade original | Status |
|---------------------|--------|
| P0 Loop carreira (match day → standings) | **Feito (base)** |
| P0 Sync FE↔API (players, pool, mercado, calendário) | **Feito (base)** |
| P1 Transferências backend | **Feito (MVP)** |
| P1 Auto-sim de outros jogos | **Feito** |
| P2 Modularizar API | Pendente |
| P2 Save/load | Pendente |
| P3 Playoffs / offseason profundos | Pendente |
