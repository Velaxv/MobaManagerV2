# Relatório de Melhorias e Continuidade — Moba Manager / LoL Manager

**Data:** 2026-07-14  
**Objetivo:** guiar as próximas sessões de desenvolvimento com prioridades claras, dependências e critérios de “pronto”.  
**Complementa:** `docs/RELATORIO_ESTADO_ATUAL.md` e `CONTINUIDADE.md`

---

## 1. Princípios para continuar

1. **Não quebrar o vertical slice** — dia → draft → live → standings deve sempre rodar após mudanças.  
2. **Dados CBLOL primeiro** — evitar reintroduzir times/mercados de fora da liga sem decisão explícita.  
3. **UI já está madura o suficiente** — priorizar sistemas e profundidade de manager; polish pontual só onde faltar clareza.  
4. **Commits pequenos e jogáveis** — cada PR deve deixar `pytest` + `npm run build` verdes.  
5. **Seed é a fonte da verdade de conteúdo** — alterações de elenco/times em `src/shared/cblol_2026_data.py`.

---

## 2. Visão de produto (próximos 3 marcos)

| Marco | Nome | Resultado para o jogador |
|-------|------|---------------------------|
| **M1** | Temporada que fecha | Playoffs, campeão, offseason mínimo, recomeço de split |
| **M2** | Carreira que persiste | Save/load local, multi-sessão sem perder progresso |
| **M3** | Manager profundo | Finanças, contratos, scouting, treino e mercado realistas |

Enquanto M1–M2 não existem, o jogo é um **demo loop** excelente, não ainda um *career game* completo.

---

## 3. Backlog priorizado

### P0 — Crítico (estabilidade e loop)

| ID | Melhoria | Por quê | Esforço | Critério de pronto |
|----|----------|---------|---------|-------------------|
| P0-1 | **Commit / versionar** as mudanças locais desta sessão | Continuidade em outra máquina/sessão | Baixo | `git status` limpo ou PR aberta |
| P0-2 | **Burnout pós-live-match** no elenco do manager | Match day real sem consequência de forma | Médio | ✅ Feito (2026-07-14) — titulares + refresh no hub |
| P0-3 | **Sincronizar calendário visual com a SM** | Grade semanal ainda é template | Médio | ✅ Feito (2026-07-14) — `week_calendar.py` + adversário RR no hub |
| P0-4 | **Pareamento determinístico (round-robin)** | Shuffle aleatório quebra sensação de liga | Médio | ✅ Feito (2026-07-14) — `round_robin.py` + dispatch |
| P0-5 | **Velocidade configurável da live** | ~80s por partida cansa em playtest | Baixo | ✅ Feito (2026-07-14) — 1x/2x/4x/instant + mid-match |

### P1 — Alto valor de gameplay

| ID | Melhoria | Por quê | Esforço | Critério de pronto |
|----|----------|---------|---------|-------------------|
| P1-1 | **Playoffs** (top 6, chave, BO) | Split sem desfecho | Alto | ✅ Feito (2026-07-14) — bracket Redis, QF/SF/Final, campeão + prize |
| P1-2 | **Offseason / renovação** | Contratos e rookies só fazem sentido com ciclo | Alto | ✅ Feito (2026-07-14) — renovar/liberar + novo split |
| P1-3 | **Save / Load de carreira** | Sem isso cada sessão recomeça do zero | Alto | ✅ Feito (2026-07-14) — JSON em `saves/` + API career |
| P1-4 | **Draft adversário via backend DraftAI** | Hoje IA do FE é fraca vs motor real | Médio | Picks RED/blue AI usam `/` serviço backend |
| P1-5 | **Táticas pré-partida** | Manager sem decisões além do draft | Médio | Lineup starters, style Early/Mid/Late, comms default |
| P1-6 | **Resultados da rodada no hub** | Contexto da liga | Baixo | ✅ Feito (2026-07-14) — lista completa + ver log |

### P2 — Gestão e profundidade

