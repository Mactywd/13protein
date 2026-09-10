import SectionCard from './SectionCard';
import PieChart from '../../../charts/PieChart';
import { OUTCOME_COLORS } from '../../../charts/theme';
import { formatInt, formatPct, formatDuration } from '../format';

export default function EsitiSection({ title, stats }) {
  const o = stats?.outcomes;
  if (!o) return null;
  const slices = [
    { name: 'Completate', value: o.completed, color: OUTCOME_COLORS.completate },
    { name: 'Abbandonate', value: o.abandoned, color: OUTCOME_COLORS.abbandonate },
    { name: 'Inizializzate', value: o.initialized, color: OUTCOME_COLORS.inizializzate },
  ];
  return (
    <SectionCard title={title}>
      <div className="resoconto-stats">
        <div><span>Sessioni totali</span><b>{formatInt(stats.total_sessions)}</b></div>
        <div><span>Completate</span><b>{formatInt(o.completed)} ({formatPct(o.completed_share)})</b></div>
        <div><span>Abbandonate</span><b>{formatInt(o.abandoned)} ({formatPct(o.abandoned_share)})</b></div>
        <div><span>Inizializzate</span><b>{formatInt(o.initialized)} ({formatPct(o.initialized_share)})</b></div>
        <div><span>Durata mediana</span><b>{formatDuration(stats.duration?.median_seconds)}</b></div>
        <div><span>Durata media</span><b>{formatDuration(stats.duration?.mean_seconds)}</b></div>
      </div>
      <PieChart data={slices} valueFormatter={formatInt} />
    </SectionCard>
  );
}
