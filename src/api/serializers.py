"""Serialização de modelos de domínio para payloads JSON do frontend."""

from typing import Any, Dict, Optional

from src.models import Player, Team, Contract, Match
from src.shared.enums import ContractStatus


def serialize_player(
    player: Player,
    contract: Optional[Contract] = None,
    *,
    scouting_knowledge: Optional[Dict[str, Any]] = None,
    is_own_roster: bool = False,
    apply_scouting_mask: bool = False,
    form: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Serializa jogador + contrato ativo para o frontend.

    apply_scouting_mask=True: esconde consistency / BMA / PA até scoutar.
    """
    active_contract = contract
    if active_contract is None and getattr(player, "contracts", None):
        for c in player.contracts:
            if c.status in (
                ContractStatus.ACTIVE,
                ContractStatus.ROOKIE_EXTENDED,
                ContractStatus.PENDING_RENEWAL,
            ):
                active_contract = c
                break

    champion_pool = player.champion_pool if isinstance(player.champion_pool, list) else []
    base = {
        "id": str(player.id),
        "name": player.name,
        "age": player.get_age(),
        "nationality": player.nationality,
        "role": player.role.value,
        "region": player.region.value if player.region else None,
        "teamId": str(player.team_id) if player.team_id else None,
        "isRookie": player.is_rookie,
        "isStarter": bool(getattr(player, "is_starter", False)),
        "squadStatus": (
            "STARTER"
            if getattr(player, "is_starter", False)
            else (
                "ACADEMY"
                if player.is_rookie or "Academy" in (player.name or "")
                else "BENCH"
            )
        ),
        "currentAbility": player.current_ability,
        "potentialAbility": player.potential_ability,
        "mechanics": player.mechanics,
        "championPool": champion_pool,
        "focus": player.focus,
        "resilience": player.resilience,
        "coachability": player.coachability,
        "teamwork": player.teamwork,
        "consistency": player.consistency,
        "bigMatchAptitude": player.big_match_aptitude,
        "burnoutMeter": player.burnout_meter,
        "visualFatigue": player.visual_fatigue,
        "mentalFatigue": player.mental_fatigue,
        "gamesPlayedThisSplit": player.games_played_this_split or 0,
        "hasRookieClause": bool(active_contract.has_rookie_clause) if active_contract else False,
        "participationRate": (
            active_contract.rookie_participation_rate if active_contract else 0.0
        ),
        "rookieGamesPlayed": (
            int(active_contract.rookie_games_played or 0) if active_contract else 0
        ),
        "rookieTotalLeagueGames": (
            int(active_contract.rookie_total_league_games or 0) if active_contract else 0
        ),
        "rookieExtensionTriggered": (
            bool(active_contract.rookie_extension_triggered) if active_contract else False
        ),
        "rookieClauseThreshold": 0.25,
        "formAvg": form.get("avg") if form else None,
        "formTrend": form.get("trend") if form else None,
        "formLabel": form.get("form_label") if form else None,
        "formLast": form.get("last_rating") if form else None,
        "formGames": form.get("games") if form else 0,
        "formDiscontent": form.get("discontent") if form else 0,
        "formRatings": form.get("ratings") if form else [],
        "contractExpirySeasons": (
            active_contract.remaining_seasons if active_contract else 0
        ),
        "monthlySalary": float(active_contract.monthly_salary) if active_contract else 0.0,
        # Defaults quando sem mask (compat)
        "consistencyKnown": True,
        "bigMatchAptitudeKnown": True,
        "potentialAbilityKnown": True,
        "consistencyMin": None,
        "consistencyMax": None,
        "bigMatchAptitudeMin": None,
        "bigMatchAptitudeMax": None,
        "potentialAbilityMin": None,
        "potentialAbilityMax": None,
        "scoutingProgress": 100.0 if not apply_scouting_mask else 0.0,
        "scoutingFullyScouted": not apply_scouting_mask,
        "scoutingDaysInvested": 0,
    }

    if apply_scouting_mask:
        from src.modules.career.scouting_service import ScoutingService

        # Usa métodos estáticos de máscara sem precisar de sessão DB
        svc = ScoutingService(db=None)  # type: ignore[arg-type]
        return svc.mask_player_payload(
            base,
            player,
            scouting_knowledge,
            is_own_roster=is_own_roster,
        )

    return base


def match_summary_row(match_obj: Match, blue: Team, red: Team) -> dict:
    """Serializa partida para lista de resultados da rodada."""
    winner_id = str(match_obj.winner_team_id) if match_obj.winner_team_id else None
    winner_name = None
    if winner_id == str(blue.id):
        winner_name = blue.name
    elif winner_id == str(red.id):
        winner_name = red.name
    return {
        "match_id": str(match_obj.id),
        "blue_team_id": str(blue.id),
        "blue_team_name": blue.name,
        "blue_team_abbr": blue.abbreviation,
        "red_team_id": str(red.id),
        "red_team_name": red.name,
        "red_team_abbr": red.abbreviation,
        "winner_team_id": winner_id,
        "winner_name": winner_name,
        "duration": match_obj.match_duration_minutes,
        "split_week": match_obj.split_week,
        "split_phase": match_obj.split_phase.value if match_obj.split_phase else None,
        "is_playoff": bool(match_obj.is_playoff),
        "scheduled_at": match_obj.scheduled_at.isoformat() if match_obj.scheduled_at else None,
        "status": "complete" if winner_id else "pending",
    }
