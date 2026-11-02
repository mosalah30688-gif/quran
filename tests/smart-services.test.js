'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const Services = require('../smart-services.js');

function byService(candidates, service) {
  return candidates.find((candidate) => candidate.service === service);
}

test('builds a conservative cold-start set with explicit actions', () => {
  const candidates = Services.buildCandidates({
    readToday: 0,
    wirdPointer: 42,
    readingAverage: 3.5,
    memoDue: 0,
  }, 1);
  const wird = byService(candidates, 'wird');
  assert.ok(wird);
  assert.equal(wird.action, 'open_wird');
  assert.match(wird.body, /42/);
  assert.deepEqual(wird.completionTypes, ['READ_PAGE']);
  assert.ok(byService(candidates, 'adhkar_morning'));
  assert.ok(byService(candidates, 'adhkar_evening'));
  assert.equal(byService(candidates, 'recitation'), undefined);
  assert.equal(byService(candidates, 'tajweed'), undefined);
});

test('does not offer a service already completed today', () => {
  const candidates = Services.buildCandidates({
    readToday: 1,
    completedServices: ['wird', 'adhkar_morning', 'adhkar_wake'],
  });
  assert.equal(byService(candidates, 'wird'), undefined);
  assert.equal(byService(candidates, 'adhkar_morning'), undefined);
  assert.equal(byService(candidates, 'adhkar_wake'), undefined);
  assert.ok(byService(candidates, 'adhkar_evening'));
});

test('memorization reviews are high-priority only when due', () => {
  let candidates = Services.buildCandidates({ memoDue: 0 });
  assert.equal(byService(candidates, 'memorization'), undefined);

  candidates = Services.buildCandidates({ memoDue: 3 });
  const memo = byService(candidates, 'memorization');
  assert.ok(memo);
  assert.equal(memo.action, 'open_memorization');
  assert.equal(memo.priority, 0.94);
  assert.match(memo.body, /3/);
});

test('exploratory services require prior local use', () => {
  const candidates = Services.buildCandidates({
    readToday: 1,
    knownServices: ['recitation', 'tajweed'],
  });
  assert.ok(byService(candidates, 'recitation'));
  assert.ok(byService(candidates, 'tajweed'));
});

test('time-specific adhkar candidates declare required context states', () => {
  const candidates = Services.buildCandidates({});
  assert.deepEqual(byService(candidates, 'adhkar_wake').requiredStates, ['JUST_WOKE_UP']);
  assert.deepEqual(byService(candidates, 'adhkar_morning').requiredStates, ['MORNING_WINDOW']);
  assert.deepEqual(byService(candidates, 'adhkar_evening').requiredStates, ['EVENING_WINDOW']);
});

test('selection explanation is transparent about cold start and local processing', () => {
  const text = Services.explainSelection({
    candidate: { id: 'continue_wird' },
    reasons: ['COLD_START', 'DUE_NOW'],
  });
  assert.match(text, /اقتراح مبدئي/);
  assert.match(text, /هذا الجهاز فقط/);
  assert.doesNotMatch(text, /اعتدت/);
});

test('learned explanation may describe a habit match', () => {
  const text = Services.explainSelection({
    candidate: { id: 'continue_wird' },
    reasons: ['HABIT_MATCH', 'DUE_NOW'],
  });
  assert.match(text, /اعتدت/);
  assert.match(text, /محفوظ على هذا الجهاز/);
});

test('block descriptions and adhkar service names fail safely', () => {
  assert.match(Services.describeBlock('LIKELY_SLEEPING'), /النوم/);
  assert.match(Services.describeBlock('DAILY_CAP'), /اليوم/);
  assert.equal(Services.serviceForAdhkar('morning'), 'adhkar_morning');
  assert.equal(Services.serviceForAdhkar('../private'), 'adhkar');
});

test('same input always produces the same candidate order and fields', () => {
  const input = {
    readToday: 0,
    wirdPointer: 7,
    memoDue: 2,
    knownServices: ['tajweed', 'recitation'],
  };
  assert.deepEqual(Services.buildCandidates(input, 10), Services.buildCandidates(input, 20));
});
