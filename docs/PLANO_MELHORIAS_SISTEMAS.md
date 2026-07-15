# Plano de melhorias por sistema — Moba Manager

**Data:** 2026-07-14  
**Objetivo:** orientar o próximo ciclo de desenvolvimento com base no estado real do código + referências de design de *management sims* e esports.  
**Complementa:** `RELATORIO_MELHORIAS_CONTINUIDADE.md`, `RELATORIO_ESTADO_ATUAL.md`, `CONTINUIDADE.md`

---

## 1. Resumo executivo

O projeto já passou do “vertical slice demo” e tem **carreira completa em MVP**: calendário, draft, live+Rift, playoffs BO, save, finanças, treino, scouting, academy, staff, org (board/sponsors/facility), moral/scrim/VOD.

O gargalo agora **não é “falta de sistema”** — é **profundidade, feedback e acoplamento** entre sistemas que já existem.

| Camada | Maturidade | Problema principal |
|--------|------------|-------------------|
| Loop core (dia→draft→live→tabela) | ★★★★☆ | Estável; live ainda “aleatória por role” |
| Match engine + Rift UI | ★★★☆☆ | Mapa rico; simulação ainda pouca memória de estado |
| Draft / meta / patch | ★★★☆☆ | Patch e scout existem; pouco impacto acumulado |
| Gestão (treino, mercado, finanças) | ★★★☆☆ | Regras MVP; poucas decisões difíceis |
| Org / board / moral | ★★☆☆☆ | Estado em Redis; pouco drama narrativo |
| Persistência / infra | ★★★☆☆ | Save JSON OK; MockRedis frágil; FE sem testes |

**Direção recomendada (próximos 3 marcos):**

1. **Motor que “lembra” a partida** — estado de mapa/lanes/objetivos no tick, não só ouro+kills.  
2. **Decisões de manager com trade-off** — treino, scrim, lineup e contratos com custo real.  
3. **Carreira que cobra** — board, mídia, forma e reputação como pressão contínua.

---

## 2. O que o código tem hoje (auditoria)

### 2.1 Competição e calendário
- Round-robin, calendário semanal, playoffs top 6, séries BO3/BO5, fearless, momentum.  
- Offseason + free agents + janela de mercado.  
- **Gap:** pouco “storytelling de liga” (rivalidades, forma recente exibida, previsão de chave).

### 2.2 Draft
- Snake draft, DraftAI backend, analyzer de comp, scout de dicas, patch notes + bias.  
- **Gap:** bans/picks pouco amarrados a *pool real do jogador*; pouca punição por comp sem wincon; sem “draft history” entre maps de série além de fearless.

### 2.3 Match engine (live)
- Ticks early/mid/late; duelos por role aleatória; objetivos mid/late; coach comms; estilos EARLY/MID/LATE/BALANCED.  
- Minimapa Rift v2: posições, trilhas, wards, torres/inhib/nexus derivados de eventos.  
- **Gap crítico:**  
  - Early = 1 role/tick aleatória (não 5 lanes em paralelo).  
  - Vitória por gold diff ou “timeout 40 min” — pouco snowball estrutural (torres no motor real vs só no mapa FE).  
  - Estilo de jogo = viés de ouro sutil, não plano tático legível.  
  - Pós-partida: pouco relatório de performance por jogador (rating / notes).

### 2.4 Elenco e atributos
- CA/PA, mechanics, focus, resilience, coachability, teamwork.  
- Ocultos: consistency, big_match_aptitude.  
- Burnout / fadiga visual e mental.  
- **Gap:** champion_pool pouco usado como *restrição de draft*; sinérgias duo (bot/jg-mid) existem na moral mas pouco no motor.

### 2.5 Treino / prática
- Foco + intensidade; XP em treino/scrim/match; scrim, VOD, moral/chemistry.  
- **Gap:** plano semanal “set and forget”; sem individualização forte; pouco feedback “X melhorou mechanics +1”.

### 2.6 Mercado e contratos
- Valuation, oferta/contra, FA, staff hire/fire.  
- **Gap:** sem cláusulas ricas (release, no-trade, role guarantee); IA de outros times fraca no mercado; pouca escassez de talentos por role.

