import {
  ResponsiveContainer, BarChart as RBarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from 'recharts';
import { SERIES, INK } from './theme';

const AXIS = { fontSize: 12, fill: INK.muted };

// Bar chart a serie singola. horizontal=true → barre orizzontali (categorie
// sull'asse Y), per etichette lunghe (essenze, percorsi).
export default function BarChart({
  data, xKey, yKey, color = SERIES.blue,
  horizontal = false, height = 220, valueFormatter = (v) => v,
}) {
  if (!data?.length) return null;
  const bars = (
    <Bar dataKey={yKey} fill={color} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={28} />
  );
  return (
    <ResponsiveContainer width="100%" height={height}>
      {horizontal ? (
        <RBarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke={INK.grid} />
          <XAxis type="number" tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey={xKey} tick={{ ...AXIS, fill: INK.text }} tickLine={false} axisLine={false} width={150} />
          <Tooltip formatter={(v) => valueFormatter(v)} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
          {bars}
        </RBarChart>
      ) : (
        <RBarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid vertical={false} stroke={INK.grid} />
          <XAxis dataKey={xKey} tick={AXIS} tickLine={false} axisLine={{ stroke: INK.grid }} interval={0} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} width={36} />
          <Tooltip formatter={(v) => valueFormatter(v)} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
          {bars}
        </RBarChart>
      )}
    </ResponsiveContainer>
  );
}
