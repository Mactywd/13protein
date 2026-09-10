import SectionCard from './SectionCard';
import FunnelChart from '../../../charts/FunnelChart';

export default function FunnelSection({ title, funnel }) {
  if (!funnel) return null;
  const stages = [
    { label: 'Page views', value: funnel.page_views || 0 },
    { label: 'Visitatori unici', value: funnel.unique_visitors || 0 },
    { label: 'CTA click', value: funnel.cta_clicks || 0 },
    { label: 'Chat completate', value: funnel.chat_completes || 0 },
    { label: 'Preventivi richiesti', value: funnel.quote_requests || 0 },
  ];
  return (
    <SectionCard title={title}>
      <FunnelChart stages={stages} height={240} />
    </SectionCard>
  );
}