### 2.7 Finanças e org
- Folha mensal, receita, sponsors, facility 1–3, board confidence + demissão.  
- **Gap:** board reage pouco entre splits; sponsors pouco “contrato com meta”; facility sem árvore de upgrades granular.

### 2.8 Save / infra
- Save JSON local; API modular; CI pytest+build.  
- **Gap:** estado Redis (live, moral, org, training plan) some no restart; sem Vitest; seed destrutivo.

---

## 3. Referências de design (pesquisa)

### 3.1 Management sims (Football Manager e similares)

Padrões que definem “sensação de manager de verdade”:

| Pilar | Como FM / peers fazem | Aplicação no Moba Manager |
|-------|----------------------|---------------------------|
| **Atributos + contexto** | CA/PA + forma + moral + adequação tática | Ampliar: forma 5 jogos, rating pós-partida, fit com estilo |
| **Decisões com custo** | Treino intenso cansa; rotação evita lesão/burnout | Intensidade HARD já cansa — tornar burnout *visível e crítico* no draft/live |
| **Board / expectativas** | Metas sazonais + paciência | Board já existe — avaliar **semanalmente** e gerar eventos |
| **Match engine legível** | Highlights + ratings + “por que perdemos” | Relatório pós-partida + heatmap mental de lanes |
| **Mercado assimétrico** | Scouting revela, não mostra tudo | Já há máscara — amarrar à **confiança de scouting no valor de transferência** |
| **Feedback loop curto** | Após cada jogo o elenco “reage” | Moral já reage — adicionar interviews / locker room 1-liners |

Fontes conceituais: documentação e ecossistema de *sports management sims* (Sports Interactive / FM): profundidade vem de **muitos sistemas rasos bem acoplados**, não de um motor perfeito isolado.

### 3.2 Realidade do LoL esports (sistemas de produto)

| Tema real | Mecânica de jogo |
|-----------|------------------|
| **Patch redefine meta** | Tier list por patch → draft bias + valor de pool |
| **BO e fearless** | Já no playoff — expandir “draft adaptativo” entre maps |
| **Contratos e academy** | Promote/demote + development league (Desafiante) |
| **Staff (coach, analyst, scout)** | Já hire — dar **poderes distintos** no motor (não só labels) |
| **Forma e superteam chemistry** | Chemistry/duo synergy → modificadores mid/late |
| **Sponsors / org brand** | Receita atrelada a standings e redes sociais (simplificado) |

### 3.3 Princípios de design para o nosso escopo

1. **Todo sistema deve alterar o match** ou o **dinheiro/reputação** — senão vira checklist.  
2. **Mostrar a consequência em ≤1 tela** (feed, relatório, KPI do hub).  
3. **Preferir aprofundar 1 pipeline** (ex.: early game 5 lanes) a adicionar 3 telas novas.  
4. **Persistir estado de carreira no save**, não só no Redis.  
5. **Manter CBLOL-first** — profundidade local antes de multi-liga.

---

## 4. Melhorias por sistema (priorizadas)

Legenda de esforço: **P** pequeno (≤1 sessão) · **M** médio (1–2) · **G** grande (3+)  
Impacto: **A** alto · **B** médio · **C** baixo/polish

### A. Match engine + Rift (maior ROI de imersão)

