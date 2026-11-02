'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const Learning = require('../tajweed-learning.js');

const DAY = 86400000;
const MINUTE = 60000;
const HAFS = Object.freeze({
  riwayah: 'hafs-an-asim',
  tariq: 'source-unspecified',
  wajh: 'source-default',
  edition: 'alquran-cloud-tajweed-v1',
});
const WARSH = Object.freeze({
  riwayah: 'warsh-an-nafi',
  tariq: 'al-azraq',
  wajh: 'source-default',
  edition: 'warsh-reviewed-v1',
});

function card(id, scope = HAFS, order = 0) {
  return { id, scope, order, prompt: `prompt ${id}`, answer: `answer ${id}` };
}

function at(day, hour = 12) {
  return new Date(2026, 9, day, hour, 0, 0, 0).getTime();
}

test('scope requires riwayah, tariq, wajh, and edition', () => {
  assert.deepEqual(Learning.normalizeScope(HAFS), HAFS);
  assert.equal(Learning.normalizeScope({ riwayah: 'hafs' }), null);
  assert.equal(Learning.normalizeScope({ ...HAFS, tariq: '../bad' }), null);
  assert.equal(Learning.scopeKey(HAFS),
    'hafs-an-asim/source-unspecified/source-default/alquran-cloud-tajweed-v1');
});

test('card identity includes the complete recitation scope', () => {
  const hafs = Learning.normalizeCard(card('madd'));
  const warsh = Learning.normalizeCard(card('madd', WARSH));
  assert.notEqual(hafs.key, warsh.key);
  assert.match(hafs.key, /hafs-an-asim/);
  assert.match(warsh.key, /al-azraq/);
});

test('new queue respects explicit order and daily limit', () => {
  const cards = [card('third', HAFS, 3), card('first', HAFS, 1), card('second', HAFS, 2)];
  const queue = Learning.buildQueue(cards, { config: { newPerDay: 2 } }, HAFS, at(20));
  assert.deepEqual(queue.map((item) => item.card.id), ['first', 'second']);
  assert.ok(queue.every((item) => item.kind === 'new'));
});

test('queues never leak cards across riwayat or turuq', () => {
  const cards = [card('hafs-rule', HAFS), card('warsh-rule', WARSH)];
  assert.deepEqual(Learning.buildQueue(cards, {}, HAFS, at(20)).map((item) => item.card.id),
    ['hafs-rule']);
  assert.deepEqual(Learning.buildQueue(cards, {}, WARSH, at(20)).map((item) => item.card.id),
    ['warsh-rule']);
});

test('again schedules a ten-minute relearning step', () => {
  const now = at(20);
  const entry = Learning.reviewedEntry(null, 'again', now);
  assert.equal(entry.dueAt, now + 10 * MINUTE);
  assert.equal(entry.repetitions, 0);
  assert.equal(entry.intervalDays, 0);
  assert.equal(entry.correctCount, 0);
});

test('good follows one, three, then ease-scaled day intervals', () => {
  const first = Learning.reviewedEntry(null, 'good', at(20));
  assert.equal(first.intervalDays, 1);
  const second = Learning.reviewedEntry(first, 'good', at(21));
  assert.equal(second.intervalDays, 3);
  const third = Learning.reviewedEntry(second, 'good', at(24));
  assert.equal(third.intervalDays, Math.round(3 * second.ease));
  assert.equal(third.repetitions, 3);
});

test('easy starts at four days and raises ease without exceeding bounds', () => {
  let entry = Learning.reviewedEntry(null, 'easy', at(20));
  assert.equal(entry.intervalDays, 4);
  assert.equal(entry.ease, 2.65);
  for (let index = 0; index < 20; index++) {
    entry = Learning.reviewedEntry(entry, 'easy', entry.dueAt);
  }
  assert.equal(entry.ease, 3);
  assert.ok(entry.intervalDays <= 365);
});

test('hard grows slowly and lowers ease', () => {
  const previous = {
    introducedAt: at(1), repetitions: 3, intervalDays: 10, ease: 2.5,
    dueAt: at(20), reviewCount: 3, correctCount: 3,
  };
  const entry = Learning.reviewedEntry(previous, 'hard', at(20));
  assert.equal(entry.intervalDays, 12);
  assert.equal(entry.ease, 2.35);
  assert.equal(entry.repetitions, 3);
});

test('a lapse resets repetitions and marks a repeated leech', () => {
  let entry = {
    introducedAt: at(1), repetitions: 3, intervalDays: 30, ease: 2.5,
    dueAt: at(20), lapses: 7,
  };
  entry = Learning.reviewedEntry(entry, 'again', at(20));
  assert.equal(entry.repetitions, 0);
  assert.equal(entry.lapses, 8);
  assert.equal(entry.leech, true);
});

