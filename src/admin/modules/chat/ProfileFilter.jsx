import { useEffect, useRef, useState } from 'react';
import { PROFILES } from './filters';

/**
 * Selezione multipla dei profili.
 *
 * Un `<select multiple>` nativo richiede ctrl-click e tiene la lista sempre
 * aperta dentro la barra dei filtri: qui serve un bottone che apre un pannello
 * di checkbox, con l'etichetta che riassume la selezione.
 */
export default function ProfileFilter({ selected, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    function onDocClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    function onKey(e) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  function toggle(value) {
    onChange(selected.includes(value)
      ? selected.filter((s) => s !== value)
      : [...selected, value]);
  }

  let summary;
  if (selected.length === 0 || selected.length === PROFILES.length) summary = 'tutti';
  else if (selected.length === 1) summary = PROFILES.find((p) => p.value === selected[0]).label;
  else summary = `${selected.length} profili`;

  return (
    <div className="chat-admin-paths" ref={ref}>
      <button
        type="button"
        className="chat-admin-paths-button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        Profili: {summary} ▾
      </button>
      {open && (
        <div className="chat-admin-paths-panel" role="group" aria-label="Profili">
          {PROFILES.map((p) => (
            <label key={p.value}>
              <input
                type="checkbox"
                checked={selected.includes(p.value)}
                onChange={() => toggle(p.value)}
              />
              {p.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
