// Card di sezione del Resoconto: titolo + contenuto. Ogni sezione la usa e
// ritorna null se i suoi dati mancano, così la card sparisce senza buchi.
export default function SectionCard({ title, children }) {
  return (
    <section className="resoconto-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
