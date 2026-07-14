import { useState, useEffect, useMemo, useCallback } from 'react';
import { useGameStore } from '../store/useGameStore';
import { Ban, RotateCcw, Swords, Sparkles, Volume2 } from 'lucide-react';
import { PlayerRole, ChampionPoolTier, DraftTeam, DraftAction } from '../types/game';
import { ChampionImage } from '../components/ChampionImage';
import { RoleIcon } from '../components/RoleIcon';
import { ROLE_LABELS, championSplashUrl } from '../lib/champions';
import { api } from '../services/api';

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
  const submitDraftAndStartMatch = useGameStore((s) => s.submitDraftAndStartMatch);
  const myTeamName = useGameStore((s) => s.myTeamName);
  const activeMatch = useGameStore((s) => s.activeMatch);
  const setCurrentScreen = useGameStore((s) => s.setCurrentScreen);

  const [selectedRole, setSelectedRole] = useState<PlayerRole>(PlayerRole.MID);
  const [selectedChamp, setSelectedChamp] = useState<string>('');
  const [search, setSearch] = useState('');
  const [lockIn, setLockIn] = useState<LockInState | null>(null);
  const [lastBanned, setLastBanned] = useState<string | null>(null);
  const [isStartingMatch, setIsStartingMatch] = useState(false);

  const starters = myPlayers.slice(0, 5);
  const isComplete = draft.isComplete;
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

  const usedChamps = useMemo(
    () =>
      new Set([
        ...draft.blueBans,
        ...draft.redBans,
        ...draft.bluePicks.map((p) => p.champion),
        ...draft.redPicks.map((p) => p.champion),
      ]),
    [draft]
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
    return list.sort((a, b) => a.name.localeCompare(b.name));
  }, [champions, selectedRole, usedChamps, search]);

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
        setLockIn({ champion, action, team, role });
        if (action === DraftAction.BAN) {
          setLastBanned(champion);
          setTimeout(() => setLastBanned(null), 1200);
        }
        setTimeout(() => {
          processDraftAction(champion, role || selectedRole);
          setLockIn(null);
          setSelectedChamp('');
          resolve();
        }, LOCK_IN_MS);
      });
    },
    [processDraftAction, selectedRole]
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
                                · {comfort}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Grid de campeões */}
                  <div className="flex-1 overflow-y-auto max-h-[280px] sm:max-h-[300px] grid grid-cols-5 sm:grid-cols-6 md:grid-cols-7 gap-1.5 p-1 content-start">
                    {championsList.map((c) => (
                      <ChampionImage
                        key={c.id}
                        name={c.name}
                        variant="portrait"
                        showName
                        highlighted={selectedChamp === c.name}
                        disabled={!isMyTurn || isBusy}
                        onClick={() => isMyTurn && !isBusy && setSelectedChamp(c.name)}
                        className="!w-full !h-auto aspect-square"
                      />
                    ))}
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
                <div className="flex flex-col items-center justify-center py-10 gap-5 flex-1">
                  <div className="flex gap-1.5 flex-wrap justify-center max-w-md">
                    {draft.bluePicks.map((p) => (
                      <ChampionImage key={`b-${p.champion}`} name={p.champion} variant="pick" locked />
                    ))}
                    <span className="self-center text-white/30 px-2 font-display">VS</span>
                    {draft.redPicks.map((p) => (
                      <ChampionImage key={`r-${p.champion}`} name={p.champion} variant="pick" locked />
                    ))}
                  </div>
                  <Sparkles className="w-10 h-10 text-lol-gold animate-pulse" />
                  <h3 className="font-display text-lg text-lol-gold-soft uppercase tracking-wide">
                    Draft completo
                  </h3>
                  <p className="text-xs text-white/50 max-w-sm text-center">
                    Composições travadas. Hora de entrar no Rift.
                  </p>
                  <button
                    className="btn-lol-primary px-8 py-3 text-sm"
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
