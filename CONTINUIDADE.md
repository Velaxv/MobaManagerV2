# Continuidade — Moba Manager / LoL Manager

**Última atualização:** 2026-07-15 (noite) — checkpoint arte menu + style bible  
**Branch:** `main`  
**Remote:** https://github.com/Velaxv/MobaManagerV2.git  

### Retomar amanhã
1. [`docs/HANDOFF_SESSAO.md`](docs/HANDOFF_SESSAO.md)  
2. [`docs/STYLE_BIBLE.md`](docs/STYLE_BIBLE.md) — bible visual + workflow de arte  
3. `run_game.bat` → conferir tela de **menu principal** com HQ art  

### Entregue nesta sessão (arte)
- Style bible em `docs/STYLE_BIBLE.md` (cyan/orange/navy, sem texto na IA, base→edit)  
- Pack menu em `frontend/public/art/`:
  - `menu-hq-bg.jpg` — fundo ativo do Main Menu  
  - `menu-hq-base.jpg` — referência para `image_edit` (mesma HQ)  
  - `menu-hq-alt.jpg` — variação cyberpunk (backup)  
- `MainMenu.tsx` — key art + vinheta/legibilidade; UI em React  

### Já no histórico (sessão anterior)
- FADIGA · DRAFT-FLEX · Nova carreira · War Room UI  
- Commit base: `06e0439`  

### Próximo passo sugerido (arte)
1. **Draft room** — variação da HQ a partir de `menu-hq-base.jpg`  
2. **Mapa blueprint** live (fantasy/wireframe, não Rift oficial)  
3. Loading / splash 16:9  

### Não feito (de propósito)
- Coach mid/late · Tutorial · Som / i18n · Desafiante  

### Como rodar
```bat
run_game.bat
```

### Stack
Backend FastAPI + SQLite + MockRedis · Frontend React/Vite/Tailwind · seed CBLOL 2026  
