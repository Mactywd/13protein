import SectionCard from './SectionCard';
import PieChart from '../../../charts/PieChart';
import { PALETTE } from '../../../charts/theme';
import { formatInt, WEEKDAY_LABEL } from '../format';

export default function SettimanaSection({ title, stats }) {
  const days = stats?.by_weekday;
  if (!days?.length) return null;
  const slices = days.map((d, i) => ({
    name: WEEKDAY_LABEL[d.weekday] || String(d.weekday),
    value: d.count,
    color: PALETTE[i % PALETTE.length],
  }));
  return (
    <SectionCard title={title}>
      <PieChart data={slices} valueFormatter={formatInt} height={260} />
    </SectionCard>
  );
}
