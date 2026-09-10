import SectionCard from './SectionCard';
import PieChart from '../../../charts/PieChart';
import { PALETTE } from '../../../charts/theme';
import { formatInt, DEVICE_LABEL, BROWSER_LABEL } from '../format';

// Le fette seguono l'ordine delle mappe di etichette, non quello ricevuto dal
// server: così il colore di una categoria non cambia al variare delle date.
// PieChart scarta da sé le fette a zero.
function slices(counts, labels) {
  return Object.entries(labels).map(([key, name], i) => ({
    name,
    value: counts?.[key] || 0,
    color: PALETTE[i % PALETTE.length],
  }));
}

export default function DispositiviSection({ title, funnel }) {
  const seg = funnel?.visitor_segments;
  if (!seg?.base) return null;
  return (
    <SectionCard title={title}>
      <div className="resoconto-charts-2col">
        <div>
          <h3>Dispositivo</h3>
          <PieChart data={slices(seg.device, DEVICE_LABEL)} valueFormatter={formatInt} height={240} />
        </div>
        <div>
          <h3>Browser</h3>
          <PieChart data={slices(seg.browser, BROWSER_LABEL)} valueFormatter={formatInt} height={240} />
        </div>
      </div>
      <p className="resoconto-section-note">
        Base: {formatInt(seg.base)} visitatori unici con dato disponibile
        (su {formatInt(funnel.unique_visitors)} del periodo).
      </p>
    </SectionCard>
  );
}