| ID | Melhoria | Por quê | Esforço | Critério de pronto |
|----|----------|---------|---------|-------------------|
| P2-1 | **Finanças reais** (salários, receita, multas) | Budget hoje é quase cosmético | Alto | Fluxo mensal e falência / corte |
| P2-2 | **Negociação de transferência** | Taxa fixa €250k é MVP | Médio | Oferta, contra-oferta, salário, duração |
| P2-3 | **Treino e desenvolvimento** (CA→PA) | Sem progressão de elenco | Alto | Treino por role; CA sobe com uso/treino |
| P2-4 | **Scouting / atributos ocultos** | Consistency e BMA existem mas não brilham | Médio | Staff revela atributos com tempo |
| P2-5 | **Academy e subidas** | Rookies existem mas pouco usados | Médio | Promover reserva, cláusula rookie na UI |
| P2-6 | **Patches jogáveis** | Patch meta no seed pouco visível | Médio | Tela de patch + impacto em draft/recomendação |

### P3 — Arquitetura e qualidade

| ID | Melhoria | Por quê | Esforço | Critério de pronto |
|----|----------|---------|---------|-------------------|
| P3-1 | **Modularizar `main.py`** em routers | Manutenção e testes de API | Médio | `api/calendar.py`, `matches.py`, `teams.py`, `seed.py` |
| P3-2 | **Testes de integração API** (httpx) | Unitários não cobrem seed→advance→match | Médio | Suite seed + advance + standings verde |
| P3-3 | **Testes frontend** (Vitest) store + componentes chave | UI quebra sem rede de segurança | Médio | Testes do store e mapeamento de players |
| P3-4 | **Pydantic v2 / lifespan FastAPI** | Warnings e deprecações | Baixo | Zero warnings nos testes |
| P3-5 | **Redis real opcional sem mock frágil** | Live match over restarts | Médio | Persistência AOF/dev com fallback documentado |
| P3-6 | **CI (GitHub Actions)** | Qualidade em todo push | Médio | pytest + npm build no CI |

### P4 — Conteúdo e polish (quando o core estiver sólido)

| ID | Melhoria |
|----|----------|
| P4-1 | Ícones oficiais de role (assets estáticos vs SVG atual) |
| P4-2 | Cores/crest por org CBLOL (brand kit simplificado) |
| P4-3 | Narração de partida mais rica (templates por evento) |
| P4-4 | Som sutil de lock-in / victory (opcional, mute default) |
| P4-5 | Circuito Desafiante como pool de mercado tier-2 |
| P4-6 | Multi-liga / Worlds (longo prazo) |
| P4-7 | Localização EN (i18n) |
| P4-8 | Tutorial interativo na primeira carreira |

---

## 4. Roadmap sugerido por sprints

### Sprint A — “Liga de verdade” (1–2 sessões)
1. P0-4 Round-robin  
2. P0-3 Calendário visual = SM  
3. P0-2 Burnout pós-live  
4. P0-5 Velocidade da live  

**Entrega:** jogar 7 semanas com sensação de campeonato real.

### Sprint B — “Fim de split” (2–3 sessões)
1. P1-1 Playoffs  
2. P1-6 Resultados da rodada  
3. P1-4 DraftAI backend no fluxo interativo  

**Entrega:** coroar um campeão CBLOL na carreira.

### Sprint C — “Carreira salva” (2 sessões)
1. P1-3 Save/Load  
2. P1-2 Offseason mínimo (renovar/liberar + reset standings)  
3. P0-1 Higiene de git/release notes  

**Entrega:** fechar o jogo e reabrir no dia seguinte sem seed.

### Sprint D — “Manager” (3+ sessões)
1. P2-1 Finanças  
2. P2-2 Transferências profundas  
3. P2-3 Treino/desenvolvimento  
4. P3-1 Modularizar API  

**Entrega:** decisões econômicas e de elenco com peso.

---

## 5. Melhorias técnicas detalhadas (guia de implementação)

### 5.1 Round-robin e calendário
- Gerar matriz de confrontos no seed (`league_fixtures` table)  
- `CalendarService._dispatch_match_day` consome fixture da rodada, não shuffle  
- FE: `week_calendar` montado a partir de fixtures do manager  

