import { useState, useEffect, useMemo, useCallback } from 'react';
import { useGameStore } from '../store/useGameStore';
import { Ban, RotateCcw, Swords, Sparkles, Volume2, Crosshair, Radar, Eye } from 'lucide-react';
import { PlayerRole, ChampionPoolTier, DraftTeam, DraftAction } from '../types/game';
import { ChampionImage } from '../components/ChampionImage';
import { RoleIcon } from '../components/RoleIcon';
import { ROLE_LABELS, championSplashUrl } from '../lib/champions';
import { api, type DraftScoutAdviceResponse, type DraftScoutRecommendation } from '../services/api';

const DRAFT_SEQUENCES = [
  { team: DraftTeam.BLUE, action: DraftAction.BAN },
  { team: DraftTeam.RED, action: DraftAction.BAN },
  { team: DraftTeam.BLUE, action: DraftAction.BAN },
  { team: DraftTeam.RED, action: DraftAction.BAN },
  { team: DraftTeam.BLUE, action: DraftAction.BAN },
  { team: DraftTeam.RED, action: DraftAction.BAN },
  { team: DraftTeam.BLUE, action: DraftAction.PICK },
  { team: DraftTeam.RED, action: DraftAction.PICK },
  { team: DraftTeam.RED, action: DraftAction.PICK },
  { team: DraftTeam.BLUE, action: DraftAction.PICK },
  { team: DraftTeam.BLUE, action: DraftAction.PICK },
  { team: DraftTeam.RED, action: DraftAction.PICK },
  { team: DraftTeam.RED, action: DraftAction.BAN },
  { team: DraftTeam.BLUE, action: DraftAction.BAN },
  { team: DraftTeam.RED, action: DraftAction.BAN },
  { team: DraftTeam.BLUE, action: DraftAction.BAN },
  { team: DraftTeam.RED, action: DraftAction.PICK },
  { team: DraftTeam.BLUE, action: DraftAction.PICK },
  { team: DraftTeam.BLUE, action: DraftAction.PICK },
  { team: DraftTeam.RED, action: DraftAction.PICK },
];

const ROLES_ORDER = [
  PlayerRole.TOP,
  PlayerRole.JUNGLE,
  PlayerRole.MID,
  PlayerRole.BOT,
  PlayerRole.SUPPORT,
];

const LOCK_IN_MS = 950;

type LockInState = {
  champion: string;
  action: DraftAction;
  team: DraftTeam;
  role?: PlayerRole;
};

function BanSlot({ name, justBanned }: { name?: string; justBanned?: boolean }) {
  return (
    <div className={`relative ${justBanned ? 'animate-ban-stamp' : ''}`}>
      <ChampionImage name={name} variant="ban" banned={!!name} emptyLabel="?" />
    </div>
  );
}

function PickSlot({
  champion,
  role,
  side,
  playerName,
  isActiveSlot,
}: {
  champion?: string;
  role: PlayerRole;
  side: 'blue' | 'red';
  playerName?: string;
  isActiveSlot?: boolean;
}) {
  const border = champion
    ? side === 'blue'
      ? 'border-lol-blue-side/60 shadow-[0_0_12px_rgba(0,150,255,0.2)]'
      : 'border-lol-red-side/60 shadow-[0_0_12px_rgba(255,70,85,0.2)]'
    : isActiveSlot
      ? 'border-lol-gold/50 animate-pulse'
      : side === 'blue'
        ? 'border-lol-blue-side/25'
        : 'border-lol-red-side/25';
  const accent = side === 'blue' ? 'text-lol-blue-side' : 'text-lol-red-side';

  return (
    <div
      className={`flex items-center gap-2 p-1.5 bg-black/45 border rounded-sm transition-all duration-300 ${border} ${
        champion ? 'animate-fade-in' : ''
      }`}
    >
      <ChampionImage
        name={champion}
        variant="pick"
        locked={!!champion}
        emptyLabel=""
        className={!champion ? 'opacity-40' : ''}
      />
      <div className="min-w-0 flex-1">
        <div className={`flex items-center gap-1 text-[10px] font-mono uppercase ${accent}`}>
          <RoleIcon role={role} size={12} className={accent} />
          {ROLE_LABELS[role] || role}
        </div>
        <div className="text-xs font-semibold text-white/90 truncate">
          {champion || <span className="text-white/25 italic">Aguardando…</span>}
        </div>
        {playerName && <div className="text-[10px] text-white/40 truncate">{playerName}</div>}
      </div>
      {champion && (
        <span className="text-[8px] font-bold uppercase tracking-wider text-lol-gold/80 border border-lol-gold/30 px-1 py-0.5 rounded-sm">
          Lock
        </span>
      )}
    </div>
  );
}

function LockInOverlay({ state }: { state: LockInState }) {
  const isBan = state.action === DraftAction.BAN;
  return (
    <div className="lock-in-overlay">
      <div className="lock-in-card">
        {/* Splash blur atrás */}
        <div
          className="absolute -inset-20 opacity-40 blur-sm bg-cover bg-center -z-10"
          style={{ backgroundImage: `url(${championSplashUrl(state.champion)})` }}
        />
        <ChampionImage name={state.champion} variant="loading" className="shadow-2xl ring-2 ring-lol-gold/60" />
        <div className={isBan ? 'ban-stamp-label animate-ban-stamp' : 'lock-in-label text-lol-gold'}>
          {isBan ? 'BANNED' : 'LOCKED IN'}
        </div>
        <div className="text-sm font-display text-lol-gold-soft tracking-wide">{state.champion}</div>
        <div
          className={`text-[10px] font-mono uppercase tracking-widest ${
            state.team === DraftTeam.BLUE ? 'text-lol-blue-side' : 'text-lol-red-side'
          }`}
        >
          {state.team} side
          {state.role ? ` · ${ROLE_LABELS[state.role] || state.role}` : ''}
        </div>
        <div className="w-40 h-0.5 bg-white/10 rounded-full overflow-hidden mt-1">
          <div className="h-full bg-lol-gold animate-draft-bar" />
        </div>
      </div>
    </div>
  );
}

