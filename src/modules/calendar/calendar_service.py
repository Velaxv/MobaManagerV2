"""
Serviço principal do Calendário do LoL Manager.

Responsabilidades:
  - Coordenar o avanço diário do calendário para todas as ligas ativas
  - Instanciar e cachear State Machines por liga
  - Sincronizar o estado do calendário com a tabela `leagues` no banco
  - Delegar o processamento de burnout ao BurnoutService ao final de cada dia
  - Despachar eventos de partida para o match engine quando is_match_day=True
"""
import logging
from typing import Optional
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.modules.calendar.state_machine import CalendarStateMachine
from src.modules.calendar.burnout_service import BurnoutService
from src.models.league import League
from src.models.team import Team
from src.shared.enums import SplitPhase, CalendarDayType

logger = logging.getLogger(__name__)


class CalendarService:
    """
    Serviço que coordena o avanço diário do tempo para todas as ligas.

    Instância é criada por requisição (ou por worker de cron), recebendo
    a sessão assíncrona do banco de dados.

    As State Machines são cacheadas em memória durante a vida da instância
    para evitar roundtrips desnecessários ao Redis.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Args:
            db: Sessão assíncrona do SQLAlchemy (injetada via DI).
        """
        self.db = db
        self.burnout_service = BurnoutService(db)
        # Cache em memória: league_id → CalendarStateMachine
        self._state_machines: dict[str, CalendarStateMachine] = {}

    async def _get_or_create_sm(self, league: League) -> CalendarStateMachine:
        """
        Recupera a State Machine de uma liga do cache ou cria uma nova.

        A SM é inicializada (restaura do Redis ou cria do zero) na primeira
        vez que é solicitada para uma liga.

        Args:
            league: Entidade da liga.

        Returns:
            State Machine inicializada e pronta para uso.
        """
        league_id = str(league.id)

        if league_id not in self._state_machines:
            sm = CalendarStateMachine(
                league_id=league_id,
                regular_season_weeks=league.regular_season_weeks,
            )
            await sm.initialize()
            self._state_machines[league_id] = sm
            logger.debug(f"[CalendarService] SM criada para liga {league.name} ({league_id})")

        return self._state_machines[league_id]

    async def advance_all_leagues(self, managed_team_id: Optional[str] = None) -> list[dict]:
        """
        Avança o calendário de todas as ligas ativas por exatamente um dia.

        Chamado pelo CRON job diário. Processa cada liga de forma isolada;
        erros em uma liga não afetam as demais.

        Args:
            managed_team_id: Se informado, partidas desse time NÃO são auto-simuladas
                (ficam em scheduled_matches para o jogador interagir no frontend).

        Returns:
            Lista de dicts com o resultado do dia de cada liga.
        """
        result = await self.db.execute(select(League))
        leagues = result.scalars().all()

        if not leagues:
            logger.warning("[CalendarService] Nenhuma liga ativa encontrada.")
            return []

        day_results = []
        for league in leagues:
            try:
                day_info = await self.advance_league_day(league, managed_team_id=managed_team_id)
                day_results.append(day_info)
            except Exception as exc:
                logger.error(
                    f"[CalendarService] Erro ao avançar dia da liga "
                    f"'{league.name}' ({league.id}): {exc}",
                    exc_info=True,
                )

        logger.info(
            f"[CalendarService] Dia processado para {len(day_results)}/{len(leagues)} ligas."
        )
        return day_results

    async def advance_league_day(self, league: League, managed_team_id: Optional[str] = None) -> dict:
        """
        Avança um dia para uma liga específica.

        Fluxo:
          1. Avança a SM → obtém informações do dia.
          2. Sincroniza estado no banco (tabela leagues).
          3. Processa burnout de todos os times da liga.
          4. Se is_match_day → despacha evento de partida (futuro: match engine).
          5. Retorna dict completo do dia.

        Args:
            league: Entidade da liga a ser avançada.

        Returns:
            Dict com informações completas do dia processado.
        """
        sm = await self._get_or_create_sm(league)
        day_info = await sm.advance_day()

        # Sincroniza dados do calendário com a tabela leagues no banco
        await self.db.execute(
            update(League)
            .where(League.id == league.id)
            .values(
                current_week=day_info["week"],
                current_day=day_info["total_days"],
                current_phase=self._map_state_to_phase(day_info["state"]),
            )
        )

        # Busca todos os times participantes desta liga
        teams_in_league = await self._get_league_teams(league)

        if not teams_in_league:
            logger.debug(
                f"[CalendarService] Liga '{league.name}' sem times participantes ainda."
            )
        else:
            # Processa burnout para cada time ao final do dia
            for team in teams_in_league:
                try:
                    burnout_events = await self.burnout_service.process_end_of_day(
                        team=team,
                        day_type=day_info["day_type"],
                        is_match_day=day_info["is_match_day"],
                    )
                    if burnout_events:
                        # Agrega eventos de burnout ao resultado do dia
                        day_info.setdefault("burnout_events", []).extend(burnout_events)
                except Exception as exc:
                    logger.error(
                        f"[CalendarService] Erro ao processar burnout do time "
                        f"'{team.name}' na liga '{league.name}': {exc}",
                        exc_info=True,
                    )

            # Despacha partidas se for dia de jogo (regular RR ou playoffs)
            if day_info["is_match_day"]:
                phase_name = day_info.get("state") or ""
                if phase_name == "PLAYOFFS" or (
                    league.current_phase and league.current_phase.value == "PLAYOFFS"
                ):
                    await self._dispatch_playoff_day(
                        league=league,
                        day_info=day_info,
                        managed_team_id=managed_team_id,
                    )
                else:
                    await self._dispatch_match_day(
                        league=league,
                        day_info=day_info,
                        managed_team_id=managed_team_id,
                    )

            # Ao entrar em playoffs (transição no mesmo advance), gera bracket
            if day_info.get("state_changed") and day_info.get("state") == "PLAYOFFS":
                try:
                    from src.modules.calendar.playoff_service import PlayoffService

                    ps = PlayoffService(self.db)
                    bracket = await ps.ensure_bracket(league)
                    day_info["playoff_bracket"] = bracket
                    day_info["playoffs_started"] = True
                except Exception as exc:
                    logger.error(
                        f"[CalendarService] Falha ao iniciar playoffs: {exc}",
                        exc_info=True,
                    )

        # Atualiza o cache do patch ativo para a data atual do calendário
        from src.modules.simulation.patch_service import PatchService
        current_date = date.today() + timedelta(days=day_info["total_days"])
        patch_service = PatchService(self.db)
        active_patch_version = await patch_service.update_patch_cache(current_date)
        day_info["active_patch"] = active_patch_version

        # Enriquecimento para o frontend montar a grade semanal
        day_info["league_id"] = str(league.id)
        day_info["league_name"] = league.name
        day_info["day_of_week_label"] = self._day_label(day_info.get("day_of_week", 0))
        day_info["managed_team_id"] = managed_team_id

        logger.info(
            f"[CalendarService] Liga '{league.name}' | "
            f"Dia {day_info['total_days']} | "
            f"Estado: {day_info['state']} | "
            f"Tipo: {day_info['day_type']} | "
            f"Partida: {day_info['is_match_day']}"
        )

        return day_info

    async def _get_league_teams(self, league: League) -> list[Team]:
        """
        Busca todos os times participantes de uma liga via tabela league_teams.

        Args:
            league: Entidade da liga.

        Returns:
            Lista de entidades Team participantes.
        """
        from src.models.league import LeagueTeam

        result = await self.db.execute(
            select(Team)
            .join(LeagueTeam, LeagueTeam.team_id == Team.id)
            .where(LeagueTeam.league_id == league.id)
        )
        return result.scalars().all()

    async def _dispatch_playoff_day(
        self,
        league: League,
        day_info: dict,
        managed_team_id: Optional[str] = None,
    ) -> list[dict]:
        """Despacha séries de playoffs (top 6) no match day."""
        from src.modules.calendar.playoff_service import PlayoffService

        logger.info(
            f"[CalendarService] PLAYOFF MATCH DAY | {league.name} | "
            f"Semana {day_info.get('week')} | Dia {day_info.get('total_days')}"
        )
        ps = PlayoffService(self.db)

        async def _auto(blue_id: str, red_id: str, week: int, is_playoff: bool):
            return await self._auto_simulate_match(
                league=league,
                blue_team_id=blue_id,
                red_team_id=red_id,
                week=week,
                is_playoff=is_playoff,
            )

        interactive = await ps.dispatch_match_day(
            league=league,
            day_info=day_info,
            managed_team_id=managed_team_id,
            auto_simulate_fn=_auto,
        )
        day_info["round_results"] = self._merge_round_results(
            day_info.get("all_matches_today") or [],
            day_info.get("auto_simulated_matches") or [],
            day_info.get("scheduled_matches") or [],
        )
        return interactive

    async def _dispatch_match_day(
        self,
        league: League,
        day_info: dict,
        managed_team_id: Optional[str] = None,
    ) -> list[dict]:
        """
        Despacha o processamento de partidas para um dia de jogo.

        - Agenda confrontos (round-robin determinístico).
        - Auto-simula confrontos em que o time gerenciado NÃO participa (liga viva).
        - Mantém em scheduled_matches as partidas do time do jogador (interativas).

        Args:
            league: Entidade da liga.
            day_info: Informações do dia atual retornadas pela SM.
            managed_team_id: UUID do time do manager (opcional).

        Returns:
            Lista de dicionários representando as partidas agendadas para UI.
        """
        logger.info(
            f"[CalendarService] MATCH DAY disparado para liga '{league.name}' "
            f"| Semana {day_info['week']} | Dia {day_info['total_days']} "
            f"| Estado: {day_info['state']}"
        )
        
        teams = await self._get_league_teams(league)
        if len(teams) < 2:
            day_info["scheduled_matches"] = []
            day_info["auto_simulated_matches"] = []
            return []

        # Round-robin determinístico (ordem estável por nome)
        from src.shared.round_robin import get_round_pairs, match_day_round_index

        ordered = sorted(teams, key=lambda t: (t.name or "", str(t.id)))
        week = int(day_info.get("week") or 0)
        dow = int(day_info.get("day_of_week") or 0)
        round_idx = match_day_round_index(week, dow)
        pairs = get_round_pairs(ordered, round_idx)

        all_matches = []
        for home, away in pairs:
            all_matches.append({
                "blue_team_id": str(home.id),
                "blue_team_name": home.name,
                "blue_team_abbr": home.abbreviation,
                "red_team_id": str(away.id),
                "red_team_name": away.name,
                "red_team_abbr": away.abbreviation,
                "round_index": round_idx,
            })
        day_info["round_index"] = round_idx

        interactive: list[dict] = []
        auto_results: list[dict] = []

        for match in all_matches:
            involves_manager = (
                managed_team_id
                and managed_team_id in (match["blue_team_id"], match["red_team_id"])
            )
            if involves_manager:
                interactive.append(match)
                continue

            # Sem manager (ou partida de terceiros): simula automaticamente
            try:
                result = await self._auto_simulate_match(
                    league=league,
                    blue_team_id=match["blue_team_id"],
                    red_team_id=match["red_team_id"],
                    week=day_info.get("week", 1),
                )
                auto_results.append({**match, **result})
            except Exception as exc:
                logger.error(
                    f"[CalendarService] Falha ao auto-simular "
                    f"{match['blue_team_abbr']} vs {match['red_team_abbr']}: {exc}",
                    exc_info=True,
                )
                # Em falha, ainda expõe a partida como agendada (sem resultado)
                interactive.append({**match, "auto_sim_failed": True})

        day_info["scheduled_matches"] = interactive
        day_info["auto_simulated_matches"] = auto_results
        day_info["all_matches_today"] = all_matches
        day_info["round_results"] = self._merge_round_results(
            all_matches, auto_results, interactive
        )
        return interactive

    @staticmethod
    def _merge_round_results(
        all_matches: list[dict],
        auto_results: list[dict],
        interactive: list[dict],
    ) -> list[dict]:
        """Monta lista completa da rodada (auto-sim + pendentes do manager)."""
        done_by_pair: dict[tuple, dict] = {}
        for r in auto_results:
            key = (r.get("blue_team_id"), r.get("red_team_id"))
            done_by_pair[key] = r

        pending_ids = {
            (m.get("blue_team_id"), m.get("red_team_id")) for m in interactive
        }
        source = all_matches if all_matches else list(auto_results) + list(interactive)
        rows: list[dict] = []
        seen: set[tuple] = set()
        for m in source:
            key = (m.get("blue_team_id"), m.get("red_team_id"))
            if key in seen or not key[0] or not key[1]:
                continue
            seen.add(key)
            if key in done_by_pair:
                done = done_by_pair[key]
                rows.append({
                    **m,
                    **{k: done[k] for k in done if k not in ("blue_team_id", "red_team_id")},
                    "status": "complete",
                    "match_id": done.get("match_id"),
                    "winner_team_id": done.get("winner_team_id"),
                    "winner_name": done.get("winner_name"),
                    "duration": done.get("duration"),
                    "auto_simulated": True,
                })
            elif key in pending_ids:
                rows.append({
                    **m,
                    "status": "pending",
                    "match_id": None,
                    "winner_team_id": None,
                    "winner_name": None,
                    "auto_simulated": False,
                })
            else:
                rows.append({**m, "status": "unknown"})
        return rows

    async def _auto_simulate_match(
        self,
        league: League,
        blue_team_id: str,
        red_team_id: str,
        week: int,
        is_playoff: bool = False,
    ) -> dict:
        """
        Simula uma partida IA vs IA (draft + MatchEngine) e atualiza standings
        (standings de pontos só na fase regular).
        """
        import uuid as uuid_mod
        from datetime import datetime
        from sqlalchemy import update
        from src.models.match import Match
        from src.models.league import LeagueTeam
        from src.models.contract import Contract
        from src.shared.enums import ContractStatus, SplitPhase
        from src.modules.draft.snake_draft import SnakeDraft, DraftTeam, DraftAction
        from src.modules.draft.draft_ai import DraftAI, calculate_draft_penalties
        from src.modules.simulation.match_engine import MatchEngine, MatchInput

        blue_team = await self.db.get(Team, uuid_mod.UUID(blue_team_id))
        red_team = await self.db.get(Team, uuid_mod.UUID(red_team_id))
        if not blue_team or not red_team:
            raise ValueError("Time não encontrado para auto-simulação")

        blue_team.validate_roster_size()
        red_team.validate_roster_size()

        match_uuid = uuid_mod.uuid4()
        draft = SnakeDraft(match_id=str(match_uuid))
        draft.initialize()
        draft_ai = DraftAI()

        while not draft.get_current_state().is_complete:
            expected = draft.get_expected_action()
            current_team_side = DraftTeam(expected["team"])
            active_team = blue_team if current_team_side == DraftTeam.BLUE else red_team
            passive_team = red_team if current_team_side == DraftTeam.BLUE else blue_team
            chosen_champ, role = draft_ai.make_decision(
                draft_state=draft.get_current_state(),
                team_side=current_team_side,
                team_obj=active_team,
                opponent_team_obj=passive_team,
            )
            draft.process_action(
                team=current_team_side,
                action=DraftAction(expected["action"]),
                champion=chosen_champ,
                role_hint=role.value if role else None,
            )

        draft_state = draft.get_current_state()
        blue_penalty, red_penalty = calculate_draft_penalties(
            blue_picks=draft_state.blue_picks,
            red_picks=draft_state.red_picks,
            blue_team=blue_team,
            red_team=red_team,
        )

        sim_result = MatchEngine().simulate(
            MatchInput(
                blue_team=blue_team,
                red_team=red_team,
                blue_draft=draft_state.blue_picks,
                red_draft=draft_state.red_picks,
                is_playoff=is_playoff,
                match_id=str(match_uuid),
                blue_draft_penalty=blue_penalty,
                red_draft_penalty=red_penalty,
            )
        )
        sim_result.draft_log = draft.to_match_log()

        winner_id = uuid_mod.UUID(sim_result.winner_team_id)
        loser_id = (
            uuid_mod.UUID(red_team_id)
            if winner_id == uuid_mod.UUID(blue_team_id)
            else uuid_mod.UUID(blue_team_id)
        )

        # Standings de pontos apenas na fase regular
        if not is_playoff:
            await self.db.execute(
                update(LeagueTeam)
                .where(LeagueTeam.league_id == league.id, LeagueTeam.team_id == winner_id)
                .values(wins=LeagueTeam.wins + 1, points=LeagueTeam.points + 3)
            )
            await self.db.execute(
                update(LeagueTeam)
                .where(LeagueTeam.league_id == league.id, LeagueTeam.team_id == loser_id)
                .values(losses=LeagueTeam.losses + 1)
            )

        for player in (blue_team.get_starters() + red_team.get_starters()):
            player.games_played_this_split = (player.games_played_this_split or 0) + 1
            contract_query = await self.db.execute(
                select(Contract).where(
                    Contract.player_id == player.id,
                    Contract.status == ContractStatus.ACTIVE,
                )
            )
            contract = contract_query.scalar_one_or_none()
            if contract:
                contract.rookie_games_played += 1
                contract.check_and_trigger_rookie_extension()

        db_match = Match(
            id=match_uuid,
            league_id=league.id,
            split_week=week,
            split_phase=SplitPhase.PLAYOFFS if is_playoff else SplitPhase.REGULAR_SEASON,
            is_playoff=is_playoff,
            scheduled_at=datetime.utcnow(),
            blue_team_id=blue_team.id,
            red_team_id=red_team.id,
            winner_team_id=winner_id,
            blue_result=sim_result.blue_result,
            red_result=sim_result.red_result,
            match_duration_minutes=sim_result.match_duration_minutes,
            blue_win_probability=sim_result.blue_win_probability,
            early_game_log=sim_result.early_game_log,
            mid_game_log=sim_result.mid_game_log,
            late_game_log=sim_result.late_game_log,
            draft_log=sim_result.draft_log,
        )
        self.db.add(db_match)
        await self.db.flush()

        return {
            "match_id": str(match_uuid),
            "winner_team_id": str(winner_id),
            "winner_name": blue_team.name if winner_id == blue_team.id else red_team.name,
            "duration": sim_result.match_duration_minutes,
            "auto_simulated": True,
            "is_playoff": is_playoff,
        }

    @staticmethod
    def _day_label(day_of_week: int) -> str:
        labels = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
        try:
            return labels[int(day_of_week) % 7]
        except (TypeError, ValueError):
            return "SEG"

    async def get_league_calendar_status(self, league_id: str) -> Optional[dict]:
        """
        Retorna o status atual do calendário de uma liga sem avançar o dia.

        Útil para exibição no dashboard e para APIs de consulta.

        Args:
            league_id: UUID da liga como string.

        Returns:
            Dict com o estado atual ou None se a liga não existir.
        """
        import uuid as uuid_mod

        try:
            league_uuid = uuid_mod.UUID(str(league_id))
        except (ValueError, TypeError):
            logger.warning(f"[CalendarService] league_id inválido: {league_id!r}")
            return None

        result = await self.db.execute(
            select(League).where(League.id == league_uuid)
        )
        league = result.scalar_one_or_none()

        if not league:
            logger.warning(f"[CalendarService] Liga {league_id} não encontrada.")
            return None

        sm = await self._get_or_create_sm(league)

        if not sm.is_initialized or sm.context is None:
            return None

        ctx = sm.context
        return {
            "league_id": league_id,
            "league_name": league.name,
            "state": ctx.current_state_name,
            "week": ctx.current_week,
            "day_of_week": ctx.current_day_of_week,
            "total_days": ctx.total_days_elapsed,
            "regular_season_weeks": ctx.regular_season_weeks,
            "is_match_day": ctx.is_match_day,
            "is_rest_day": ctx.is_rest_day,
        }

    @staticmethod
    def _map_state_to_phase(state_name: str) -> SplitPhase:
        """
        Converte o nome canônico do estado da SM para o enum SplitPhase.

        Usado para sincronizar o campo current_phase na tabela leagues.

        Args:
            state_name: Nome do estado (ex: "REGULAR_SEASON").

        Returns:
            Enum SplitPhase correspondente. Retorna OFFSEASON como fallback.
        """
        mapping: dict[str, SplitPhase] = {
            "OFFSEASON": SplitPhase.OFFSEASON,
            "PRESEASON": SplitPhase.PRESEASON,
            "REGULAR_SEASON": SplitPhase.REGULAR_SEASON,
            "PLAYOFFS": SplitPhase.PLAYOFFS,
        }
        phase = mapping.get(state_name)
        if phase is None:
            logger.warning(
                f"[CalendarService] Estado desconhecido '{state_name}'. "
                f"Usando OFFSEASON como fallback."
            )
            return SplitPhase.OFFSEASON
        return phase