### 5.2 Save/Load (proposta simples)
- Endpoint `POST /career/save` e `GET /career/load`  
- Payload: `{ managerName, teamId, leagueState, calendarRedisSnapshot, seedVersion }`  
- Arquivo local `saves/career_01.json` **ou** tabela `careers` no SQLite  
- Ao load: restaurar SM no Redis mock + rehydrate Zustand  

### 5.3 Playoffs
- Ao fim da regular season (SM já tem transição), gerar bracket top 6  
- Série BO3/BO5 no mesmo motor live ou batch  
- Prize pool já modelado em `League` — usar  

### 5.4 Modularização da API
```
src/api/
  deps.py
  routes/
    calendar.py
    teams.py
    matches.py
    market.py
    seed.py
  schemas/
```
`main.py` só cria app + include_router.

### 5.5 Live match performance
- Parâmetro `tick_ms` no start live (default 2000, opções 500/1000/0)  
- Ou endpoint `simulate-to-end` para skip  

---

## 6. Riscos e mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Seed destrutivo apaga progresso | Alto | Save antes; seed só em dev explícito |
| MockRedis perde live mid-match | Médio | Aviso na UI; tick mais rápido; opcional Redis real |
| Draft AI FE diverge do backend | Médio | Unificar no backend (P1-4) |
| Scope creep de UI | Médio | Congelar visual hub/draft/live; focar sistemas |
| Data Dragon offline | Baixo | Fallback já existe (iniciais); cache local futuro |
| Balanceamento “pay-to-win” de budget | Baixo | Caps de roster e fair play financeiro (P2-1) |

---

## 7. Checklist de sessão (copiar a cada retomada)

```
[ ] Ler docs/RELATORIO_ESTADO_ATUAL.md (5 min)
[ ] Ler esta lista P0/P1 e escolher 1–2 itens
[ ] git status / branch
[ ] Backend sobe? Seed atualizado?
[ ] pytest + npm run build
[ ] Implementar
[ ] Playtest manual do loop core
[ ] Atualizar CONTINUIDADE.md com o que mudou
[ ] Commit com mensagem clara
```

---

## 8. Métricas de sucesso do projeto

| Métrica | Alvo de curto prazo |
|---------|---------------------|
| Tempo até primeira partida na nova carreira | &lt; 3 minutos |
| Duração playable de um split completo | 1 sessão de 45–90 min |
| Testes backend | ≥ 25 (incluir integração) |
| Crashes no loop core | 0 em playtest de 1 split |
| Saves funcionais | ≥ 1 slot local estável |

---

## 9. O que **não** priorizar agora

- Multiplayer / ranked online  
- 3D / replay cinematográfico  
- Todas as ligas mundiais  
- Auth OAuth  
- Mobile nativo  
- Microtransações / gacha (fora da visão do projeto)

---

## 10. Ordem recomendada para a **próxima** sessão

**Concluído nesta sessão (2026-07-14):** P0-5, P0-2, P0-4.

Próximo foco sugerido:
1. **P0-3** Calendário visual = fixtures do round-robin (mostrar adversário do manager na grade)  
2. **P1-1** Playoffs (top 6)  
3. **P1-3** Save/Load (schema JSON de carreira)  
4. **P0-1** Commit das mudanças locais

---

## 11. Referência rápida de arquivos-chave

| Área | Arquivo |
|------|---------|
| Seed CBLOL | `src/shared/cblol_2026_data.py` |
| API | `src/main.py` |
| Calendário | `src/modules/calendar/calendar_service.py` |
| Live match | `src/modules/simulation/match_engine_service.py` |
| Draft UI | `frontend/src/screens/TacticsDraft.tsx` |
| Live UI | `frontend/src/screens/MatchSimulation.tsx` |
| Hub shell | `frontend/src/components/GameShell.tsx` |
| Store | `frontend/src/store/useGameStore.ts` |
| Wizard | `frontend/src/screens/NewGameWizard.tsx` |

---

*Documento vivo: atualizar a seção 3 (status das linhas P0/P1) a cada sprint concluído.*