export function TacticsDraft() {
  const draft = useGameStore((s) => s.draft);
  const myPlayers = useGameStore((s) => s.myPlayers);
  const processDraftAction = useGameStore((s) => s.processDraftAction);
  const resetDraft = useGameStore((s) => s.resetDraft);
  const champions = useGameStore((s) => s.champions);
  const patchBadges = useGameStore((s) => s.patchBadges);
  const refreshPatch = useGameStore((s) => s.refreshPatch);
  const patchStatus = useGameStore((s) => s.patchStatus);
  const submitDraftAndStartMatch = useGameStore((s) => s.submitDraftAndStartMatch);
  const matchTactics = useGameStore((s) => s.matchTactics);
  const setMatchTactics = useGameStore((s) => s.setMatchTactics);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const activeMatch = useGameStore((s) => s.activeMatch);
  const manager = useGameStore((s) => s.manager);
  const scoutSessionId = useGameStore((s) => s.scoutSessionId);
  const setScoutSessionId = useGameStore((s) => s.setScoutSessionId);
  const setCurrentScreen = useGameStore((s) => s.setCurrentScreen);

  const [selectedRole, setSelectedRole] = useState<PlayerRole>(PlayerRole.MID);
  const [selectedChamp, setSelectedChamp] = useState<string>('');
  const [search, setSearch] = useState('');
  const [lockIn, setLockIn] = useState<LockInState | null>(null);
  const [lastBanned, setLastBanned] = useState<string | null>(null);
  const [isStartingMatch, setIsStartingMatch] = useState(false);
  const [scoutAdvice, setScoutAdvice] = useState<DraftScoutAdviceResponse | null>(null);
  const [scoutLoading, setScoutLoading] = useState(false);
  const [scoutError, setScoutError] = useState<string | null>(null);

  const starters = myPlayers.slice(0, 5);
  const isComplete = draft.isComplete;

  useEffect(() => {
    void refreshPatch();
  }, [refreshPatch]);

  // Inicializa lineup padrão (1º de cada role) quando o draft completa
  useEffect(() => {
    if (!isComplete) return;
    if (matchTactics.starterIds.length >= 5) return;
    const byRole = ROLES_ORDER.map(
      (role) => myPlayers.find((p) => p.role === role)?.id
    ).filter(Boolean) as string[];
    if (byRole.length >= 5) {
      setMatchTactics({ starterIds: byRole.slice(0, 5) });
    } else if (starters.length >= 5) {
      setMatchTactics({ starterIds: starters.slice(0, 5).map((p) => p.id) });
    }
  }, [isComplete, myPlayers, matchTactics.starterIds.length, setMatchTactics, starters]);
  const currentStep =
    !isComplete && draft.currentTurn < 20 ? DRAFT_SEQUENCES[draft.currentTurn] : null;
  const isBusy = !!lockIn;

  const resolvedSide: DraftTeam = useMemo(() => {
    if (!activeMatch) return DraftTeam.BLUE;
    if (activeMatch.blueTeam === myTeamName) return DraftTeam.BLUE;
    if (activeMatch.redTeam === myTeamName) return DraftTeam.RED;
    return DraftTeam.BLUE;
  }, [activeMatch, myTeamName]);

  const isMyTurn = !!(currentStep && currentStep.team === resolvedSide && !isBusy);

  const managedTeamId = useMemo(() => {
    if (manager?.teamId) return manager.teamId;
    if (!activeMatch) return undefined;
    if (resolvedSide === DraftTeam.BLUE) return activeMatch.blueTeamId;
    return activeMatch.redTeamId;
  }, [manager?.teamId, activeMatch, resolvedSide]);

  const scoutRecByChamp = useMemo(() => {
    const map = new Map<string, DraftScoutRecommendation>();
    for (const rec of scoutAdvice?.recommendations || []) {
      map.set(rec.champion.toLowerCase(), rec);
    }
    return map;
  }, [scoutAdvice]);

  // Conselho do scout no turno do manager (patch + maestria + meta global)
  useEffect(() => {
    if (!isMyTurn || isComplete || isBusy || !currentStep) {
      if (!isMyTurn) setScoutAdvice(null);
      return;
    }
    if (!activeMatch?.blueTeamId || !activeMatch?.redTeamId || !managedTeamId) return;

    let cancelled = false;
    const turnSnapshot = draft.currentTurn;
    setScoutLoading(true);
    setScoutError(null);

    const timer = setTimeout(async () => {
      try {
        const res = await api.getDraftScoutAdvice({
          blue_team_id: activeMatch.blueTeamId!,
          red_team_id: activeMatch.redTeamId!,
          managed_team_id: managedTeamId,
          acting_side: resolvedSide,
          current_turn: turnSnapshot,
          blue_bans: draft.blueBans,
          red_bans: draft.redBans,
          blue_picks: draft.bluePicks.map((p) => ({
            champion: p.champion,
            role: p.role,
          })),
          red_picks: draft.redPicks.map((p) => ({
            champion: p.champion,
            role: p.role,
          })),
          focus_role: selectedRole,
          limit: 5,
          session_id: scoutSessionId || undefined,
          fearless_used: fearlessUsed,
        });
        if (cancelled) return;
        if (useGameStore.getState().draft.currentTurn !== turnSnapshot) return;
        if (res.session_id && res.session_id !== scoutSessionId) {
          setScoutSessionId(res.session_id);
        }
        setScoutAdvice(res);
      } catch (e) {
        if (cancelled) return;
        setScoutError(e instanceof Error ? e.message : 'Scout indisponível');
        setScoutAdvice(null);
      } finally {
        if (!cancelled) setScoutLoading(false);
      }
    }, 280);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [
    isMyTurn,
    isComplete,
    isBusy,
    currentStep,
    draft.currentTurn,
    draft.blueBans,
    draft.redBans,
    draft.bluePicks,
    draft.redPicks,
    activeMatch?.blueTeamId,
    activeMatch?.redTeamId,
    managedTeamId,
    resolvedSide,
    selectedRole,
    scoutSessionId,
    setScoutSessionId,
  ]);

  const applyScoutPick = useCallback(
    (rec: DraftScoutRecommendation) => {
      if (!isMyTurn || isBusy) return;
      setSelectedChamp(rec.champion);
      if (rec.role && Object.values(PlayerRole).includes(rec.role as PlayerRole)) {
        setSelectedRole(rec.role as PlayerRole);
      }
    },
    [isMyTurn, isBusy]
  );

  const fearlessUsed = activeMatch?.fearlessUsed || [];

  const usedChamps = useMemo(
    () =>
      new Set([
        ...draft.blueBans,
        ...draft.redBans,
        ...draft.bluePicks.map((p) => p.champion),
        ...draft.redPicks.map((p) => p.champion),
        ...fearlessUsed,
      ]),
    [draft, fearlessUsed]
  );

  const championsList = useMemo(() => {
    let list = champions.filter(
      (c) =>
        (c.primary_role === selectedRole || c.secondary_role === selectedRole) &&
        !usedChamps.has(c.name)
    );
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((c) => c.name.toLowerCase().includes(q));
    }
    // Meta do patch: buffs primeiro, nerfs por último, depois A-Z
    const rank = (name: string) => {
      const b = patchBadges[name.toLowerCase()];
      if (b === 'BUFF') return 0;
      if (b === 'NERF') return 2;
      return 1;
    };
    return list.sort((a, b) => {
      const d = rank(a.name) - rank(b.name);
      return d !== 0 ? d : a.name.localeCompare(b.name);
    });
  }, [champions, selectedRole, usedChamps, search, patchBadges]);

  const getComfortLevel = (championName: string, role: PlayerRole) => {
    const player = starters.find((p) => p.role === role);
    if (!player) return ChampionPoolTier.OFF_POOL;
    const entry = (player.championPool || []).find(
      (c) => c.champion.toLowerCase() === championName.toLowerCase()
    );
    return entry ? entry.tier : ChampionPoolTier.OFF_POOL;
  };

  /** Splash de fundo: seleção atual → último pick → Azir */
  const splashChampion = useMemo(() => {
    if (selectedChamp) return selectedChamp;
    if (lockIn) return lockIn.champion;
    const allPicks = [...draft.bluePicks, ...draft.redPicks];
    if (allPicks.length) return allPicks[allPicks.length - 1].champion;
    if (draft.blueBans.length) return draft.blueBans[draft.blueBans.length - 1];
    if (draft.redBans.length) return draft.redBans[draft.redBans.length - 1];
    return 'Aatrox';
  }, [selectedChamp, lockIn, draft.bluePicks, draft.redPicks, draft.blueBans, draft.redBans]);

  const runLockIn = useCallback(
    (champion: string, action: DraftAction, team: DraftTeam, role?: PlayerRole) => {
      return new Promise<void>((resolve) => {
        const turnAtLock = useGameStore.getState().draft.currentTurn;
        const sessionId = useGameStore.getState().scoutSessionId;
        const mySide = resolvedSide;
        setLockIn({ champion, action, team, role });
        if (action === DraftAction.BAN) {
          setLastBanned(champion);
          setTimeout(() => setLastBanned(null), 1200);
        }
        setTimeout(() => {
          // Registra se o manager seguiu o scout (só no turno dele)
          if (sessionId && team === mySide) {
            void api
              .recordDraftScoutAction({
                session_id: sessionId,
                current_turn: turnAtLock,
                action: action === DraftAction.BAN ? 'BAN' : 'PICK',
                champion,
                role: role || selectedRole,
              })
              .catch(() => undefined);
          }
          processDraftAction(champion, role || selectedRole);
          setLockIn(null);
          setSelectedChamp('');
          resolve();
        }, LOCK_IN_MS);
      });
    },
    [processDraftAction, selectedRole, resolvedSide]
  );

  const handleConfirm = async () => {
    if (!selectedChamp || isComplete || !isMyTurn || !currentStep || isBusy) return;
    await runLockIn(
      selectedChamp,
      currentStep.action,
      currentStep.team,
      currentStep.action === DraftAction.PICK ? selectedRole : undefined
    );
  };

  // IA adversária via backend DraftAI (pool + counters), fallback aleatório
  useEffect(() => {
    if (isBusy || isComplete || !currentStep || isMyTurn || champions.length === 0) return;
    if (!activeMatch?.blueTeamId || !activeMatch?.redTeamId) return;

    let cancelled = false;
    const turnSnapshot = draft.currentTurn;

    const timer = setTimeout(async () => {
      if (cancelled) return;
      const available = champions.filter((c) => !usedChamps.has(c.name));
      if (!available.length) return;

      const fallback = () => {
        if (currentStep.action === DraftAction.BAN) {
          return {
            champion: available[Math.floor(Math.random() * available.length)].name,
            role: undefined as PlayerRole | undefined,
          };
        }
        const aiPicks =
          currentStep.team === DraftTeam.BLUE ? draft.bluePicks : draft.redPicks;
        const rolesPicked = aiPicks.map((p) => p.role);
        const availableRole =
          ROLES_ORDER.find((r) => !rolesPicked.includes(r)) || PlayerRole.MID;
        const roleChamps = available.filter(
          (c) => c.primary_role === availableRole || c.secondary_role === availableRole
        );
        return {
          champion:
            roleChamps.length > 0
              ? roleChamps[Math.floor(Math.random() * roleChamps.length)].name
              : available[0].name,
          role: availableRole,
        };
      };

      let champion: string;
      let role: PlayerRole | undefined;

      try {
        const res = await api.getDraftAiDecision({
          blue_team_id: activeMatch.blueTeamId!,
          red_team_id: activeMatch.redTeamId!,
          acting_side: currentStep.team,
          current_turn: turnSnapshot,
          blue_bans: draft.blueBans,
          red_bans: draft.redBans,
          blue_picks: draft.bluePicks.map((p) => ({
            champion: p.champion,
            role: p.role,
          })),
          red_picks: draft.redPicks.map((p) => ({
            champion: p.champion,
            role: p.role,
          })),
          fearless_used: fearlessUsed,
        });
        champion = res.champion;
        if (usedChamps.has(champion)) {
          const fb = fallback();
          champion = fb.champion;
          role = fb.role;
        } else if (res.role && Object.values(PlayerRole).includes(res.role as PlayerRole)) {
          role = res.role as PlayerRole;
        } else if (currentStep.action === DraftAction.PICK) {
          const aiPicks =
            currentStep.team === DraftTeam.BLUE ? draft.bluePicks : draft.redPicks;
          const rolesPicked = aiPicks.map((p) => p.role);
          role = ROLES_ORDER.find((r) => !rolesPicked.includes(r)) || PlayerRole.MID;
        }
      } catch {
        const fb = fallback();
        champion = fb.champion;
        role = fb.role;
      }

      if (cancelled) return;
      // Evita aplicar se o turno já avançou (race)
      if (useGameStore.getState().draft.currentTurn !== turnSnapshot) return;

      await runLockIn(
        champion,
        currentStep.action,
        currentStep.team,
        currentStep.action === DraftAction.PICK ? role : undefined
      );
    }, 650);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [
    draft.currentTurn,
    isComplete,
    currentStep,
    isMyTurn,
    champions.length,
    isBusy,
    usedChamps,
    runLockIn,
    draft.bluePicks,
    draft.redPicks,
    draft.blueBans,
    draft.redBans,
    activeMatch?.blueTeamId,
    activeMatch?.redTeamId,
  ]);

  const blueName = activeMatch?.blueTeam || 'Blue Side';
  const redName = activeMatch?.redTeam || 'Red Side';

  const pickForRole = (side: 'blue' | 'red', role: PlayerRole) => {
    const picks = side === 'blue' ? draft.bluePicks : draft.redPicks;
    return picks.find((p) => p.role === role)?.champion;
  };

  /** Role sendo pickada agora (slot piscando) */
  const activePickRole = useMemo(() => {
    if (!currentStep || currentStep.action !== DraftAction.PICK) return null;
    const picks =
      currentStep.team === DraftTeam.BLUE ? draft.bluePicks : draft.redPicks;
    const rolesPicked = picks.map((p) => p.role);
    return ROLES_ORDER.find((r) => !rolesPicked.includes(r)) || null;
  }, [currentStep, draft.bluePicks, draft.redPicks]);

  const progressPct = (draft.currentTurn / 20) * 100;
  const comfort = selectedChamp ? getComfortLevel(selectedChamp, selectedRole) : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="draft-stage min-h-[560px]">
        {/* Splash de fundo dinâmico */}
        <div
          key={splashChampion}
          className="draft-splash-bg transition-opacity duration-700"
          style={{ backgroundImage: `url(${championSplashUrl(splashChampion)})` }}
        />
        <div className="draft-splash-veil" />

        {/* Overlay lock-in */}
        {lockIn && <LockInOverlay state={lockIn} />}

        <div className="relative z-10 flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 border-b border-lol-gold/20 bg-black/40 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-sm bg-gradient-to-br from-lol-gold to-lol-gold-dim flex items-center justify-center shadow-lol-gold">
                <Swords className="w-4 h-4 text-lol-void" />
              </div>
              <div>
                <h2 className="font-display font-bold text-lol-gold-soft tracking-wide uppercase text-sm sm:text-base">
                  Champion Select
                </h2>
                <p className="text-[10px] text-white/45 font-mono flex items-center gap-1.5">
                  <Volume2 className="w-3 h-3 opacity-50" />
                  Snake Draft · Ação {Math.min(draft.currentTurn + 1, 20)}/20
                  {activeMatch?.isPlayoff && activeMatch?.seriesScoreDisplay && (
                    <span className="text-lol-gold-soft">
                      · Série {activeMatch.seriesScoreDisplay}
                      {activeMatch.mapIndex ? ` · Map ${activeMatch.mapIndex}` : ''}
                    </span>
                  )}
                  {fearlessUsed.length > 0 && (
                    <span className="text-cyan-300/80">· Fearless {fearlessUsed.length}</span>
                  )}
                </p>
              </div>
            </div>
            <button
              onClick={resetDraft}
              disabled={isBusy}
              className="btn-lol flex items-center gap-1.5 py-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          </div>

          {/* Barra de progresso do draft */}
          <div className="h-1 bg-black/50">
            <div
              className="h-full bg-gradient-to-r from-lol-blue-side via-lol-gold to-lol-red-side transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Bans */}
          <div className="grid grid-cols-[1fr_auto_1fr] gap-2 sm:gap-4 items-center px-3 sm:px-4 py-3 bg-black/35 border-b border-white/5 backdrop-blur-[2px]">
            <div className="flex flex-col gap-1.5 items-start">
              <span className="text-[10px] font-bold uppercase tracking-widest text-lol-blue-side drop-shadow">
                {blueName}
              </span>
              <div className="flex gap-1 flex-wrap">
                {Array.from({ length: 5 }).map((_, i) => (
                  <BanSlot
                    key={i}
                    name={draft.blueBans[i]}
                    justBanned={draft.blueBans[i] === lastBanned}
                  />
                ))}
              </div>
            </div>

            <div className="text-center px-1 sm:px-2 min-w-[7rem]">
              {currentStep ? (
                <div
                  className={`px-3 py-2 rounded-sm border backdrop-blur-sm ${
                    currentStep.team === DraftTeam.BLUE
                      ? 'border-lol-blue-side/60 bg-lol-blue-side/15 text-lol-blue-side shadow-lol-blue'
                      : 'border-lol-red-side/60 bg-lol-red-side/15 text-lol-red-side'
                  }`}
                >
                  <div className="text-[9px] uppercase tracking-widest opacity-70">Turno</div>
                  <div className="text-xs sm:text-sm font-bold font-display flex items-center justify-center gap-1">
                    {currentStep.action === DraftAction.BAN ? (
                      <Ban className="w-3.5 h-3.5" />
                    ) : (
                      <Swords className="w-3.5 h-3.5" />
                    )}
                    {currentStep.action}
                  </div>
                  <div className="text-[9px] mt-0.5 opacity-90">
                    {isBusy ? 'Travando…' : isMyTurn ? '● Sua vez' : '○ Oponente'}
                  </div>
                </div>
              ) : (
                <div className="text-emerald-400 text-xs font-bold uppercase flex items-center gap-1 justify-center">
                  <Sparkles className="w-4 h-4" /> Pronto
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1.5 items-end">
              <span className="text-[10px] font-bold uppercase tracking-widest text-lol-red-side drop-shadow">
                {redName}
              </span>
              <div className="flex gap-1 flex-wrap justify-end">
                {Array.from({ length: 5 }).map((_, i) => (
                  <BanSlot
                    key={i}
                    name={draft.redBans[i]}
                    justBanned={draft.redBans[i] === lastBanned}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Picks + grid */}
          <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_220px] gap-0 flex-1">
            {/* Blue */}
            <div className="p-3 space-y-1.5 border-r border-white/5 bg-gradient-to-b from-lol-blue-side/10 to-black/20 order-2 lg:order-1 backdrop-blur-[1px]">
              {ROLES_ORDER.map((role) => (
                <PickSlot
                  key={role}
                  role={role}
                  side="blue"
                  champion={pickForRole('blue', role)}
                  isActiveSlot={
                    currentStep?.team === DraftTeam.BLUE &&
                    currentStep.action === DraftAction.PICK &&
                    activePickRole === role
                  }
                  playerName={
                    resolvedSide === DraftTeam.BLUE
                      ? starters.find((p) => p.role === role)?.name
                      : undefined
                  }
                />
              ))}
            </div>

            {/* Centro */}
            <div className="p-3 sm:p-4 flex flex-col gap-3 order-1 lg:order-2 min-h-[340px] bg-black/25 backdrop-blur-[1px]">
              {!isComplete && currentStep ? (
                <>
                  {/* Role filters com ícones */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {ROLES_ORDER.map((role) => {
                      const active = selectedRole === role;
                      return (
                        <button
                          key={role}
                          onClick={() => {
                            setSelectedRole(role);
                            setSelectedChamp('');
                          }}
                          disabled={isBusy}
                          className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide rounded-sm border transition-all ${
                            active
                              ? 'border-lol-gold bg-lol-gold/20 text-lol-gold shadow-lol-gold'
                              : 'border-white/15 text-white/50 hover:border-white/35 hover:text-white/80 bg-black/30'
                          }`}
                        >
                          <RoleIcon role={role} size={14} active={active} />
                          <span className="hidden sm:inline">{ROLE_LABELS[role]}</span>
                        </button>
                      );
                    })}
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Buscar…"
                      disabled={isBusy}
                      className="ml-auto flex-1 min-w-[7rem] max-w-xs bg-black/55 border border-white/15 px-2 py-1.5 text-xs rounded-sm focus:border-lol-gold focus:outline-none placeholder:text-white/30"
                    />
                  </div>

                  {/* Preview do campeão hover/selecionado (splash thumb) */}
                  {selectedChamp && (
                    <div className="relative h-16 sm:h-20 rounded-sm overflow-hidden border border-lol-gold/30 animate-fade-in">
                      <div
                        className="absolute inset-0 bg-cover bg-center"
                        style={{ backgroundImage: `url(${championSplashUrl(selectedChamp)})` }}
                      />
                      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent" />
                      <div className="relative h-full flex items-center gap-3 px-3">
                        <ChampionImage name={selectedChamp} variant="portrait" highlighted />
                        <div>
                          <div className="font-display font-bold text-lol-gold-soft text-sm sm:text-base">
                            {selectedChamp}
                          </div>
                          <div className="text-[10px] text-white/60 flex items-center gap-1">
                            <RoleIcon role={selectedRole} size={11} className="text-lol-gold" />
                            {ROLE_LABELS[selectedRole]}
                            {currentStep.action === DraftAction.PICK && comfort && (
                              <span
                                className={`ml-2 ${
                                  comfort === ChampionPoolTier.MAIN
                                    ? 'text-emerald-400'
                                    : comfort === ChampionPoolTier.SECONDARY
                                      ? 'text-sky-400'
                                      : 'text-lol-red-side'
                                }`}
                              >
                                ·{' '}
                                {comfort === ChampionPoolTier.MAIN
                                  ? 'MAIN (+12% live)'
                                  : comfort === ChampionPoolTier.SECONDARY
                                    ? 'SEC (−12% live)'
                                    : 'OFF POOL (−48% live)'}
                              </span>
                            )}
                          </div>
                          {currentStep.action === DraftAction.PICK &&
                            comfort === ChampionPoolTier.OFF_POOL && (
                              <p className="text-[9px] text-lol-red-side/90 mt-0.5 max-w-xs">
                                Fora da pool do laner — performance reduzida no motor.
                              </p>
                            )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Grid de campeões (buffs do patch sobem na lista) */}
                  {patchStatus?.active?.version && (
                    <div className="text-[9px] font-mono text-white/40 px-1 flex items-center gap-2">
                      <span className="text-lol-gold-soft">Patch v{patchStatus.active.version}</span>
                      <span className="text-emerald-400">▲ BUFF</span>
                      <span className="text-red-400">▼ NERF</span>
                      <span className="text-cyan-300/80">◎ Scout</span>
                      <span className="text-white/30">ordenam o grid e guiam a IA</span>
                    </div>
                  )}

                  {/* Painel Scout — recomenda ban/pick com patch + maestria + meta */}
                  {isMyTurn && (
                    <div className="border border-cyan-500/25 bg-gradient-to-r from-cyan-950/40 via-black/50 to-black/40 rounded-sm p-2.5 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-cyan-300/90 font-semibold">
                          <Radar className="w-3.5 h-3.5" />
                          Scout
                          {scoutAdvice?.scout?.name && (
                            <span className="text-white/50 font-normal normal-case tracking-normal">
                              · {scoutAdvice.scout.name}
                              <span className="text-white/30 ml-1">
                                (meta {scoutAdvice.scout.meta_reading}/20)
                              </span>
                            </span>
                          )}
                        </div>
                        <div className="text-[9px] font-mono text-white/40 flex items-center gap-1">
                          <Eye className="w-3 h-3" />
                          {currentStep.action === DraftAction.BAN ? 'BAN tip' : 'PICK tip'}
                          {scoutAdvice?.patch?.version && (
                            <span className="text-lol-gold-soft ml-1">
                              p{scoutAdvice.patch.version}
                            </span>
                          )}
                        </div>
                      </div>

                      {scoutLoading && (
                        <p className="text-[10px] text-cyan-200/50 font-mono animate-pulse px-0.5">
                          Analisando pool, patch e meta global…
                        </p>
                      )}
                      {scoutError && !scoutLoading && (
                        <p className="text-[10px] text-red-300/70 px-0.5">{scoutError}</p>
                      )}
                      {!scoutLoading && !scoutError && scoutAdvice?.intel_note && (
                        <p className="text-[9px] text-white/40 leading-snug px-0.5">
                          {scoutAdvice.intel_note}
                        </p>
                      )}
                      {!scoutLoading &&
                        (scoutAdvice?.opponent_stars?.length || 0) > 0 && (
                          <div className="flex flex-wrap gap-1 px-0.5">
                            {scoutAdvice!.opponent_stars!.slice(0, 3).map((s) => (
                              <span
                                key={s.player_id}
                                className="text-[8px] px-1.5 py-0.5 rounded-sm border border-amber-500/30 bg-amber-950/40 text-amber-200/90"
                                title={`Scouting ${s.scouting_progress}% · score ${s.star_score}`}
                              >
                                ★ {s.player_name} · {s.label}
                              </span>
                            ))}
                          </div>
                        )}

                      <div className="flex flex-col gap-1.5 max-h-[148px] overflow-y-auto">
                        {(scoutAdvice?.recommendations || []).map((rec) => {
                          const topReason = rec.reasons?.[0]?.label;
                          const active = selectedChamp === rec.champion;
                          const wr = rec.global_meta?.win_rate_proxy;
                          const pr = rec.global_meta?.pick_rate_proxy;
                          return (
                            <button
                              key={`${rec.priority}-${rec.champion}`}
                              type="button"
                              onClick={() => applyScoutPick(rec)}
                              disabled={isBusy}
                              className={`flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-sm border transition-colors ${
                                active
                                  ? 'border-cyan-400/60 bg-cyan-500/15'
                                  : 'border-white/10 bg-black/35 hover:border-cyan-500/35 hover:bg-cyan-950/30'
                              }`}
                            >
                              <span className="text-[10px] font-mono text-cyan-300/80 w-4 shrink-0">
                                #{rec.priority}
                              </span>
                              <ChampionImage
                                name={rec.champion}
                                variant="portrait"
                                className="!w-8 !h-8 shrink-0"
                              />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-white/90">
                                  <span className="truncate">{rec.champion}</span>
                                  {rec.pool_tier === ChampionPoolTier.MAIN && (
                                    <span className="text-[8px] text-emerald-400 uppercase">Main</span>
                                  )}
                                  {rec.global_meta?.tier && (
                                    <span className="text-[8px] font-mono text-lol-gold/80">
                                      meta {rec.global_meta.tier}
                                    </span>
                                  )}
                                </div>
                                <div className="text-[9px] text-white/45 truncate">
                                  {wr != null && pr != null
                                    ? `${wr}% WR · ${pr}% PR · `
                                    : ''}
                                  {topReason || rec.summary}
                                </div>
                              </div>
                              <div className="text-right shrink-0">
                                <div className="text-[11px] font-mono text-cyan-300">
                                  {Math.round(rec.score)}
                                </div>
                                <div className="text-[8px] text-white/30">
                                  {Math.round((rec.confidence || 0) * 100)}% conf
                                </div>
                              </div>
                            </button>
                          );
                        })}
                        {!scoutLoading &&
                          !scoutError &&
                          (scoutAdvice?.recommendations?.length || 0) === 0 && (
                            <p className="text-[10px] text-white/35 px-0.5 py-1">
                              Aguardando análise do scout…
                            </p>
                          )}
                      </div>
                    </div>
                  )}

                  <div className="flex-1 overflow-y-auto max-h-[280px] sm:max-h-[300px] grid grid-cols-5 sm:grid-cols-6 md:grid-cols-7 gap-1.5 p-1 content-start">
                    {championsList.map((c) => {
                      const badge = patchBadges[c.name.toLowerCase()];
                      const scoutRec = scoutRecByChamp.get(c.name.toLowerCase());
                      return (
                        <div key={c.id} className="relative">
                          <ChampionImage
                            name={c.name}
                            variant="portrait"
                            showName
                            highlighted={selectedChamp === c.name}
                            disabled={!isMyTurn || isBusy}
                            onClick={() => isMyTurn && !isBusy && setSelectedChamp(c.name)}
                            className={`!w-full !h-auto aspect-square ${
                              scoutRec ? 'ring-1 ring-cyan-400/50' : ''
                            }`}
                          />
                          {scoutRec && (
                            <span className="absolute top-0.5 left-0.5 text-[8px] font-bold px-1 rounded-sm border z-10 bg-cyan-950/90 text-cyan-200 border-cyan-500/50">
                              #{scoutRec.priority}
                            </span>
                          )}
                          {badge && (
                            <span
                              className={`absolute top-0.5 right-0.5 text-[8px] font-bold px-1 rounded-sm border z-10 ${
                                badge === 'BUFF'
                                  ? 'bg-emerald-950/90 text-emerald-300 border-emerald-600/50'
                                  : 'bg-red-950/90 text-red-300 border-red-700/50'
                              }`}
                            >
                              {badge === 'BUFF' ? '▲' : '▼'}
                            </span>
                          )}
                        </div>
                      );
                    })}
                    {championsList.length === 0 && (
                      <div className="col-span-full text-center text-white/40 text-xs py-10">
                        Nenhum campeão disponível nesta role.
                      </div>
                    )}
                  </div>

                  {/* Confirm bar */}
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2.5 bg-black/55 border border-lol-gold/20 rounded-sm">
                    {selectedChamp ? (
                      <>
                        <ChampionImage name={selectedChamp} variant="pick" highlighted />
                        <div className="flex-1 min-w-0 text-xs text-white/55">
                          {currentStep.action === DraftAction.BAN
                            ? `Banir ${selectedChamp} do draft`
                            : `Travar ${selectedChamp} como ${ROLE_LABELS[selectedRole]}`}
                          {currentStep.action === DraftAction.PICK &&
                            comfort === ChampionPoolTier.OFF_POOL && (
                              <span className="block text-lol-red-side text-[10px] mt-0.5">
                                ⚠ Off-pool — debuff de mecânica
                              </span>
                            )}
                          {selectedChamp && patchBadges[selectedChamp.toLowerCase()] === 'BUFF' && (
                            <span className="block text-emerald-400 text-[10px] mt-0.5">
                              ▲ Buff no patch — recomendado no meta atual
                            </span>
                          )}
                          {selectedChamp && patchBadges[selectedChamp.toLowerCase()] === 'NERF' && (
                            <span className="block text-red-400 text-[10px] mt-0.5">
                              ▼ Nerf no patch — desempenho reduzido no motor
                            </span>
                          )}
                        </div>
                        <button
                          onClick={handleConfirm}
                          disabled={!isMyTurn || isBusy}
                          className={
                            currentStep.action === DraftAction.BAN
                              ? 'btn-lol-danger min-w-[9rem]'
                              : 'btn-lol-primary min-w-[9rem]'
                          }
                        >
                          {currentStep.action === DraftAction.BAN ? (
                            <span className="flex items-center justify-center gap-1">
                              <Ban className="w-3.5 h-3.5" /> Banir
                            </span>
                          ) : (
                            'Lock In'
                          )}
                        </button>
                      </>
                    ) : (
                      <p className="text-[11px] text-white/40 w-full text-center py-2 font-mono">
                        {isMyTurn
                          ? 'Selecione um campeão no grid para continuar'
                          : 'Aguardando oponente…'}
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <div className="flex flex-col gap-3 py-3 px-1 flex-1 overflow-y-auto max-h-[420px] animate-fade-in">
                  <div className="flex flex-col items-center gap-2">
                    <div className="flex gap-1.5 flex-wrap justify-center max-w-md">
                      {draft.bluePicks.map((p) => (
                        <ChampionImage key={`b-${p.champion}`} name={p.champion} variant="pick" locked />
                      ))}
                      <span className="self-center text-white/30 px-2 font-display">VS</span>
                      {draft.redPicks.map((p) => (
                        <ChampionImage key={`r-${p.champion}`} name={p.champion} variant="pick" locked />
                      ))}
                    </div>
                    <Sparkles className="w-8 h-8 text-lol-gold animate-pulse" />
                    <h3 className="font-display text-base text-lol-gold-soft uppercase tracking-wide">
                      Draft completo · Táticas
                    </h3>
                    <p className="text-[11px] text-white/45 max-w-md text-center">
                      Defina estilo, coach comms e titulares antes de entrar no Rift.
                    </p>
                  </div>

                  <div className="border border-white/10 bg-black/40 rounded-sm p-3 space-y-2">
                    <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-lol-gold/80 font-semibold">
                      <Crosshair className="w-3.5 h-3.5" /> Estilo de jogo
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                      {(
                        [
                          { id: 'BALANCED' as const, label: 'Balanced', hint: 'Sem viés' },
                          { id: 'EARLY' as const, label: 'Early', hint: 'Rotas / 0-15' },
                          { id: 'MID' as const, label: 'Mid', hint: 'Objetivos' },
                          { id: 'LATE' as const, label: 'Late', hint: 'Scaling' },
                        ] as const
                      ).map((opt) => (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => setMatchTactics({ gameStyle: opt.id })}
                          className={`px-2 py-2 rounded-sm border text-left transition-colors ${
                            matchTactics.gameStyle === opt.id
                              ? 'border-lol-gold bg-lol-gold/15 text-lol-gold'
                              : 'border-white/10 bg-black/30 text-white/60 hover:border-white/25'
                          }`}
                        >
                          <div className="text-[11px] font-bold uppercase">{opt.label}</div>
                          <div className="text-[9px] opacity-60">{opt.hint}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="border border-white/10 bg-black/40 rounded-sm p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase tracking-wider text-lol-gold/80 font-semibold">
                        Coach Comms (early)
                      </span>
                      <span className="font-mono text-sm text-lol-gold">
                        {matchTactics.coachComms}/6
                      </span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={6}
                      value={matchTactics.coachComms}
                      onChange={(e) =>
                        setMatchTactics({ coachComms: Number(e.target.value) })
                      }
                      className="w-full accent-[#c89b3c]"
                    />
                    <p className="text-[9px] text-white/35">
                      Chamadas táticas no early. Acima de 3 aumenta risco de confusão.
                    </p>
                  </div>

                  <div className="border border-white/10 bg-black/40 rounded-sm p-3 space-y-2">
                    <span className="text-[10px] uppercase tracking-wider text-lol-gold/80 font-semibold">
                      Lineup titulares
                    </span>
                    <div className="space-y-1.5">
                      {ROLES_ORDER.map((role, idx) => {
                        const selectedId = matchTactics.starterIds[idx];
                        const options = myPlayers.filter((p) => p.role === role);
                        return (
                          <div key={role} className="flex items-center gap-2 text-[11px]">
                            <span className="w-14 text-white/40 font-mono flex items-center gap-1">
                              <RoleIcon role={role} size={11} />
                              {ROLE_LABELS[role]}
                            </span>
                            <select
                              value={selectedId || options[0]?.id || ''}
                              onChange={(e) => {
                                const next = ROLES_ORDER.map((_, i) =>
                                  i === idx
                                    ? e.target.value
                                    : matchTactics.starterIds[i] || ''
                                );
                                setMatchTactics({ starterIds: next });
                              }}
                              className="flex-1 bg-black/50 border border-white/15 rounded-sm px-2 py-1 text-white/80 focus:border-lol-gold outline-none"
                            >
                              {options.length === 0 && <option value="">Sem jogador</option>}
                              {options.map((p) => (
                                <option key={p.id} value={p.id}>
                                  {p.name} · CA {p.currentAbility}
                                  {p.burnoutMeter > 60 ? ' · cansado' : ''}
                                </option>
                              ))}
                            </select>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <button
                    className="btn-lol-primary px-8 py-3 text-sm self-center"
                    disabled={isStartingMatch}
                    onClick={async () => {
                      setIsStartingMatch(true);
                      try {
                        await submitDraftAndStartMatch();
                        setCurrentScreen('SIMULATION');
                      } catch (e) {
                        console.error(e);
                        alert('Erro ao iniciar partida');
                      } finally {
                        setIsStartingMatch(false);
                      }
                    }}
                  >
                    {isStartingMatch ? 'Carregando…' : 'Entrar no Rift →'}
                  </button>
                </div>
              )}
            </div>

            {/* Red */}
            <div className="p-3 space-y-1.5 border-l border-white/5 bg-gradient-to-b from-lol-red-side/10 to-black/20 order-3 backdrop-blur-[1px]">
              {ROLES_ORDER.map((role) => (
                <PickSlot
                  key={role}
                  role={role}
                  side="red"
                  champion={pickForRole('red', role)}
                  isActiveSlot={
                    currentStep?.team === DraftTeam.RED &&
                    currentStep.action === DraftAction.PICK &&
                    activePickRole === role
                  }
                  playerName={
                    resolvedSide === DraftTeam.RED
                      ? starters.find((p) => p.role === role)?.name
                      : undefined
                  }
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Log */}
      <div className="panel-lol">
        <div className="panel-lol-header">
          <span className="text-xs font-semibold uppercase tracking-wider text-white/60">
            Log do draft
          </span>
          <span className="text-[10px] font-mono text-white/30">{draft.narrative.length} eventos</span>
        </div>
        <div className="max-h-28 overflow-y-auto p-2 font-mono text-[10px] text-white/45 space-y-0.5">
          {draft.narrative.map((log, i) => (
            <div
              key={i}
              className={`${log.includes('⚠️') ? 'text-lol-red-side' : ''} ${
                i === draft.narrative.length - 1 ? 'text-lol-gold-soft' : ''
              }`}
            >
              {log}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