test('due reviews are ordered before new lessons', () => {
  const first = card('oldest');
  const second = card('later');
  const fresh = card('fresh');
  const state = { progress: {
    [Learning.normalizeCard(first).key]: { dueAt: at(18), introducedAt: at(1) },
    [Learning.normalizeCard(second).key]: { dueAt: at(19), introducedAt: at(2) },
  } };
  const queue = Learning.buildQueue([second, fresh, first], state, HAFS, at(20));
  assert.deepEqual(queue.map((item) => item.card.id), ['oldest', 'later', 'fresh']);
  assert.deepEqual(queue.map((item) => item.kind), ['review', 'review', 'new']);
});

test('future and suspended reviews stay out of the queue', () => {
  const future = card('future');
  const suspended = card('suspended');
  const state = { progress: {
    [Learning.normalizeCard(future).key]: { dueAt: at(21), introducedAt: at(1) },
    [Learning.normalizeCard(suspended).key]: {
      dueAt: at(19), introducedAt: at(1), suspended: true,
    },
  } };
  assert.deepEqual(Learning.buildQueue([future, suspended], state, HAFS, at(20)), []);
});

test('reviews already completed today reduce the daily review budget', () => {
  const cards = Array.from({ length: 7 }, (_, i) => card(`r${i}`));
  const progress = {};
  cards.forEach((item, index) => {
    progress[Learning.normalizeCard(item).key] = {
      dueAt: at(19), introducedAt: at(1),
      lastReviewedAt: index < 3 ? at(20, 8) : at(19),
    };
  });
  const queue = Learning.buildQueue(cards, {
    config: { reviewsPerDay: 5 }, progress,
  }, HAFS, at(20));
  assert.equal(queue.length, 2);
});

test('engine rejects malformed cards and ratings', () => {
  const engine = new Learning.TajweedLearningEngine({}, { now: () => at(20) });
  assert.equal(engine.review({ id: 'x' }, 'good'), null);
  assert.equal(engine.review(card('x'), 'perfect'), null);
  assert.equal(engine.stats(HAFS).total, 0);
});

test('engine snapshot is detached from mutable internal state', () => {
  const engine = new Learning.TajweedLearningEngine({}, { now: () => at(20) });
  engine.review(card('madd'), 'good');
  const snapshot = engine.snapshot();
  const key = Learning.normalizeCard(card('madd')).key;
  snapshot.progress[key].ease = 1.3;
  assert.equal(engine.snapshot().progress[key].ease, 2.5);
});

test('reset affects only the selected scope', () => {
  const engine = new Learning.TajweedLearningEngine({}, { now: () => at(20) });
  engine.review(card('same', HAFS), 'good');
  engine.review(card('same', WARSH), 'easy');
  engine.resetScope(HAFS);
  assert.equal(engine.stats(HAFS).total, 0);
  assert.equal(engine.stats(WARSH).total, 1);
});

test('scope statistics report accuracy, maturity, leeches, and next due', () => {
  const good = card('good');
  const leech = card('leech');
  const state = { progress: {
    [Learning.normalizeCard(good).key]: {
      introducedAt: at(1), dueAt: at(25), repetitions: 3,
      reviewCount: 4, correctCount: 3,
    },
    [Learning.normalizeCard(leech).key]: {
      introducedAt: at(1), dueAt: at(19), repetitions: 0,
      reviewCount: 4, correctCount: 1, lapses: 8, leech: true,
    },
  } };
  const stats = Learning.statsForScope(state, HAFS, at(20));
  assert.equal(stats.total, 2);
  assert.equal(stats.due, 1);
  assert.equal(stats.mature, 1);
  assert.equal(stats.leeches, 1);
  assert.equal(stats.accuracy, 0.5);
  assert.equal(stats.nextDueAt, at(19));
});

test('state normalization bounds corrupt numeric values', () => {
  const key = Learning.normalizeCard(card('madd')).key;
  const state = Learning.normalizeState({ progress: { [key]: {
    intervalDays: Infinity, ease: 99, repetitions: -4, lapses: 99999999,
  } } });
  assert.equal(state.progress[key].intervalDays, 0);
  assert.equal(state.progress[key].ease, 3);
  assert.equal(state.progress[key].repetitions, 0);
  assert.equal(state.progress[key].lapses, 10000);
});

test('queue and review decisions are deterministic for the same state and clock', () => {
  const now = at(20);
  const cards = [card('b', HAFS, 2), card('a', HAFS, 1)];
  const a = new Learning.TajweedLearningEngine({}, { now: () => now });
  const b = new Learning.TajweedLearningEngine({}, { now: () => now });
  assert.deepEqual(a.queue(cards, HAFS), b.queue(cards, HAFS));
  assert.deepEqual(a.review(cards[0], 'good'), b.review(cards[0], 'good'));
  assert.deepEqual(a.snapshot(), b.snapshot());
});
