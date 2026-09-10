import FunnelSection from './FunnelSection';
import EsitiSection from './EsitiSection';
import QualificazioneSection from './QualificazioneSection';
import TopicSection from './TopicSection';
import SettimanaSection from './SettimanaSection';
import DispositiviSection from './DispositiviSection';

// Aggiungere una sezione = un file nuovo + una entry qui.
export const REPORT_SECTIONS = [
  { id: 'funnel', title: '📈 Traffico & Funnel', Component: FunnelSection },
  { id: 'dispositivi', title: '📱 Dispositivi & browser', Component: DispositiviSection },
  { id: 'esiti', title: '🥧 Esiti delle conversazioni', Component: EsitiSection },
  { id: 'qualificazione', title: '🧭 Qualificazione', Component: QualificazioneSection },
  { id: 'topic', title: '📚 Knowledgebase & preventivi', Component: TopicSection },
  { id: 'settimana', title: '📅 Andamento settimanale', Component: SettimanaSection },
];