| ID | Melhoria | Esforço | Impacto | Notas de implementação |
|----|----------|---------|---------|------------------------|
| **ME-1** | **Estado de partida no backend** (gold/towers/dragons já existem; adicionar `lane_pressure[5]`, `turrets_alive` real, `vision_score`) | M | A | ✅ 2026-07-14 — `map_structures`, `lane_pressure`, vision no LiveMatchState |
| **ME-2** | **Early paralelo** — resolver TOP/JG/MID/BOT+SUP no mesmo tick com pesos | M | A | ✅ 2026-07-14 — 5 roles/tick; highlight do maior impacto |
| **ME-3** | **Win conditions** — aces, open nexus, elder; não só gold@40 | M | A | ✅ 2026-07-14 — `win_reason` (SNOWBALL/NEXUS/TIME_LIMIT/…) |
| **ME-4** | **Player ratings pós-partida** (0–10) por kills/objetivos/burnout | M | A | ✅ 2026-07-14 — `player_ratings` + UI victory |
| **ME-5** | **Chemistry/duo no motor** — bot_synergy e jg_mid_synergy como mult | P | A | ✅ 2026-07-14 — MoraleService → duel bonus |
| **ME-6** | **Coach comms mid/late** limitados (timeout call / engage) | M | B | Expande só-early |
| **ME-7** | Rift: objetivo contest bar, torre HP, mini-feed no mapa | P | B | UI sobre estado ME-1 |
| **ME-8** | Narração com templates (pickoff, 2v2 river, siege) | M | B | P4-3 do backlog antigo |

### B. Draft e meta

| ID | Melhoria | Esforço | Impacto |
|----|----------|---------|---------|
| **DR-1** | **Champion pool por jogador** restringe comfort picks (off-role penalty) | M | A | ✅ 2026-07-14 — penalty live + UI draft |
| **DR-2** | Counter-pick score no analyzer → dica de scout + mult no early | M | A |
| **DR-3** | Blind vs flex: priorizar flex picks na DraftAI | M | B |
| **DR-4** | Histórico de drafts do split (UI + IA aprende “frequência”) | G | B |
| **DR-5** | Patch mid-split automático (16.x → 16.y) com transição de meta | M | A |

### C. Treino, forma e elenco

| ID | Melhoria | Esforço | Impacto |
|----|----------|---------|---------|
| **TR-1** | **Forma (last 5 ratings)** exibida no elenco e no hub | M | A | ✅ 2026-07-14 — FormService + Squad |
| **TR-2** | Plano de treino **por role** (não só global) | M | B |
| **TR-3** | Individual training: “focus player of the week” | P | B |
| **TR-4** | Declínio de PA/CA por idade / burnout crônico | M | B |
| **TR-5** | Match XP só se minutes/role jogados (já parcial) + bench discontent | P | A | ✅ 2026-07-14 — discontent + fadiga mental |

### D. Mercado e staff

| ID | Melhoria | Esforço | Impacto |
|----|----------|---------|---------|
| **MK-1** | IA de times rivais faz 1–2 moves na janela | M | A |
| **MK-2** | Cláusulas: duração, salário, buyout, role starter promise | M | A |
| **MK-3** | Staff powers: Head Coach → coach comms; Analyst → draft tips; Scout → speed | P | A | ✅ 2026-07-14 — power no motor + UI |
| **MK-4** | Free agents com personalidade (ambitious / loyal) | M | B |
| **MK-5** | Pool Desafiante (tier-2) | G | B |

### E. Finanças, board, org

| ID | Melhoria | Esforço | Impacto |
|----|----------|---------|---------|
| **OR-1** | Board review **semanal** + e-mail no hub | M | A | ✅ 2026-07-14 — weekly_board_review + card hub |
| **OR-2** | Sponsors com metas (top 4 / views proxy = wins) | M | B |
| **OR-3** | Facility tree (scrim / analytics / recovery separados) | M | B |
| **OR-4** | Prize split + salary cap soft (fair play) | M | B |
| **OR-5** | Game over / re-employment flow (não só “fired”) | M | B |

### F. Persistência e qualidade

| ID | Melhoria | Esforço | Impacto |
|----|----------|---------|---------|
| **IN-1** | **Save inclui Redis snapshots** (moral, org, live mid-match opcional) | M | A |
| **IN-2** | Redis real opcional (docker) documentado | M | B |
| **IN-3** | Vitest: store + `riftMap` pure functions | M | A |
| **IN-4** | Seed não destrutivo / “new career” explícito | M | A |
| **IN-5** | Tutorial 1ª carreira (3 tooltips) | P | B |

---

## 5. Roadmap sugerido (sprints)

### Sprint E — “Partida que conta” (recomendado agora)
Foco: motor + feedback. Entrega: o jogador entende *por que* ganhou/perdeu.

