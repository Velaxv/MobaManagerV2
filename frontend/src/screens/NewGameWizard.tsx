import { useEffect, useMemo, useState } from 'react';
import { useGameStore } from '../store/useGameStore';
import { api, type ApiPlayer } from '../services/api';
import {
  ArrowRight,
  ArrowLeft,
  Check,
  User,
  Shield,
  Sparkles,
  Wallet,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import { PlayerPortrait } from '../components/PlayerPortrait';
import { RoleIcon } from '../components/RoleIcon';
import { ROLE_LABELS, championSplashUrl } from '../lib/champions';
import { PlayerRole } from '../types/game';

const STEPS = [
  { id: 1, label: 'Treinador', icon: User },
  { id: 2, label: 'Organização', icon: Shield },
  { id: 3, label: 'Confirmar', icon: Sparkles },
] as const;

/** Flavor curto por tag CBLOL 2026 */
const TEAM_FLAVOR: Record<string, string> = {
  RED: 'Campeã da fase regular no Split 1 — estrutura sólida e mid em alta.',
  FUR: 'Campeã do Split 1 — plantel doméstico agressivo e forma física.',
  VKS: 'Importes de alto nível e comissão técnica experiente.',
  LOS: 'Guest team com Zest e imports coreanos no frontline.',
  FX7: 'Projeto ousado com roster internacional e CA em evolução.',
  LLL: 'Gigante de audiência — orçamento e pressão de título.',
  PNG: 'Tradicional do CBLOL — Robo e núcleo misto BR/KR.',
  LEV: 'Ex-LLA no circuito BR — identidade LATAM e crescimento.',
};

const ROLE_ORDER = [
  PlayerRole.TOP,
  PlayerRole.JUNGLE,
  PlayerRole.MID,
  PlayerRole.BOT,
  PlayerRole.SUPPORT,
];

function teamInitials(name: string, tag?: string) {
  if (tag && tag.length <= 4) return tag.slice(0, 3).toUpperCase();
  const parts = name.replace(/[^\w\s]/g, '').trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

/** Splash por org (campeão “assinatura” do meta/flavor) */
const TEAM_SPLASH: Record<string, string> = {
  RED: 'Azir',
  FUR: "Kai'Sa",
  VKS: 'Aatrox',
  LOS: "K'Sante",
  FX7: 'Lee Sin',
  LLL: 'Jinx',
  PNG: 'Jax',
  LEV: 'Ahri',
};

export function NewGameWizard() {
  const { teams, setManager, setGameState, loadData, isDataLoaded } = useGameStore();
  const [step, setStep] = useState(1);
  const [managerName, setManagerName] = useState('');
  const [selectedTeamId, setSelectedTeamId] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [previewPlayers, setPreviewPlayers] = useState<ApiPlayer[]>([]);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [searchTeam, setSearchTeam] = useState('');

  const selectedTeam = teams.find((t) => t.id === selectedTeamId);

  const filteredTeams = useMemo(() => {
    if (!searchTeam.trim()) return teams;
    const q = searchTeam.toLowerCase();
    return teams.filter(
      (t) =>
        t.name.toLowerCase().includes(q) || t.abbreviation.toLowerCase().includes(q)
    );
  }, [teams, searchTeam]);

  const splashChamp = selectedTeam
    ? TEAM_SPLASH[selectedTeam.abbreviation] || 'Aatrox'
    : 'Aatrox';

  // Preview de titulares ao selecionar time
  useEffect(() => {
    if (!selectedTeamId) {
      setPreviewPlayers([]);
      return;
    }
    let cancelled = false;
    setLoadingPreview(true);
    api
      .getTeamPlayers(selectedTeamId)
      .then((players) => {
        if (cancelled) return;
        // Ordena por role titular
        const ordered: ApiPlayer[] = [];
        for (const role of ROLE_ORDER) {
          const p = players.find((x) => x.role === role && !x.isRookie);
          if (p) ordered.push(p);
          else {
            const any = players.find((x) => x.role === role);
            if (any) ordered.push(any);
          }
        }
        setPreviewPlayers(ordered.slice(0, 5));
      })
      .catch(() => {
        if (!cancelled) setPreviewPlayers([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingPreview(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedTeamId]);

  const canGoStep2 = managerName.trim().length >= 2;
  const canGoStep3 = canGoStep2 && !!selectedTeamId;
  const canStart = canGoStep3 && !isStarting;

  const handleStartCareer = async () => {
    if (!canStart || !selectedTeamId) return;
    setIsStarting(true);
    try {
      setManager(managerName.trim(), selectedTeamId);
      await loadData();
      setGameState('PLAYING');
    } finally {
      setIsStarting(false);
    }
  };

  const maxBudget = Math.max(...teams.map((t) => t.budget), 1);

  return (
    <div className="min-h-screen relative flex flex-col overflow-hidden bg-lol-void">
      {/* Splash de fundo */}
      <div
        key={splashChamp}
        className="absolute inset-0 bg-cover bg-center scale-105 transition-opacity duration-700"
        style={{ backgroundImage: `url(${championSplashUrl(splashChamp)})` }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(200,155,60,0.12)_0%,_transparent_55%),linear-gradient(180deg,rgba(1,10,19,0.75)_0%,rgba(1,10,19,0.96)_55%,#010a13_100%)]" />

      <div className="relative z-10 flex-1 flex flex-col max-w-5xl w-full mx-auto p-4 sm:p-6 lg:p-8 animate-fade-in">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-6 sm:mb-8">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="team-crest !w-8 !h-8 text-[10px]">LM</div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-lol-gold/70 font-semibold">
                Setup de carreira · CBLOL 2026
              </p>
            </div>
            <h1 className="font-display text-2xl sm:text-4xl font-bold text-lol-gold-soft tracking-wide">
              Nova carreira
            </h1>
            <p className="text-white/40 mt-1.5 text-sm max-w-md">
              Defina seu nome de treinador e escolha a organização que vai comandar no split.
            </p>
          </div>
          <button
            onClick={() => setGameState('MAIN_MENU')}
            className="btn-lol flex items-center gap-2 py-1.5 text-[10px]"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Menu
          </button>
        </div>

        {/* Stepper */}
        <div className="flex items-center gap-1 sm:gap-2 mb-6 sm:mb-8">
          {STEPS.map((s, idx) => {
            const Icon = s.icon;
            const done = step > s.id;
            const active = step === s.id;
            return (
              <div key={s.id} className="flex items-center flex-1 min-w-0">
                <button
                  type="button"
                  disabled={s.id === 2 && !canGoStep2 || s.id === 3 && !canGoStep3}
                  onClick={() => {
                    if (s.id === 1) setStep(1);
                    else if (s.id === 2 && canGoStep2) setStep(2);
                    else if (s.id === 3 && canGoStep3) setStep(3);
                  }}
                  className={`flex items-center gap-2 px-2 sm:px-3 py-2 rounded-sm border w-full transition-all ${
                    active
                      ? 'border-lol-gold bg-lol-gold/15 text-lol-gold shadow-lol-gold'
                      : done
                        ? 'border-emerald-700/40 bg-emerald-950/20 text-emerald-400'
                        : 'border-white/10 bg-black/30 text-white/35'
                  } disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  <span
                    className={`w-6 h-6 rounded-sm flex items-center justify-center text-[10px] font-bold shrink-0 ${
                      active
                        ? 'bg-lol-gold text-lol-void'
                        : done
                          ? 'bg-emerald-600 text-white'
                          : 'bg-white/10'
                    }`}
                  >
                    {done ? <Check className="w-3.5 h-3.5" /> : s.id}
                  </span>
                  <span className="hidden sm:flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide truncate">
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    {s.label}
                  </span>
                </button>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`w-3 sm:w-6 h-px shrink-0 mx-0.5 ${
                      step > s.id ? 'bg-emerald-600/60' : 'bg-white/10'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Content */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6 min-h-0">
          {/* Main panel */}
          <div className="lg:col-span-3 panel-lol flex flex-col min-h-[380px]">
            {step === 1 && (
              <div className="p-5 sm:p-8 flex flex-col justify-center flex-1 animate-fade-in">
                <div className="flex items-center gap-2 text-lol-gold mb-4">
                  <User className="w-5 h-5" />
                  <span className="text-xs font-semibold uppercase tracking-[0.2em]">
                    Passo 1 — Identidade
                  </span>
                </div>
                <h2 className="font-display text-xl sm:text-2xl text-lol-gold-soft mb-2">
                  Como você quer ser chamado?
                </h2>
                <p className="text-sm text-white/40 mb-6 max-w-md">
                  Seu nome aparece no hub, nas partidas e na comissão técnica do clube.
                </p>
                <label className="text-[10px] uppercase tracking-widest text-white/35 font-semibold block mb-2">
                  Nome do treinador
                </label>
                <input
                  type="text"
                  value={managerName}
                  onChange={(e) => setManagerName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && canGoStep2) setStep(2);
                  }}
                  placeholder="Ex: tockers, Maestro, BeellzY…"
                  autoFocus
                  maxLength={32}
                  className="w-full max-w-md bg-black/50 border border-white/15 focus:border-lol-gold focus:outline-none focus:shadow-lol-gold px-4 py-3.5 text-lg rounded-sm transition-all"
                />
                <p className="text-[10px] text-white/25 mt-2 font-mono">
                  Mínimo 2 caracteres · {managerName.trim().length}/32
                </p>
                <div className="mt-8">
                  <button
                    disabled={!canGoStep2}
                    onClick={() => setStep(2)}
                    className="btn-lol-primary flex items-center gap-2 px-6 py-3"
                  >
                    Escolher organização
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="flex flex-col flex-1 min-h-0 animate-fade-in">
                <div className="p-4 sm:p-5 border-b border-white/5">
                  <div className="flex items-center gap-2 text-lol-gold mb-1">
                    <Shield className="w-4 h-4" />
                    <span className="text-xs font-semibold uppercase tracking-[0.2em]">
                      Passo 2 — Organização
                    </span>
                  </div>
                  <p className="text-sm text-white/40 mb-3">
                    Olá, <strong className="text-lol-gold-soft">{managerName}</strong> — escolha seu
                    clube no CBLOL.
                  </p>
                  <input
                    value={searchTeam}
                    onChange={(e) => setSearchTeam(e.target.value)}
                    placeholder="Filtrar por nome ou tag…"
                    className="w-full bg-black/40 border border-white/10 focus:border-lol-gold focus:outline-none px-3 py-2 text-sm rounded-sm"
                  />
                </div>
                <div className="flex-1 overflow-y-auto p-3 sm:p-4 grid grid-cols-1 sm:grid-cols-2 gap-2 content-start max-h-[420px]">
                  {!isDataLoaded && teams.length === 0 && (
                    <div className="col-span-full flex items-center justify-center gap-2 py-12 text-white/40 text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Carregando times…
                    </div>
                  )}
                  {filteredTeams.map((team) => {
                    const active = selectedTeamId === team.id;
                    const budgetPct = (team.budget / maxBudget) * 100;
                    return (
                      <button
                        key={team.id}
                        type="button"
                        onClick={() => setSelectedTeamId(team.id)}
                        className={`text-left p-3 rounded-sm border transition-all flex gap-3 ${
                          active
                            ? 'border-lol-gold bg-lol-gold/15 shadow-lol-gold'
                            : 'border-white/10 bg-black/35 hover:border-white/25 hover:bg-black/50'
                        }`}
                      >
                        <div
                          className={`team-crest !w-12 !h-12 text-xs shrink-0 ${
                            active ? 'shadow-lol-gold' : 'opacity-90'
                          }`}
                        >
                          {teamInitials(team.name, team.abbreviation)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <span
                              className={`font-semibold text-sm truncate ${
                                active ? 'text-lol-gold-soft' : 'text-white'
                              }`}
                            >
                              {team.name}
                            </span>
                            <span className="text-[10px] font-mono text-white/40 shrink-0">
                              {team.abbreviation}
                            </span>
                          </div>
                          <div className="text-[10px] font-mono text-emerald-400/90 mt-1">
                            €{(team.budget / 1_000_000).toFixed(2)}M
                            <span className="text-white/30 ml-1.5">
                              · {(team.monthlyRevenue / 1000).toFixed(0)}k/mês
                            </span>
                          </div>
                          <div className="stat-bar mt-1.5 h-1">
                            <div
                              className="stat-bar-fill bg-gradient-to-r from-lol-gold-dim to-lol-gold"
                              style={{ width: `${budgetPct}%` }}
                            />
                          </div>
                          {TEAM_FLAVOR[team.abbreviation] && (
                            <p className="text-[10px] text-white/35 mt-1.5 line-clamp-2 leading-snug">
                              {TEAM_FLAVOR[team.abbreviation]}
                            </p>
                          )}
                        </div>
                        {active && (
                          <Check className="w-4 h-4 text-lol-gold shrink-0 self-center" />
                        )}
                      </button>
                    );
                  })}
                  {isDataLoaded && filteredTeams.length === 0 && (
                    <p className="col-span-full text-xs text-white/40 p-6 text-center font-mono">
                      Nenhum time encontrado. Rode o seed do backend se a lista estiver vazia.
                    </p>
                  )}
                </div>
                <div className="p-3 sm:p-4 border-t border-white/5 flex flex-wrap gap-2 justify-between">
                  <button onClick={() => setStep(1)} className="btn-lol flex items-center gap-1.5">
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Voltar
                  </button>
                  <button
                    disabled={!selectedTeamId}
                    onClick={() => setStep(3)}
                    className="btn-lol-primary flex items-center gap-2"
                  >
                    Revisar e confirmar
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {step === 3 && selectedTeam && (
              <div className="p-5 sm:p-8 flex flex-col flex-1 animate-fade-in">
                <div className="flex items-center gap-2 text-lol-gold mb-4">
                  <Sparkles className="w-5 h-5" />
                  <span className="text-xs font-semibold uppercase tracking-[0.2em]">
                    Passo 3 — Confirmação
                  </span>
                </div>
                <h2 className="font-display text-xl sm:text-2xl text-lol-gold-soft mb-1">
                  Pronto para a temporada?
                </h2>
                <p className="text-sm text-white/40 mb-6">
                  Você assume o comando da comissão técnica. O calendário e o elenco já estão no
                  hub.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
                  <div className="p-4 rounded-sm bg-black/40 border border-white/10">
                    <div className="text-[9px] uppercase tracking-widest text-white/35 mb-1">
                      Treinador
                    </div>
                    <div className="font-display text-lg text-white">{managerName}</div>
                  </div>
                  <div className="p-4 rounded-sm bg-black/40 border border-lol-gold/25">
                    <div className="text-[9px] uppercase tracking-widest text-lol-gold/60 mb-1">
                      Organização
                    </div>
                    <div className="font-display text-lg text-lol-gold-soft">
                      {selectedTeam.name}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 mb-8">
                  <button onClick={() => setStep(1)} className="btn-lol text-[10px] py-1.5">
                    Editar nome
                  </button>
                  <button onClick={() => setStep(2)} className="btn-lol text-[10px] py-1.5">
                    Trocar time
                  </button>
                </div>

                <div className="mt-auto flex flex-wrap gap-2 justify-between items-center">
                  <button onClick={() => setStep(2)} className="btn-lol flex items-center gap-1.5">
                    <ArrowLeft className="w-3.5 h-3.5" />
                    Voltar
                  </button>
                  <button
                    disabled={!canStart}
                    onClick={handleStartCareer}
                    className="btn-lol-primary flex items-center gap-2 px-8 py-3.5 text-sm shadow-lol-gold"
                  >
                    {isStarting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Entrando no hub…
                      </>
                    ) : (
                      <>
                        Começar temporada
                        <ArrowRight className="w-4 h-4" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Side preview */}
          <div className="lg:col-span-2 panel-lol flex flex-col overflow-hidden min-h-[320px]">
            <div className="relative h-28 sm:h-36 overflow-hidden border-b border-white/5">
              <div
                className="absolute inset-0 bg-cover bg-center"
                style={{ backgroundImage: `url(${championSplashUrl(splashChamp)})` }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a1428] via-black/50 to-transparent" />
              <div className="absolute bottom-3 left-3 right-3 flex items-end gap-3">
                <div className="team-crest !w-14 !h-14 text-sm">
                  {selectedTeam
                    ? teamInitials(selectedTeam.name, selectedTeam.abbreviation)
                    : '??'}
                </div>
                <div className="min-w-0">
                  <div className="font-display font-bold text-lg text-lol-gold-soft truncate">
                    {selectedTeam?.name || 'Selecione um time'}
                  </div>
                  <div className="text-[10px] font-mono text-white/45 uppercase tracking-wider">
                    {selectedTeam?.abbreviation || '—'} · {selectedTeam?.region || 'CBLOL'}
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 flex-1 flex flex-col gap-4">
              {selectedTeam ? (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="hub-stat-card !p-2.5">
                      <div className="flex items-center gap-1 text-[9px] uppercase text-white/35">
                        <Wallet className="w-3 h-3 text-emerald-400" /> Orçamento
                      </div>
                      <div className="font-mono font-bold text-emerald-400 text-sm">
                        €{(selectedTeam.budget / 1_000_000).toFixed(2)}M
                      </div>
                    </div>
                    <div className="hub-stat-card !p-2.5">
                      <div className="flex items-center gap-1 text-[9px] uppercase text-white/35">
                        <TrendingUp className="w-3 h-3 text-sky-400" /> Receita
                      </div>
                      <div className="font-mono font-bold text-sky-300 text-sm">
                        €{(selectedTeam.monthlyRevenue / 1000).toFixed(0)}k/mês
                      </div>
                    </div>
                  </div>

                  {TEAM_FLAVOR[selectedTeam.abbreviation] && (
                    <p className="text-[11px] text-white/45 leading-relaxed border-l-2 border-lol-gold/40 pl-3">
                      {TEAM_FLAVOR[selectedTeam.abbreviation]}
                    </p>
                  )}

                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-white/35 font-semibold mb-2">
                      Preview do elenco
                    </div>
                    {loadingPreview ? (
                      <div className="flex items-center gap-2 text-white/35 text-xs py-4">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Carregando titulares…
                      </div>
                    ) : previewPlayers.length > 0 ? (
                      <div className="space-y-1.5">
                        {previewPlayers.map((p) => (
                          <div
                            key={p.id}
                            className="flex items-center gap-2 p-1.5 rounded-sm bg-black/35 border border-white/5"
                          >
                            <PlayerPortrait name={p.name} size="xs" />
                            <div className="min-w-0 flex-1">
                              <div className="text-xs font-semibold text-white truncate">
                                {p.name}
                              </div>
                              <div className="flex items-center gap-1 text-[9px] text-white/40">
                                <RoleIcon role={p.role} size={10} className="text-lol-gold/70" />
                                {ROLE_LABELS[p.role] || p.role}
                              </div>
                            </div>
                            <div className="font-mono text-xs font-bold text-emerald-400">
                              {p.currentAbility}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[11px] text-white/30 font-mono py-2">
                        Sem preview de jogadores (seed offline?).
                      </p>
                    )}
                  </div>

                  <div className="mt-auto pt-2 border-t border-white/5">
                    <div className="text-[10px] text-white/35 font-mono">
                      Coach designado:{' '}
                      <span className="text-lol-gold-soft">
                        {managerName.trim() || '—'}
                      </span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center text-white/30 py-8">
                  <Shield className="w-10 h-10 mb-3 opacity-40" />
                  <p className="text-sm">Selecione uma organização</p>
                  <p className="text-[11px] mt-1 max-w-[200px]">
                    O preview do elenco e o splash do clube aparecem aqui.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
