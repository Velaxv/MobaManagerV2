import { useEffect, useState } from 'react';
import { Briefcase, UserPlus } from 'lucide-react';
import { useGameStore } from '../store/useGameStore';
import { api, type StaffCandidate, type StaffMember } from '../services/api';
import { HubPageHeader } from '../components/HubPageHeader';

/**
 * Comissão técnica — contratar/demitir e ver poderes no motor.
 */
export function Staff() {
  const manager = useGameStore((s) => s.manager);
  const myTeamId = manager?.teamId;

  const [staffList, setStaffList] = useState<StaffMember[]>([]);
  const [staffCandidates, setStaffCandidates] = useState<StaffCandidate[]>([]);
  const [staffBusy, setStaffBusy] = useState<string | null>(null);
  const [staffMsg, setStaffMsg] = useState<string | null>(null);
  const [staffPower, setStaffPower] = useState<{
    avg_meta_reading?: number;
    scout_mult?: number;
    coach_comms_max?: number;
    powers?: string[];
    burnout_recovery_bonus?: number;
    draft_confidence?: number;
  } | null>(null);

  const reloadStaff = async () => {
    if (!myTeamId) return;
    try {
      const [st, cand] = await Promise.all([
        api.getTeamStaff(myTeamId),
        api.getStaffCandidates(myTeamId),
      ]);
      setStaffList(st.staff || []);
      setStaffPower(st.power || null);
      setStaffCandidates((cand.candidates || []).slice(0, 8));
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    void reloadStaff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myTeamId]);

  return (
    <div className="flex flex-col gap-4">
      <HubPageHeader
        icon={Briefcase}
        title="Comissão técnica"
        subtitle="Pessoas fora do elenco: contratar/demitir coaches. Efeito no scouting, draft tips e coach comms da live."
        actions={
          <button
            type="button"
            onClick={() => void reloadStaff()}
            className="text-[10px] uppercase tracking-wide text-white/50 border border-white/10 px-3 py-1.5 rounded-sm hover:border-violet-400/40 hover:text-violet-200"
          >
            Atualizar
          </button>
        }
      />

      {!myTeamId ? (
        <p className="text-sm text-white/40 font-mono p-6">Selecione um time na carreira.</p>
      ) : (
        <div className="panel-lol border-violet-500/20 bg-violet-950/15">
          <div className="panel-lol-header">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-violet-300" />
              <span className="text-xs font-semibold uppercase tracking-wider text-violet-200">
                Plantel técnico
              </span>
            </div>
            <span className="text-[10px] text-white/35 font-mono">
              meta {staffPower?.avg_meta_reading ?? '—'} · scout ×
              {staffPower?.scout_mult ?? '—'}
            </span>
          </div>
          <div className="p-3 space-y-3">
            <p className="text-[11px] text-white/45 leading-relaxed">
              Meta reading melhora scouting e dicas de draft; performance coach ajuda no burnout;
              head coach define quantos coach comms na live (pré-partida / early).
            </p>

            <ul className="flex flex-col gap-1.5 max-h-[220px] overflow-y-auto">
              {staffList.length === 0 ? (
                <li className="text-xs text-white/35 font-mono p-2">
                  Sem staff — contrate candidatos abaixo.
                </li>
              ) : (
                staffList.map((s) => (
                  <li
                    key={s.id}
                    className="flex flex-wrap items-center gap-2 p-2.5 rounded-sm border border-white/5 bg-black/30 text-[11px]"
                  >
                    <span className="font-semibold text-white min-w-[6rem]">{s.name}</span>
                    <span className="text-violet-300/80 text-[10px] uppercase">
                      {s.role_label || s.role}
                    </span>
                    <span className="text-white/35 font-mono">
                      meta {s.meta_reading} · comm {s.communication} · €
                      {Math.round(s.monthly_cost).toLocaleString('pt-BR')}/mês
                    </span>
                    <button
                      type="button"
                      disabled={!!staffBusy}
                      onClick={async () => {
                        if (!confirm(`Demitir ${s.name}?`)) return;
                        setStaffBusy(s.id);
                        setStaffMsg(null);
                        try {
                          await api.fireStaff(myTeamId, s.id);
                          setStaffMsg(`Demitido: ${s.name}`);
                          await reloadStaff();
                        } catch (e) {
                          setStaffMsg(e instanceof Error ? e.message : 'Erro ao demitir');
                        } finally {
                          setStaffBusy(null);
                        }
                      }}
                      className="ml-auto text-[9px] uppercase text-lol-red-side border border-lol-red-side/30 px-2 py-1 rounded-sm hover:bg-red-950/30 disabled:opacity-40"
                    >
                      Demitir
                    </button>
                  </li>
                ))
              )}
            </ul>

            {staffPower && (staffPower.powers?.length || staffPower.coach_comms_max) && (
              <div className="rounded-sm border border-violet-500/20 bg-black/25 p-2.5 text-[10px] font-mono text-violet-200/80 space-y-0.5">
                <div>
                  Poderes · comms máx {staffPower.coach_comms_max ?? '—'} · scout ×
                  {staffPower.scout_mult ?? '—'} · draft conf{' '}
                  {staffPower.draft_confidence != null
                    ? Math.round(staffPower.draft_confidence * 100)
                    : '—'}
                  %
                  {staffPower.burnout_recovery_bonus
                    ? ` · recovery +${staffPower.burnout_recovery_bonus}`
                    : ''}
                </div>
                {(staffPower.powers || []).map((p) => (
                  <div key={p} className="text-white/40">
                    · {p}
                  </div>
                ))}
              </div>
            )}

            <div className="border-t border-white/5 pt-3 space-y-1.5">
              <div className="text-[10px] uppercase tracking-wider text-white/40 flex items-center gap-1">
                <UserPlus className="w-3 h-3" /> Candidatos no mercado
              </div>
              <ul className="flex flex-col gap-1 max-h-[240px] overflow-y-auto">
                {staffCandidates.map((c) => (
                  <li
                    key={c.candidate_id}
                    className="flex flex-wrap items-center gap-2 p-2.5 rounded-sm border border-violet-500/15 bg-black/25 text-[11px]"
                  >
                    <span className="font-semibold text-white/90">{c.name}</span>
                    <span className="text-violet-300/70 text-[10px]">{c.role_label}</span>
                    <span className="text-white/35 font-mono">
                      meta {c.meta_reading} · taxa €
                      {Math.round(c.signing_fee).toLocaleString('pt-BR')}
                    </span>
                    <button
                      type="button"
                      disabled={!!staffBusy || !c.slot_available}
                      title={!c.slot_available ? 'Slot do cargo cheio' : 'Contratar'}
                      onClick={async () => {
                        setStaffBusy(c.candidate_id);
                        setStaffMsg(null);
                        try {
                          const res = await api.hireStaff(myTeamId, {
                            name: c.name,
                            role: c.role,
                            meta_reading: c.meta_reading,
                            communication: c.communication,
                            candidate_id: c.candidate_id,
                          });
                          setStaffMsg(res.message || `Contratado: ${c.name}`);
                          await reloadStaff();
                          void useGameStore.getState().refreshRosterAndMarket?.();
                        } catch (e) {
                          setStaffMsg(e instanceof Error ? e.message : 'Erro ao contratar');
                        } finally {
                          setStaffBusy(null);
                        }
                      }}
                      className="ml-auto text-[9px] uppercase text-emerald-400 border border-emerald-700/40 px-2 py-1 rounded-sm hover:bg-emerald-950/40 disabled:opacity-40"
                    >
                      {staffBusy === c.candidate_id ? '…' : 'Contratar'}
                    </button>
                  </li>
                ))}
              </ul>
              {staffMsg && (
                <span className="text-[10px] font-mono text-white/50 block pt-1">{staffMsg}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
