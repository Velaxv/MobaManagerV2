# -*- coding: utf-8 -*-
"""
Narração de partida com templates (Sprint H / ME-8 / P4-3).

Gera descrições legíveis e variadas a partir de tipo de evento + contexto.
Sem assets de voz — só texto no feed live.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


def _pick(rng: random.Random, options: List[str]) -> str:
    return rng.choice(options) if options else ""


def narrate(
    event_type: str,
    *,
    minute: int = 0,
    role: Optional[str] = None,
    side: Optional[str] = None,
    actor: Optional[str] = None,
    victim: Optional[str] = None,
    champion: Optional[str] = None,
    team_name: Optional[str] = None,
    location: Optional[str] = None,
    extra: Optional[str] = None,
    seed: Optional[int] = None,
) -> str:
    """
    Retorna uma linha narrativa em PT-BR.
    """
    rng = random.Random(seed if seed is not None else f"{event_type}:{minute}:{actor}:{victim}")
    et = (event_type or "").upper()
    role_tag = f"[{role}] " if role else ""
    who = actor or "um jogador"
    foe = victim or "o oponente"
    side_label = "Blue" if (side or "").upper() == "BLUE" else "Red" if (side or "").upper() == "RED" else (side or "time")
    team = team_name or side_label
    loc = location or "no mapa"
    champ = champion or "seu campeão"

    templates: Dict[str, List[str]] = {
        "SOLO_KILL": [
            f"{role_tag}{who} isola {foe} e fecha o 1v1 com frieza.",
            f"{role_tag}Solo kill! {who} pune o erro de {foe} e abre vantagem de rota.",
            f"{role_tag}{who} ganha o all-in contra {foe} — pressão imediata na lane.",
            f"{role_tag}Troca suja vira kill: {who} abate {foe} e reset de wave.",
        ],
        "FARM": [
            f"{role_tag}{who} prioriza farm e escala com segurança.",
            f"{role_tag}Wave control: {who} congela e nega CS.",
        ],
        "TURRET_DESTROYED": [
            f"{team} derruba a torre {loc} e abre o mapa.",
            f"Torre cai! {team} converte pressão em estrutura {loc}.",
            f"Siege bem-sucedido — {team} remove a defesa {loc}.",
        ],
        "DRAGON_SECURED": [
            f"{team} assegura o Dragão e soma stack de alma.",
            f"Objetivo neutro: {team} pega o Dragão com vision control.",
            f"Smite timing — {team} sai com o Dragão.",
        ],
        "BARON_SECURED": [
            f"BARON! {team} garante o buff e prepara o siege final.",
            f"{team} rouba o ritmo com Baron Nashor — janela de fim de jogo.",
            f"Controle de visão no poço: {team} fecha o Baron.",
        ],
        "HERALD_SECURED": [
            f"{team} pega o Arauto para empurrar torre.",
            f"Arauto em mãos de {team} — pressão de estrutura a caminho.",
        ],
        "TEAMFIGHT": [
            f"Teamfight em {loc}: {team} sai na frente e limpa a wave.",
            f"Caos no meio do rio — {team} vence o 5v5.",
            f"Engage limpo de {team} decide a luta em {loc}.",
        ],
        "PICKOFF": [
            f"Pickoff! {who} pega {foe} fora de posição.",
            f"Visão pune: {team} abate {foe} em rotação.",
        ],
        "SIEGE": [
            f"{team} monta siege em {loc} com wave grande.",
            f"Pressão de torre: {team} força o recall inimigo.",
        ],
        "SNOWBALL": [
            f"Snowball de {team} — ouro e objetivos em cascata.",
            f"{team} acelera o jogo; oponente sem tempo de scale.",
        ],
        "ACE": [
            f"ACE! {team} limpa o time rival e marcha para o nexus.",
            f"Wipe total — {team} tem mapa livre.",
        ],
        "COACH_COMM": [
            f"[Comissão] Ajuste tático pré-definido em {role or 'rota'}: {extra or 'foco de lane'}.",
            f"[Comissão] Timeout mental: time reorganiza prioridade de objetivos.",
        ],
        "SCOUT_REPORT": [
            f"Intel de scouting: {extra or 'padrão do oponente identificado'}.",
        ],
        "VICTORY": [
            f"Vitória de {team}! {extra or 'Nexus destruído.'}",
            f"{team} fecha a partida — {extra or 'GG.'}",
        ],
        "COUNTER_SPIKE": [
            f"{role_tag}Counter-pick fala: {who} ({champ}) abusa do matchup vs {foe}.",
            f"{role_tag}Draft advantage: {who} capitaliza o counter em {loc}.",
        ],
        "DEFAULT": [
            f"{minute:02d} min — {extra or et or 'evento de partida'}.",
        ],
    }

    pool = templates.get(et) or templates["DEFAULT"]
    line = _pick(rng, pool)
    if extra and et not in ("COACH_COMM", "SCOUT_REPORT", "VICTORY", "DEFAULT"):
        # ocasionalmente anexa detalhe
        if rng.random() < 0.25 and extra not in line:
            line = f"{line} ({extra})"
    return line


def enrich_log(log: Dict[str, Any], *, seed: Optional[int] = None) -> Dict[str, Any]:
    """
    Se o log já tem description boa, mantém; senão gera narrate.
    Sempre garante message alinhada.
    """
    out = dict(log)
    et = str(out.get("event_type") or out.get("type") or "DEFAULT")
    desc = out.get("description") or out.get("message") or out.get("log")
    mmap = out.get("map") if isinstance(out.get("map"), dict) else {}
    if not desc or len(str(desc)) < 12:
        desc = narrate(
            et,
            minute=int(str(out.get("timestamp") or "0").split(":")[0] or 0),
            role=mmap.get("role") or out.get("role"),
            side=mmap.get("side") or out.get("side"),
            actor=out.get("actor"),
            victim=out.get("victim"),
            location=mmap.get("location") or out.get("location"),
            team_name=out.get("team_name"),
            extra=out.get("extra"),
            seed=seed,
        )
        out["description"] = desc
    # Variação: se description parece genérica de template antigo de solo kill, ok leave
    out.setdefault("message", out.get("description"))
    return out
