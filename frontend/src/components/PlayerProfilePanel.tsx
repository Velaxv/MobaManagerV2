/**
 * Perfil de jogador + análise de atributos (item 3 do design PDF).
 * Retrato à esquerda, radar + pool + notas do coach à direita.
 */
import { X, Headphones } from 'lucide-react';
import { AttributeRadar, playerToRadarAxes } from './AttributeRadar';
import { ChampionImage } from './ChampionImage';
import { PlayerPortrait } from './PlayerPortrait';
import { RoleIcon } from './RoleIcon';
import { ROLE_LABELS } from '../lib/champions';
import type { Player } from '../store/useGameStore';
import { PlayerRole } from '../types/game';

interface PlayerProfilePanelProps {
  player: Player;
  teamName?: string;
  onClose: () => void;
}

function formatPa(p: Player): string {
  if (p.potentialAbilityKnown && p.potentialAbility != null) {
    return String(p.potentialAbility);
  }
  if (p.potentialAbilityMin != null && p.potentialAbilityMax != null) {
    return `${p.potentialAbilityMin}–${p.potentialAbilityMax}`;
  }
  return '???';
}

export function PlayerProfilePanel({ player, teamName, onClose }: PlayerProfilePanelProps) {
  const axes = playerToRadarAxes(player);
  const mains = (player.championPool || []).filter((c) => c.tier === 'MAIN').slice(0, 5);
  const secs = (player.championPool || []).filter((c) => c.tier === 'SECONDARY').slice(0, 4);
  const poolRows = [...mains, ...secs].slice(0, 5);

  const coachNotes: string[] = [];
  if (player.burnoutMeter > 70) coachNotes.push('Burnout elevado — priorize REST.');
  if (player.visualFatigue > 70) coachNotes.push('Fadiga visual alta — mecânica comprometida.');
  if ((player.formAvg ?? 7) < 6) coachNotes.push('Forma recente baixa — reforçar scrims leves.');
  if ((player.formAvg ?? 0) >= 7.5) coachNotes.push('Em boa fase — manter ritmo de treino.');
  if ((player.championPool?.length || 0) < 4) {
    coachNotes.push('Expandir pool de campeões (diversidade).');
  }
  if (player.focus < 10) coachNotes.push('Melhorar posicionamento em teamfights.');
  if (coachNotes.length === 0) {
    coachNotes.push('Manter consistência e comunicação no early.');
    coachNotes.push('Expandir flex picks para o draft.');
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal
      aria-label={`Perfil de ${player.name}`}
    >
      <div
        className="hq-profile-card relative w-full max-w-4xl max-h-[92vh] overflow-hidden flex flex-col md:flex-row"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Left: portrait / HQ vibe */}
        <div className="relative md:w-[42%] min-h-[240px] md:min-h-[420px] hq-profile-portrait">
          <div className="absolute inset-0 hq-profile-portrait-bg" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#071422] via-[#071422]/40 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-[#071422]/90 hidden md:block" />

          <div className="relative h-full flex flex-col justify-end p-5 sm:p-6">
            <div className="absolute top-4 right-4 md:hidden">
              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-sm border border-white/20 bg-black/50 text-white/70 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-end gap-4 mb-3">
              <div className="relative">
                <PlayerPortrait
                  name={player.name}
                  size="xl"
                  className="!w-28 !h-28 sm:!w-36 sm:!h-36 ring-2 ring-lol-hq-cyan/40 shadow-hq-cyan"
                />
                <div className="absolute -bottom-1 -right-1 bg-black/80 border border-lol-hq-cyan/40 rounded-full p-1">
                  <Headphones className="w-3.5 h-3.5 text-lol-hq-cyan" />
                </div>
              </div>
              <div className="min-w-0 pb-1">
                <div className="flex items-center gap-1.5 mb-1">
                  <RoleIcon role={player.role as PlayerRole} size={14} className="text-lol-hq-cyan" />
                  <span className="text-[10px] font-mono uppercase tracking-widest text-lol-hq-cyan/80">
                    {ROLE_LABELS[player.role as PlayerRole] || player.role}
                  </span>
                  {player.isStarter && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded-sm bg-lol-hq-cyan/20 text-lol-hq-cyan border border-lol-hq-cyan/30">
                      TITULAR
                    </span>
                  )}
                </div>
                <h2 className="font-display text-xl sm:text-2xl font-bold text-white leading-tight tracking-[0.08em] uppercase">
                  {player.name}
                </h2>
                <p className="text-[11px] text-white/45 font-mono mt-0.5">
                  {player.age}a · {player.nationality}
                  {teamName ? ` · ${teamName}` : ''}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="hq-stat-chip">
                <div className="text-[9px] text-white/40 uppercase">CA</div>
                <div className="text-lg font-bold text-emerald-400 font-mono">
                  {player.currentAbility}
                </div>
              </div>
              <div className="hq-stat-chip">
                <div className="text-[9px] text-white/40 uppercase">PA</div>
                <div className="text-lg font-bold text-white font-mono">{formatPa(player)}</div>
              </div>
              <div className="hq-stat-chip">
                <div className="text-[9px] text-white/40 uppercase">Forma</div>
                <div className="text-lg font-bold text-lol-hq-cyan font-mono">
                  {player.formAvg != null ? player.formAvg.toFixed(1) : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: data panel */}
        <div className="flex-1 flex flex-col min-w-0 bg-hq-panel border-l border-lol-hq-cyan/15">
          <div className="hq-panel-header flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-lol-hq-cyan">
              Performance Attributes
            </span>
            <button
              type="button"
              onClick={onClose}
              className="hidden md:flex p-1 rounded-sm text-white/40 hover:text-white border border-transparent hover:border-white/15"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <AttributeRadar axes={axes} size={200} className="shrink-0" />
              <div className="flex-1 w-full grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                {axes.map((a) => (
                  <div
                    key={a.key}
                    className="flex justify-between px-2 py-1.5 rounded-sm bg-black/35 border border-white/5"
                  >
                    <span className="text-white/40 uppercase tracking-wide">{a.label}</span>
                    <span className="text-lol-hq-cyan font-bold">{a.value.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Champion pool table */}
            <div className="hq-glass-inset">
              <div className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-semibold mb-2 px-0.5">
                Champions · Pool
              </div>
              <table className="w-full text-[11px] font-mono">
                <thead>
                  <tr className="text-white/35 text-left border-b border-white/10">
                    <th className="py-1.5 font-medium">Champ</th>
                    <th className="py-1.5 font-medium">Tier</th>
                    <th className="py-1.5 font-medium text-right">Comfort</th>
                  </tr>
                </thead>
                <tbody>
                  {poolRows.length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-3 text-white/30 text-center">
                        Pool ainda não mapeado
                      </td>
                    </tr>
                  )}
                  {poolRows.map((c) => (
                    <tr key={c.champion} className="border-b border-white/[0.04]">
                      <td className="py-1.5">
                        <div className="flex items-center gap-2">
                          <ChampionImage name={c.champion} variant="ban" className="!w-6 !h-6" />
                          <span className="text-white/85">{c.champion}</span>
                        </div>
                      </td>
                      <td className="py-1.5">
                        <span
                          className={
                            c.tier === 'MAIN'
                              ? 'text-emerald-400'
                              : 'text-sky-400'
                          }
                        >
                          {c.tier}
                        </span>
                      </td>
                      <td className="py-1.5 text-right text-white/50">
                        {c.tier === 'MAIN' ? '★★★' : '★★'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Fatigue meters */}
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  ['Burnout', player.burnoutMeter, 'bg-lol-red-side'],
                  ['Visual', player.visualFatigue, 'bg-amber-500'],
                  ['Mental', player.mentalFatigue, 'bg-violet-500'],
                ] as const
              ).map(([label, val, bar]) => (
                <div key={label} className="hq-glass-inset !p-2">
                  <div className="flex justify-between text-[9px] text-white/40 mb-1">
                    <span>{label}</span>
                    <span className="font-mono">{Math.round(val)}%</span>
                  </div>
                  <div className="stat-bar">
                    <div className={`stat-bar-fill ${bar}`} style={{ width: `${val}%` }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Coach notes */}
            <div className="hq-glass-inset border-lol-hq-cyan/25">
              <div className="text-[10px] uppercase tracking-[0.15em] text-lol-hq-cyan font-semibold mb-2 font-mono">
                Coach&apos;s Notes
              </div>
              <ul className="space-y-1.5 text-[11px] text-white/65 leading-snug">
                {coachNotes.map((n) => (
                  <li key={n} className="flex gap-2">
                    <span className="text-lol-hq-orange shrink-0">▸</span>
                    <span>{n}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
