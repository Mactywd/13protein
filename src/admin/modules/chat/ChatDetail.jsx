import { useEffect, useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { authFetch } from '../../auth';
import Message from '../../../components/Message/Message';
import ConversationContext from '../../../contexts/ConversationContext';
import { formatDuration, formatCost, profileLabel, STATUS_LABEL, EVAL_LABEL, OUTCOME_LABEL } from './format';
import '../../../globals.css';
import './ChatModule.css';

const noopContext = { handleMessageSend: () => {}, handleEnd: () => {} };

export default function ChatDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    (async () => {
      const r = await authFetch(`/api/chats/${encodeURIComponent(id)}`);
      if (!cancelled && r.ok) setDetail(await r.json());
    })();
    return () => { cancelled = true; };
  }, [id]);

  function goBack() {
    // Came from the list (in-app history): back preserves its query-param filters.
    if (location.key !== 'default') navigate(-1);
    else navigate('/chat');
  }

  return (
    <div className="chat-admin-page">
      <div className="chat-admin-container">
        <button className="chat-admin-back" onClick={goBack}>
          ← Torna alla lista
        </button>
        {!detail ? (
          <p>Caricamento…</p>
        ) : (
          <>
            <div className="chat-admin-meta">
              {detail.session.is_testing && <span className="chat-admin-testing-badge">TESTING</span>}
              <span>Stato: <b>{STATUS_LABEL[detail.session.status] || detail.session.status}</b></span>
              <span>Profilo: <b>{profileLabel(detail.session) || '—'}</b></span>
              <span>Categoria: <b>{detail.session.category || '—'}</b></span>
              <span>Formato: <b>{detail.session.format || '—'}</b></span>
              <span>Preventivo: <b>{detail.session.quote_requested ? 'sì' : 'no'}</b></span>
              <span>Durata: <b>{formatDuration(detail.session.duration_seconds)}</b></span>
              <span>Costo: <b>{formatCost(detail.session.total_cost)}</b></span>
              <span>Token: <b>{detail.session.prompt_tokens + detail.session.completion_tokens}</b></span>
            </div>
            <div className="chat-admin-eval">
              <h3>Evaluation</h3>
              {!detail.evaluation ? (
                <p className="chat-admin-muted">Nessuna evaluation (chat non completata).</p>
              ) : detail.evaluation.status === 'done' ? (
                <>
                  {detail.evaluation.outcome && (
                    <span className={`chat-admin-outcome-badge chat-admin-outcome-${detail.evaluation.outcome}`}>
                      {OUTCOME_LABEL[detail.evaluation.outcome] || detail.evaluation.outcome}
                    </span>
                  )}
                  <p>{detail.evaluation.summary}</p>
                  <p>Preventivo richiesto: <b>{detail.evaluation.quote_requested ? 'sì' : 'no'}</b></p>
                  {detail.evaluation.friction_note ? (
                    <p className="chat-admin-friction-note">{detail.evaluation.friction_note}</p>
                  ) : (
                    <p className="chat-admin-muted">Nessuna frizione rilevata.</p>
                  )}
                  {(detail.evaluation.cost != null || detail.evaluation.model) && (
                    <p className="chat-admin-muted">
                      {detail.evaluation.model ? `Modello: ${detail.evaluation.model}` : ''}
                      {detail.evaluation.cost != null ? ` · Costo eval: ${formatCost(detail.evaluation.cost)}` : ''}
                    </p>
                  )}
                </>
              ) : (
                <p className="chat-admin-muted">{EVAL_LABEL[detail.evaluation.status] || detail.evaluation.status}…</p>
              )}
            </div>
            <div className="chat-admin-transcript">
              <h3>Transcript</h3>
              <ConversationContext.Provider value={noopContext}>
                {detail.messages.map((m, i) => (
                  <div key={i} style={{ display: 'flex' }}>
                    <Message data={m} isLastMessage={false} setUserCanWrite={() => {}} />
                  </div>
                ))}
              </ConversationContext.Provider>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
