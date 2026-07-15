# Plano: recuperação de fadiga + draft flex (ordem de role)

**Data:** 2026-07-15  
**Origem:** playtest (alerta de fadiga “grudado” após 2 jogos; picks/bans sempre TOP→JG→MID→BOT)  
**Status:** **implementado** (2026-07-15) — Feature A + B no código e testes  
**Branch alvo:** `main`

---

## 1. Problemas observados no playtest

### P1 — Fadiga que não volta
- Após o 2º game simulado, alerta de fadiga alta aparece e **não some**.
- Hoje a recuperação forte só ocorre em `CalendarDayType.REST` (`BurnoutService`).
- Match day aplica +burnout / +visual / +mental altos; treino e scrim **só somam**.
- Resultado: com poucos DOMs de descanso (ou rest fraco), o elenco acumula fadiga e o hub fica com alerta permanente.

### P2 — Ordem rígida de role no draft
- DraftAI escolhe role pela lista fixa `TOP → JUNGLE → MID → BOT → SUPPORT` (com prioridade só se o oponente já revelou a lane).
- Sensação de “sempre o mesmo roteiro de picks”, pouco realista vs pro play (flex, blind, 2ª pick bot, etc.).
- Meta: **campeão primeiro, role como consequência** — tanto IA quanto jogador.

---

## 2. Estado atual no código (âncoras)

| Área | Arquivo | Notas |
|------|---------|--------|
| Fadiga diária | `src/modules/calendar/burnout_service.py` | REST recupera; demais dias só penalizam |
| Pós-live | `match_engine_service` + form | burn extra em titulares; alertas no FE usam `burnoutMeter` / `visualFatigue` > 70 |
| Config | `src/core/config.py` | `burnout_recovery_per_rest`, `burnout_daily_penalty`, thresholds |
| Draft order (snake) | `src/modules/draft/snake_draft.py` | 20 ações oficiais (ban/pick) — **manter** |
| Escolha de role IA | `src/modules/draft/draft_ai.py` `_decide_pick` | `remaining_roles[0]` = ordem fixa |
| Scout tips | `src/modules/draft/draft_scout.py` | `ROLE_ORDER` similar |
| FE draft | `frontend/src/screens/TacticsDraft.tsx` | validar se UI força role em ordem |

---

## 3. Feature A — Sistema de restauração de fadiga (nuance)

### 3.1 Objetivo
- Fadiga **sobe** com carga (match/scrim/treino intenso).
- Fadiga **desce** com o tempo e com descanso — **nunca** “gruda” em 100% sem saída.
- Qualidade da recuperação depende de: tipo de dia, minutos/role, performance, moral, pressão do board.

### 3.2 Três eixos (já existem no model)
| Eixo | Significado | UI |
|------|-------------|-----|
| `burnout_meter` | desgaste crônico / overload | alerta “burnout” |
| `visual_fatigue` | tela / foco visual | debuff mecânica |
| `mental_fatigue` | estresse / pressão | moral / comms |

Alertas de hub usam **burnout ou visual > 70**. Ambos precisam recuperar.

### 3.3 Regras de recuperação (proposta)

#### Base diária (todo mundo no roster)
Mesmo em TRAINING/SCRIM/MEDIA, aplicar **micro-recuperação passiva** se o jogador **não jogou partida** naquele dia:

| Situação | Δ burnout | Δ visual | Δ mental |
|----------|-----------|----------|----------|
| REST (titular ou reserva) | −base_rest | −base_visual | −base_mental |
| Dia sem match (treino leve) | −1 ~ −2 | −2 ~ −3 | −1 |
| SCRIM (participou) | 0 a +leve | + | +leve |
| MATCH (titular) | +alto | +alto | +médio |
| MATCH (banco / 0 min) | −leve | −leve | −leve / 0 |

Constantes em config (tunáveis), não hardcode espalhado.

#### Multiplicadores de qualidade da recuperação (`recovery_mult` 0.0–1.4)

```
recovery_mult =
  1.0
  × performance_factor   # última nota / forma (FormService)
  × morale_factor        # team_morale + discontent individual
  × pressure_factor      # board confidence / months_under_goal
  × staff_factor         # Performance Coach burnout_recovery_bonus (já existe)
  × intensity_factor     # HARD treino reduz recovery no mesmo dia
```

| Fator | Baixo recovery (pior) | Alto recovery (melhor) |
|-------|----------------------|-------------------------|
| Performance | rating média &lt; 5 ou derrota feia | rating ≥ 7 / vitória |
| Moral | team_morale &lt; 35 ou discontent alto | moral alta, duo ok |
| Pressão board | confidence &lt; 35 ou fired path | confidence ≥ 70 |
| Staff | sem Performance Coach | com coach forte |
| Intensidade | plano HARD no mesmo dia | LIGHT / REST |

**Regra de ouro (nuance pedida):**
- Se o jogador **empenhou mal** (baixa nota) **e** moral/pressão ruins → `recovery_mult` pode ir a **0** no REST (quase não recupera) ou até **subir mental** levemente (“não desliga a cabeça”).
- Se empenhou bem e moral ok → REST recupera **acima** da base (até 1.3×).

#### Pós-partida (já parcial)
- Titulares: spike de fadiga (manter).
- Reservas com discontent: mental sobe (TR-5 já tem direção).
- **Novo:** ao processar ratings, gravar `last_match_rating` no form (já há form) e usar no recovery dos próximos 2–3 dias (decay).

#### Alertas no FE
- Só mostrar alerta se **ainda** > 70 **após** o advance day.
- Na UI do Painel / Elenco: mostrar **tendência** (↓ recuperando / ↑ piorando) se possível.
- Critério de pronto: após 1 REST com recovery_mult ≥ 0.8, atletas em 75% voltam a &lt; 70 em ≤ 2 REST (teste unitário com seed fixo).

