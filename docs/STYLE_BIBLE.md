# Moba Manager — Style Bible (Visual)

Fonte da verdade para arte de fundo, key art e mood. UI com texto legível fica em React (HTML/CSS), não na imagem gerada.

## Identidade

| Eixo | Direção |
|------|---------|
| Gênero visual | Esports HQ / management sim (FM-like) + tech-noir |
| Mood | Mesa de guerra digital, data-rich, cinematic, sem gacha |
| Materiais | Navy profundo, preto, vidro fosco, metal escuro |
| Acentos | Electric cyan `#22d3ee` · neon orange `#f97316` · branco limpo |
| Luz | Rim light ciano, LEDs laranja sutis, low-key, haze volumétrico |
| Qualidade alvo | AAA production key art / concept art polido |

## O que a IA gera

- Backgrounds de tela (menu, HQ, loading, splash)
- Ambientação de sala (war room, training bay, draft room)
- Mapas **estilizados** (blueprint / holograma fantasy, não Rift oficial)
- Portraits genéricos de staff (fictícios)

## O que o código gera

- Títulos, botões, labels, badges, tabelas
- HUD, draft board com picks reais, standings
- Ícones Lucide, crests de org, radar de atributos

## Regras de geração

1. **Sem texto** na arte (nem “fake UI” com palavras).
2. **Sem logos** reais (Riot, orgs, marcas).
3. **Sem mapa copyrighted** 1:1 — use arena fantasy / wireframe abstrato.
4. **Espaço negativo** para overlay React (menu: terço esquerdo / centro mais escuro).
5. **Consistência:** 1 base por cenário → `image_edit` para variações.
6. **Paleta travada:** cyan + orange + navy/black; evitar arco-íris neon genérico.

## Prompt seed (colar em todo pedido de arte)

```
Style bible Moba Manager:
- esports HQ / FM-like manager aesthetic
- tech-noir glass, deep navy/black, cyan accent, orange highlight
- rim light ciano, glow sutil, ambient low-key
- AAA game key art, sharp, clean, cinematic
- no readable text, no fake UI buttons, no logos
- no copyrighted maps or brand marks
```

## Assets de menu (v1)

| Arquivo | Uso | Ratio | Base |
|---------|-----|-------|------|
| `frontend/public/art/menu-hq-bg.jpg` | Fundo Main Menu | 16:9 | War room HQ + mesa holográfica |
| `frontend/public/art/menu-hq-base.jpg` | Referência para edits futuros | 16:9 | Mesma geração base |

## Workflow para próximas telas

1. Gerar/editar a partir de `menu-hq-base.jpg` quando a cena for a mesma HQ.
2. Pedir só a camada de arte (bg), nunca a tela completa com botões.
3. Integrar com `bg-cover` + gradiente `lol-void` por cima para legibilidade.
4. Revisar no jogo real (contraste dos botões cyan/orange).

## Aspect ratios

| Uso | Ratio |
|-----|-------|
| Menu / splash / banners | 16:9 |
| Ícones / avatares | 1:1 |
| Mobile / story | 9:16 |
| Mapa tático top-down | 1:1 ou 4:3 |
