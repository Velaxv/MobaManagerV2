# Handoff de sessão — 2026-07-15 (arte menu)

**Status:** Checkpoint local — arte do menu + style bible. Continuar amanhã daqui.  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  

---

## Jogar agora

```bat
run_game.bat
```

Abrir menu principal: deve aparecer war room HQ (mesa holográfica cyan) atrás do card React.

---

## O que foi feito nesta sessão

| Item | Detalhe |
|------|---------|
| **Style bible** | `docs/STYLE_BIBLE.md` — paleta, regras IA vs React, seed de prompt |
| **Key art menu** | 2 gerações + polish `image_edit`; escolhida HQ circular hologram |
| **Assets** | `frontend/public/art/menu-hq-bg.jpg` (ativo), `menu-hq-base.jpg` (ref), `menu-hq-alt.jpg` |
| **MainMenu** | Remove splash Aatrox; layers: art → vignette → ambient → grid → fade esquerdo |
| **Diretrizes** | Arte sem texto/logos; botões/labels só em React; base→edit para consistência |

### Já consolidado (commits anteriores)
FADIGA · DRAFT-FLEX · Nova carreira · War Room UI (`06e0439` e anteriores)

---

## Continuar amanhã (ordem sugerida)

1. Ler `docs/STYLE_BIBLE.md`  
2. Gerar **draft room** ou **mapa blueprint** a partir de `menu-hq-base.jpg` (image_edit)  
3. Integrar no `TacticsDraft` / `MatchSimulation` / `SummonersRiftMap` sem inventar labels na arte  
4. (Opcional) Push deste commit se ainda não estiver no origin  

### Prompt seed (copiar)
```
Style bible Moba Manager:
- esports HQ / FM-like manager aesthetic
- tech-noir glass, deep navy/black, cyan accent, orange highlight
- rim light ciano, glow sutil, ambient low-key
- AAA game key art, sharp, clean, cinematic
- no readable text, no fake UI buttons, no logos
- no copyrighted maps or brand marks
```

---

## Backlog livre (não arte)
- MK-2 cláusulas ricas  
- OR-3 facility tree granular  
- Som sutil (mute default)  
- Desafiante tier-2  
- Playtest UAT fadiga + draft flex  

---

## Explicitamente fora
- Coach mid/late · Tutorial · Desafiante / i18n / som  

---

*Retomar: este arquivo + `CONTINUIDADE.md` + `STYLE_BIBLE.md` + `run_game.bat`.*