### 3.4 Tarefas de implementação (Feature A)

| # | Tarefa | Onde |
|---|--------|------|
| A1 | Extrair tabela de deltas + recovery_mult para funções puras testáveis | `burnout_service.py` ou `fatigue_recovery.py` |
| A2 | Integrar FormService (avg rating) + MoraleService + staff power no REST/dias leves | services |
| A3 | Banco/reserva: não aplicar MATCH_DAY full se `is_starter=False` e não jogou | burnout + match end |
| A4 | Micro-recovery em TRAINING LIGHT / MEDIA; HARD reduz recovery | training plan intensity |
| A5 | Eventos legíveis no advance (`FATIGUE_RECOVERY`, `POOR_RECOVERY`) → feed hub | calendar_service |
| A6 | Testes: REST limpa alerta em N dias; poor form reduz recovery; banco recupera mais | `tests/test_burnout*.py` |
| A7 | FE: badge de fadiga some quando medidores caem; opcional seta de tendência | Squad / Dashboard |

### 3.5 Critérios de pronto (UAT)
- [ ] Após 2 partidas + 1 DOM REST “bom”, alerta some para a maioria do elenco.
- [ ] Após 2 partidas + REST com form ruim + board tenso, recuperação **visívelmente** pior (testes numéricos).
- [ ] Reservas não ficam com fadiga de match se não jogaram.
- [ ] 0 regressão: `pytest tests -q` verde.

---

## 4. Feature B — Draft flex (campeão define role)

### 4.1 Objetivo
Ordem **oficial de turnos** (snake ban/pick) permanece.  
O que muda: **em cada pick**, o time escolhe um campeão e associa a **qualquer role ainda livre**, não a “próxima role da fila TOP→…→SUP”.

Exemplo realista:
- 2º pick da IA: melhor champ disponível no pool do time é **Thresh** → role **SUPPORT**, mesmo com TOP/JG ainda abertos.

### 4.2 Modelo de decisão (IA)

Para cada pick do time:

1. Listar **roles abertas** (sem pick).
2. Para cada role aberta, listar candidatos do **starter daquela role** (MAIN → SECONDARY → meta fallback), filtrar bans/picks.
3. Scorear cada par `(champion, role)`:
   - pool tier (MAIN > SEC > off)
   - counter vs lane inimiga **se** oponente já pickou aquela role
   - patch bias / meta
   - flex value (champ jogável em 2 roles → bônus se ainda há flex futuro)
   - blind risk (1ª/2ª pick: priorizar safe/flex)
4. Escolher **argmax score** (com noise leve para variedade).
5. Retornar `(champion, role_hint)` — **role não precisa ser remaining_roles[0]**.

### 4.3 Jogador (FE)
- Grid de campeões **não** bloqueado a uma role pré-selecionada rígida.
- Ao hover/pick: sugerir roles válidas (primary/secondary do champ + roles livres).
- UI: seletor de role **no momento do lock** (ou auto-assign pela role primária se só 1 livre couber).
- Validação BE: 5 picks, **5 roles distintas**, 1 champ por role.

### 4.4 Bans
- Bans **não** amarram role (já é assim).
- IA de ban pode continuar priorizando MAIN do oponente / meta (opcional: banear flex do oponente).

### 4.5 Tarefas de implementação (Feature B)

| # | Tarefa | Onde |
|---|--------|------|
| B1 | Refatorar `_decide_pick` para score por (champ, role) aberta | `draft_ai.py` |
| B2 | Helper puro `score_flex_options(...)` + testes de ordem não-TOP-first | `tests/test_draft_ai.py` |
| B3 | FE: lock com escolha de role livre; remover fila forçada se existir | `TacticsDraft.tsx` |
| B4 | Alinhar scout tips a “roles abertas” e não ROLE_ORDER fixa | `draft_scout.py` |
| B5 | Counter-matchup / live: já usam role_hint — garantir consistência | `counter_matchup.py` |
| B6 | Playtest: em 10 drafts IA, ≥40% dos 2ºs picks **não** são TOP quando TOP ainda aberto e outro role tem score maior | métrica manual + log |

### 4.6 Critérios de pronto (UAT)
- [ ] IA pode abrir bot/sup no 1º ou 2º pick se score mandar.
- [ ] Jogador consegue pickar Support no 1º pick se quiser.
- [ ] Comp final sempre 5 roles distintas.
- [ ] Snake order de turnos intacto (Blue ban1, …).

---

## 5. Ordem de execução sugerida

```
Sprint FADIGA (1 sessão)
  A1 → A2 → A3 → A4 → A5 → A6 → A7

Sprint DRAFT-FLEX (1 sessão)
  B1 → B2 → B3 → B4 → B5 → B6
```

**Dependências:** nenhuma entre as duas features — podem ser sprints paralelos.  
**Recomendação:** fazer **FADIGA primeiro** (playtest broken alert) e **DRAFT-FLEX** em seguida (imersão).

---

## 6. Fora de escopo (agora)

- Lesões físicas / IR
- Calendário com “bye week” extra
- Fearless draft além do já existente em playoffs
- Rebalance completo de meta de campeões
- Coach mid-game (já descartado)

---

## 7. Referência rápida para a sessão de execução

```bat
set PYTHONPATH=.
venv\Scripts\python -m pytest tests/test_burnout* tests/test_draft* -q
cd frontend && npm test && npm run build
```

Retomar:
1. Este arquivo  
2. `CONTINUIDADE.md`  
3. Playtest com 2 match days + REST e 1 draft observando roles dos picks  

---

*Planejamento salvo para execução futura. Não commitar implementação até o sprint dedicado.*