1. **ME-5** Chemistry no duel (quick win)  
2. **ME-1** Torres/lanes no `LiveMatchState` (fonte da verdade do Rift)  
3. **ME-2** Early paralelo 5 roles  
4. **ME-4** Ratings pós-partida + UI no victory overlay  
5. **ME-3** Win reasons  

**Critério de pronto:** 1 playtest de BO/partida regular com relatório legível; torres iguais no BE e no mapa.

### Sprint F — “Manager de verdade”
1. **TR-1** Forma  
2. **MK-3** Staff powers  
3. **TR-5** Bench discontent  
4. **OR-1** Board semanal  
5. **DR-1** Champion pool no draft  

**Critério:** decisões fora do draft mudam resultado de forma mensurável em testes.

### Sprint G — “Carreira estável”
1. **IN-1** Save completo  
2. **IN-3** Vitest  
3. **IN-4** Seed seguro  
4. **MK-1** IA de mercado  
5. **DR-5** Patch mid-split  

### Sprint H — “Conteúdo / polish” (quando F+G estáveis)
- Brand kit orgs, narração rica, Desafiante, i18n, tutorial, som.

---

## 6. Dependências e riscos

```
ME-1 (estado BE) ──► ME-7 (UI Rift fiel) ──► ME-3 (winconds)
ME-2 ──► ME-4 (ratings melhores)
ME-4 ──► TR-1 (forma) ──► MK-2 (valuation por forma)
MK-3 ──► DR-2 / coach comms
IN-1 ──► qualquer feature Redis (senão playtest quebra)
```

| Risco | Mitigação |
|-------|-----------|
| Scope creep no motor | Congelar UI hub; só victory + Rift |
| Balance “meta fixa” | Multiplicadores em tabela/config, não hardcode espalhado |
| Redis some no restart | IN-1 antes de mais estado em Redis |
| Seed apaga save | IN-4 + aviso na UI |

---

## 7. Métricas de sucesso (próximo ciclo)

| Métrica | Alvo |
|---------|------|
| Playtest 1 split completo sem crash | 100% |
| Jogador verbaliza “perdi por X” sem olhar código | ≥70% dos playtests |
| Dec de winrate entre style matchup (early vs late) | 5–15% (não 0 nem 50%) |
| Testes backend | ≥ 140 |
| Vitest pure functions (`riftMap`, ratings) | ≥ 15 cases |
| Save/load round-trip moral+org+standings | 100% |

---

## 8. O que **não** fazer agora

- Multi-liga / Worlds (P4-6)  
- Multiplayer / ranked  
- Motor frame-a-frame estilo cliente LoL  
- Auth / cloud save  
- Assets oficiais Riot (licença) — manter estilização própria  
- Reescrever frontend do zero  

---

## 9. Decisão de produto (para a próxima sessão)

**Pergunta central:** priorizar **profundidade de partida (Sprint E)** ou **pressão de carreira (Sprint F)**?

| Opção | Escolha se… |
|-------|-------------|
| **E — Partida** | Playtest reclama que “live é barulho de ouro” / mapa bonito mas vazio |
| **F — Manager** | Loop de partida já diverte e falta peso entre jogos |
| **Híbrido** | ME-5 + ME-4 + TR-1 em uma sessão (quick wins transversais) |

**Recomendação do research:** começar por **híbrido curto** (ME-5, ME-4, chemistry, ratings) e em seguida **ME-1/ME-2** — maximiza sensação de “jogo de LoL” sem abandonar o manager.

---

## 10. Checklist de planejamento (copiar)

```
[ ] Escolher Sprint E / F / Híbrido
[ ] Listar 3 IDs no máximo por sessão
[ ] Critério de pronto jogável escrito
[ ] pytest + npm run build verdes
[ ] Atualizar CONTINUIDADE.md + este doc (status das linhas)
[ ] Playtest 15–30 min e anotar em HANDOFF_SESSAO.md
```

---

*Documento vivo. Atualizar a seção 4 (status ✅) a cada sprint.*
