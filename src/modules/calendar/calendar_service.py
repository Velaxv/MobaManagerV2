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

    async def advance_all_leagues(self) -> list[dict]:
        """
        Avança o calendário de todas as ligas ativas por exatamente um dia.

        Chamado pelo CRON job diário. Processa cada liga de forma isolada;
        erros em uma liga não afetam as demais.

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
                day_info = await self.advance_league_day(league)
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

    async def advance_league_day(self, league: League) -> dict:
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

            # Despacha partidas se for dia de jogo
            if day_info["is_match_day"]:
                await self._dispatch_match_day(league=league, day_info=day_info)

        # Atualiza o cache do patch ativo para a data atual do calendário
        from src.modules.simulation.patch_service import PatchService
        current_date = date.today() + timedelta(days=day_info["total_days"])
        patch_service = PatchService(self.db)
        active_patch_version = await patch_service.update_patch_cache(current_date)
        day_info["active_patch"] = active_patch_version

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

    async def _dispatch_match_day(self, league: League, day_info: dict) -> list[dict]:
        """
        Despacha o processamento de partidas para um dia de jogo.

        Gera partidas aleatórias para todos os times da liga e as retorna
        para que o frontend possa iniciar a simulação interativa se o player estiver envolvido.

        Args:
            league: Entidade da liga.
            day_info: Informações do dia atual retornadas pela SM.
            
        Returns:
            Lista de dicionários representando as partidas agendadas (sem os IDs de banco, apenas pra UI)
        """
        logger.info(
            f"[CalendarService] MATCH DAY disparado para liga '{league.name}' "
            f"| Semana {day_info['week']} | Dia {day_info['total_days']} "
            f"| Estado: {day_info['state']}"
        )
        
        teams = await self._get_league_teams(league)
        if len(teams) < 2:
            return []
            
        import random
        shuffled = list(teams)
        random.shuffle(shuffled)
        
        matches = []
        for i in range(0, len(shuffled) - 1, 2):
            matches.append({
                "blue_team_id": str(shuffled[i].id),
                "blue_team_name": shuffled[i].name,
                "blue_team_abbr": shuffled[i].abbreviation,
                "red_team_id": str(shuffled[i+1].id),
                "red_team_name": shuffled[i+1].name,
                "red_team_abbr": shuffled[i+1].abbreviation,
            })
            
        day_info["scheduled_matches"] = matches
        return matches

    async def get_league_calendar_status(self, league_id: str) -> Optional[dict]:
        """
        Retorna o status atual do calendário de uma liga sem avançar o dia.

        Útil para exibição no dashboard e para APIs de consulta.

        Args:
            league_id: UUID da liga como string.

        Returns:
            Dict com o estado atual ou None se a liga não existir.
        """
        result = await self.db.execute(
            select(League).where(League.id == league_id)
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
