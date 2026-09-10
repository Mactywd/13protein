import { ResponsiveContainer, PieChart as RPieChart, Pie, Cell, Legend, Tooltip } from 'recharts';
import { INK } from './theme';

// Torta a ciambella per distribuzioni a poche categorie (esiti conversazioni).
// data: [{name, value, color}]. Etichetta diretta con % + legenda: l'identità
// non è mai affidata al solo colore.
export default function PieChart({ data, height = 240, valueFormatter = (v) => v }) {
  const rows = (data || []).filter((d) => d.value > 0);
  if (!rows.length) return null;
  const total = rows.reduce((s, d) => s + d.value, 0);
  const pctLabel = ({ name, value }) => `${name} ${(100 * value / total).toFixed(0)}%`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RPieChart>
        <Pie
          data={rows} dataKey="value" nameKey="name"
          innerRadius="45%" outerRadius="70%" paddingAngle={2}
          stroke="#fff" strokeWidth={2}
          label={pctLabel} labelLine={{ stroke: INK.grid }}
          isAnimationActive={false}
        >
          {rows.map((d, i) => <Cell key={i} fill={d.color} />)}
        </Pie>
        <Tooltip formatter={(v) => valueFormatter(v)} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12, color: INK.text }} />
      </RPieChart>
    </ResponsiveContainer>
  );
}
