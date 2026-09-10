import { describe, it, expect } from 'vitest';
import { PROFILES, parseProfiles, serializeProfiles, matchesProfiles, matchesStatus } from './filters';

const idea = { profile: 'product_idea' };
const nuovo = { profile: 'new_brand' };
const inizializzata = { profile: null };

describe('parseProfiles', () => {
  it('restituisce vuoto per parametro assente o vuoto', () => {
    expect(parseProfiles(null)).toEqual([]);
    expect(parseProfiles('')).toEqual([]);
    expect(parseProfiles(undefined)).toEqual([]);
  });

  it('legge una lista separata da virgole', () => {
    expect(parseProfiles('product_idea,new_brand')).toEqual(['product_idea', 'new_brand']);
  });

  it('scarta gli slug sconosciuti e i duplicati', () => {
    expect(parseProfiles('product_idea,inventato,product_idea, new_brand '))
      .toEqual(['product_idea', 'new_brand']);
  });
});

describe('serializeProfiles', () => {
  it('serializza una selezione parziale', () => {
    expect(serializeProfiles(['product_idea', 'new_brand'])).toBe('product_idea,new_brand');
  });

  it('normalizza a nulla la selezione vuota e quella completa', () => {
    expect(serializeProfiles([])).toBeNull();
    expect(serializeProfiles(PROFILES.map((p) => p.value))).toBeNull();
  });
});

describe('matchesProfiles', () => {
  it("accetta tutto quando non c'è selezione, comprese le chat senza profilo", () => {
    for (const chat of [idea, nuovo, inizializzata]) {
      expect(matchesProfiles(chat, [])).toBe(true);
    }
  });

  it('filtra sul profilo selezionato', () => {
    expect(matchesProfiles(idea, ['product_idea'])).toBe(true);
    expect(matchesProfiles(nuovo, ['product_idea'])).toBe(false);
    expect(matchesProfiles(nuovo, ['product_idea', 'new_brand'])).toBe(true);
  });

  it('esclude le chat senza profilo quando un filtro è attivo', () => {
    expect(matchesProfiles(inizializzata, ['product_idea'])).toBe(false);
  });
});

describe('matchesStatus', () => {
  it('non filtra senza valore o con un valore ignoto', () => {
    expect(matchesStatus({ status: 'in_corso' }, undefined)).toBe(true);
    expect(matchesStatus({ status: 'in_corso' }, 'boh')).toBe(true);
  });

  it('filtra le completate', () => {
    expect(matchesStatus({ status: 'completata' }, 'completed')).toBe(true);
    expect(matchesStatus({ status: 'abbandonata' }, 'completed')).toBe(false);
  });

  it('filtra quelle con preventivo richiesto', () => {
    expect(matchesStatus({ quote_requested: true }, 'quoted')).toBe(true);
    expect(matchesStatus({ quote_requested: false }, 'quoted')).toBe(false);
    expect(matchesStatus({}, 'quoted')).toBe(false);
  });
});
