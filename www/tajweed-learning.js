/*
 * Siraj Tajweed Learning Engine v1
 *
 * Deterministic, local spaced repetition. Curriculum text is deliberately kept
 * outside this file so every riwayah/tariq/wajh/edition remains an independent,
 * reviewable data layer.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SirajTajweedLearning = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SCHEMA_VERSION = 1;
  const DAY_MS = 24 * 60 * 60 * 1000;
  const TEN_MINUTES_MS = 10 * 60 * 1000;
  const MAX_INTERVAL_DAYS = 365;
  const RATINGS = Object.freeze(['again', 'hard', 'good', 'easy']);
  const DEFAULT_CONFIG = Object.freeze({ newPerDay: 5, reviewsPerDay: 20 });

  function clamp(value, low, high) {
    const number = Number(value);
    if (!Number.isFinite(number)) return low;
    return Math.min(high, Math.max(low, number));
  }

  function token(value, max = 64) {
    const text = String(value == null ? '' : value).trim().toLowerCase();
    return /^[a-z0-9][a-z0-9_.-]*$/.test(text) && text.length <= max ? text : null;
  }

  function normalizeScope(value) {
    if (!value || typeof value !== 'object') return null;
    const scope = {
      riwayah: token(value.riwayah),
      tariq: token(value.tariq),
      wajh: token(value.wajh),
      edition: token(value.edition),
    };
    return Object.values(scope).every(Boolean) ? scope : null;
  }

  function scopeKey(value) {
    const scope = normalizeScope(value);
    return scope ? `${scope.riwayah}/${scope.tariq}/${scope.wajh}/${scope.edition}` : null;
  }

  function normalizeCard(value) {
    if (!value || typeof value !== 'object') return null;
    const id = token(value.id);
    const scope = normalizeScope(value.scope);
    if (!id || !scope) return null;
    return { ...value, id, scope, key: `${scopeKey(scope)}::${id}` };
  }

  function normalizeConfig(value) {
    const input = value && typeof value === 'object' ? value : {};
    return {
      newPerDay: Math.round(clamp(input.newPerDay == null
        ? DEFAULT_CONFIG.newPerDay : input.newPerDay, 1, 20)),
      reviewsPerDay: Math.round(clamp(input.reviewsPerDay == null
        ? DEFAULT_CONFIG.reviewsPerDay : input.reviewsPerDay, 5, 100)),
    };
  }

  function normalizeEntry(value) {
    const input = value && typeof value === 'object' ? value : {};
    return {
      dueAt: Math.max(0, Math.round(Number(input.dueAt) || 0)),
      intervalDays: clamp(input.intervalDays, 0, MAX_INTERVAL_DAYS),
      ease: clamp(input.ease == null ? 2.5 : input.ease, 1.3, 3),
      repetitions: Math.round(clamp(input.repetitions, 0, 10000)),
      lapses: Math.round(clamp(input.lapses, 0, 10000)),
      reviewCount: Math.round(clamp(input.reviewCount, 0, 1000000)),
      correctCount: Math.round(clamp(input.correctCount, 0, 1000000)),
      introducedAt: Math.max(0, Math.round(Number(input.introducedAt) || 0)),
      lastReviewedAt: Math.max(0, Math.round(Number(input.lastReviewedAt) || 0)),
      lastRating: RATINGS.includes(input.lastRating) ? input.lastRating : null,
      suspended: !!input.suspended,
      leech: !!input.leech,
    };
  }

  function normalizeState(value) {
    const input = value && typeof value === 'object' ? value : {};
    const progress = {};
    const source = input.progress && typeof input.progress === 'object' ? input.progress : {};
    Object.keys(source).slice(0, 20000).forEach((key) => {
      if (/^[a-z0-9_.\/-]+::[a-z0-9_.-]+$/.test(key) && key.length <= 320) {
        progress[key] = normalizeEntry(source[key]);
      }
    });
    return { schema: SCHEMA_VERSION, config: normalizeConfig(input.config), progress };
  }

  function localDateKey(value) {
    const date = value instanceof Date ? value : new Date(value);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  function sameLocalDay(a, b) {
    return a > 0 && b > 0 && localDateKey(a) === localDateKey(b);
  }

  function reviewedEntry(previous, rating, now) {
    const entry = normalizeEntry(previous);
    const first = !entry.introducedAt;
    const next = { ...entry };
    next.introducedAt = entry.introducedAt || now;
    next.lastReviewedAt = now;
    next.lastRating = rating;
    next.reviewCount += 1;
    if (rating !== 'again') next.correctCount += 1;

    if (rating === 'again') {
      next.repetitions = 0;
      next.intervalDays = 0;
      next.ease = clamp(entry.ease - 0.2, 1.3, 3);
      next.lapses = entry.lapses + (first ? 0 : 1);
      next.dueAt = now + TEN_MINUTES_MS;
    } else if (rating === 'hard') {
      next.repetitions = entry.repetitions;
      next.intervalDays = first ? 1 : clamp(Math.max(1, entry.intervalDays * 1.2), 1, MAX_INTERVAL_DAYS);
      next.ease = clamp(entry.ease - 0.15, 1.3, 3);
      next.dueAt = now + Math.round(next.intervalDays * DAY_MS);
    } else if (rating === 'good') {
      next.repetitions = entry.repetitions + 1;
      if (entry.repetitions === 0) next.intervalDays = 1;
      else if (entry.repetitions === 1) next.intervalDays = 3;
      else next.intervalDays = clamp(Math.round(entry.intervalDays * entry.ease), 1, MAX_INTERVAL_DAYS);
      next.dueAt = now + Math.round(next.intervalDays * DAY_MS);
    } else {
      next.repetitions = entry.repetitions + 1;
      next.ease = clamp(entry.ease + 0.15, 1.3, 3);
      next.intervalDays = first ? 4
        : clamp(Math.max(4, Math.round(Math.max(1, entry.intervalDays) * next.ease * 1.3)), 1, MAX_INTERVAL_DAYS);
      next.dueAt = now + Math.round(next.intervalDays * DAY_MS);
    }
    next.leech = next.lapses >= 8;
    return normalizeEntry(next);
  }

  function scopedCards(cards, scope) {
    const wanted = scopeKey(scope);
    if (!wanted) return [];
    const seen = new Set();
    return (Array.isArray(cards) ? cards : []).map(normalizeCard).filter((card) => {
      if (!card || scopeKey(card.scope) !== wanted || seen.has(card.key)) return false;
      seen.add(card.key);
      return true;
    });
  }

  function buildQueue(cards, stateValue, scope, nowValue = Date.now()) {
    const state = normalizeState(stateValue);
    const now = Number(nowValue);
    const all = scopedCards(cards, scope);
    const reviewedToday = Object.values(state.progress)
      .filter((entry) => sameLocalDay(entry.lastReviewedAt, now)).length;
    const introducedToday = Object.values(state.progress)
      .filter((entry) => sameLocalDay(entry.introducedAt, now)).length;
    const reviewSlots = Math.max(0, state.config.reviewsPerDay - reviewedToday);
    const newSlots = Math.max(0, state.config.newPerDay - introducedToday);

    const due = all.filter((card) => {
      const entry = state.progress[card.key];
      return entry && !entry.suspended && entry.dueAt <= now;
    }).sort((a, b) => state.progress[a.key].dueAt - state.progress[b.key].dueAt
      || a.id.localeCompare(b.id)).slice(0, reviewSlots)
      .map((card) => ({ card, kind: 'review', progress: state.progress[card.key] }));

    const fresh = all.filter((card) => !state.progress[card.key])
      .sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0)
        || a.id.localeCompare(b.id)).slice(0, newSlots)
      .map((card) => ({ card, kind: 'new', progress: null }));

    return [...due, ...fresh];
  }

  function statsForScope(stateValue, scope, nowValue = Date.now()) {
    const state = normalizeState(stateValue);
    const prefix = `${scopeKey(scope) || '!'}::`;
    const entries = Object.entries(state.progress)
      .filter(([key]) => key.startsWith(prefix)).map(([, value]) => value);
    const now = Number(nowValue);
    return {
      total: entries.length,
      due: entries.filter((entry) => !entry.suspended && entry.dueAt <= now).length,
      learning: entries.filter((entry) => !entry.suspended && entry.repetitions < 2).length,
      mature: entries.filter((entry) => !entry.suspended && entry.repetitions >= 2).length,
      suspended: entries.filter((entry) => entry.suspended).length,
      leeches: entries.filter((entry) => entry.leech).length,
      accuracy: entries.reduce((sum, entry) => sum + entry.reviewCount, 0)
        ? entries.reduce((sum, entry) => sum + entry.correctCount, 0)
          / entries.reduce((sum, entry) => sum + entry.reviewCount, 0)
        : 0,
      nextDueAt: entries.filter((entry) => !entry.suspended).reduce((minimum, entry) => (
        !minimum || entry.dueAt < minimum ? entry.dueAt : minimum
      ), 0),
    };
  }

  class TajweedLearningEngine {
    constructor(stateValue, options) {
      const state = normalizeState(stateValue);
      this.config = state.config;
      this.progress = state.progress;
      this.clock = options && typeof options.now === 'function' ? options.now : () => Date.now();
    }

    configure(patch) {
      this.config = normalizeConfig({ ...this.config, ...(patch || {}) });
      return { ...this.config };
    }

    queue(cards, scope) {
      return buildQueue(cards, this.snapshot(), scope, this.clock());
    }

    review(cardValue, rating) {
      const card = normalizeCard(cardValue);
      if (!card || !RATINGS.includes(rating)) return null;
      const now = this.clock();
      this.progress[card.key] = reviewedEntry(this.progress[card.key], rating, now);
      return { key: card.key, ...this.progress[card.key] };
    }

    suspend(cardValue, suspended = true) {
      const card = normalizeCard(cardValue);
      if (!card) return null;
      const entry = normalizeEntry(this.progress[card.key]);
      entry.suspended = !!suspended;
      this.progress[card.key] = entry;
      return { key: card.key, ...entry };
    }

    resetScope(scope) {
      const prefix = `${scopeKey(scope) || '!'}::`;
      Object.keys(this.progress).forEach((key) => {
        if (key.startsWith(prefix)) delete this.progress[key];
      });
    }

    stats(scope) {
      return statsForScope(this.snapshot(), scope, this.clock());
    }

    snapshot() {
      const progress = {};
      Object.keys(this.progress).forEach((key) => { progress[key] = { ...this.progress[key] }; });
      return { schema: SCHEMA_VERSION, config: { ...this.config }, progress };
    }
  }

  return Object.freeze({
    SCHEMA_VERSION,
    RATINGS,
    DEFAULT_CONFIG,
    TajweedLearningEngine,
    normalizeScope,
    scopeKey,
    normalizeCard,
    normalizeState,
    reviewedEntry,
    buildQueue,
    statsForScope,
    localDateKey,
  });
});
