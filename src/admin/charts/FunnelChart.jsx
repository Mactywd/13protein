import {
  ResponsiveContainer, BarChart as RBarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  LabelList,
} from 'recharts';
import { FUNNEL_RAMP, INK } from './theme';

// Funnel come barre orizzontali decrescenti (rampa ordinale blu): per ogni
// step mostra a destra valore, % rispetto allo step precedente e % sul totale
// (primo step del funnel).
export default function FunnelChart({ stages, height = 200 }) {
  if (!stages?.length) return null;
  const first = stages[0].value;
  const data = stages.map((s, i) => ({
    ...s,
    pctOfPrev: i === 0 ? null : (stages[i - 1].value ? s.value / stages[i - 1].value : 0),
    pctOfTotal: i === 0 ? null : (first ? s.value / first : 0),
  }));
  const endLabel = (props) => {
    const { x, y, width, height: h, index } = props;
    const row = data[index];
    const pcts = row.pctOfPrev == null ? '' :
      ` · ${(100 * row.pctOfPrev).toFixed(1)}% del prec. · ${(100 * row.pctOfTotal).toFixed(1)}% del tot.`;
    return (
      <text x={x + width + 6} y={y + h / 2} dominantBaseline="central" fontSize={12} fill={INK.text}>
        {row.value.toLocaleString('it-IT')}{pcts}
      </text>
    );
  };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RBarChart data={data} layout="vertical" margin={{ top: 4, right: 230, bottom: 4, left: 8 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="label" tick={{ fontSize: 12, fill: INK.text }} tickLine={false} axisLine={false} width={130} />
        <Tooltip formatter={(v) => v.toLocaleString('it-IT')} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={26} isAnimationActive={false}>
          {data.map((_, i) => <Cell key={i} fill={FUNNEL_RAMP[i % FUNNEL_RAMP.length]} />)}
          <LabelList content={endLabel} />
        </Bar>
      </RBarChart>
    </ResponsiveContainer>
  );
}
