'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const Smart = require('../smart-context.js');

function localTime(day, hour, minute = 0) {
  return new Date(2026, 9, day, hour, minute, 0, 0).getTime();
}

function baseConfig(extra = {}) {
  return {
    enabled: true,
    quietStart: '23:00',
    quietEnd: '06:00',
    maxDailyInterventions: 3,
    cooldownMinutes: 120,
    minimumScore: 0.5,
    ...extra,
  };
}

function candidate(extra = {}) {
  return {
    id: 'wird_today',
    service: 'wird',
    due: 0.9,
    need: 0.9,
    relevance: 0.7,
    continuity: 0.7,
    priority: 0.7,
    defaultHabit: 0.65,
    completionTypes: ['READ_PAGE'],
    ...extra,
  };
}

test('event sanitizer accepts only the documented event schema', () => {
  const now = localTime(20, 12);
  const event = Smart.sanitizeEvent({
    type: 'read_page',
    service: 'wird',
    at: now,
    durationMs: 1500,
    context: {
      page: 42,
      riwayah: 'warsh',
      url: 'https://private.example/path',
      text: 'private message',
      nested: { secret: true },
    },
    arbitrary: 'discard me',
  }, now);
  assert.equal(event.type, 'READ_PAGE');
  assert.equal(event.service, 'wird');
  assert.deepEqual(event.context, { page: 42, riwayah: 'warsh' });
  assert.equal('arbitrary' in event, false);
  assert.equal('url' in event.context, false);
  assert.equal('text' in event.context, false);
});

test('event sanitizer rejects unknown, expired, and implausibly future events', () => {
  const now = localTime(20, 12);
  assert.equal(Smart.sanitizeEvent({ type: 'BROWSE_HISTORY', service: 'app' }, now), null);
  assert.equal(Smart.sanitizeEvent({ type: 'APP_OPEN', service: 'app', at: now - 36 * 86400000 }, now), null);
  assert.equal(Smart.sanitizeEvent({ type: 'APP_OPEN', service: 'app', at: now + 6 * 60000 }, now), null);
});

test('pruning sorts, deduplicates, and removes invalid records', () => {
  const now = localTime(20, 12);
  const events = Smart.pruneEvents([
    { id: 'b', type: 'APP_OPEN', service: 'app', at: now - 1000 },
    { id: 'a', type: 'APP_OPEN', service: 'app', at: now - 2000 },
    { id: 'a', type: 'APP_OPEN', service: 'app', at: now - 2000 },
    { type: 'NOPE', service: 'app', at: now },
  ], now, baseConfig());
  assert.deepEqual(events.map((item) => item.id), ['a', 'b']);
});

test('habit model favors the learned time window', () => {
  const now = localTime(30, 20);
  const events = [];
  for (let day = 20; day < 30; day += 1) {
    events.push({ type: 'READ_PAGE', service: 'wird', at: localTime(day, 20) });
  }
  const model = Smart.buildHabitModel(events, now, baseConfig());
  const evening = Smart.habitScore(model, 'wird', localTime(30, 20));
  const morning = Smart.habitScore(model, 'wird', localTime(30, 9));
  assert.ok(evening > 0.95, `evening=${evening}`);
  assert.ok(morning < 0.1, `morning=${morning}`);
});

test('recent behavior carries more weight than old behavior', () => {
  const now = localTime(30, 20);
  const events = [];
  for (let day = 1; day <= 10; day += 1) {
    events.push({ type: 'READ_PAGE', service: 'wird', at: localTime(day, 8) });
  }
  for (let day = 24; day < 30; day += 1) {
    events.push({ type: 'READ_PAGE', service: 'wird', at: localTime(day, 20) });
  }
  const model = Smart.buildHabitModel(events, now, baseConfig({ halfLifeDays: 7 }));
  assert.ok(
    Smart.habitScore(model, 'wird', localTime(30, 20))
      > Smart.habitScore(model, 'wird', localTime(30, 8)),
  );
});

test('sleep window uses robust first and last activity samples', () => {
  const now = localTime(20, 12);
  const events = [];
  for (let day = 10; day < 20; day += 1) {
    events.push({ type: 'DEVICE_ACTIVE', service: 'device', at: localTime(day, 7) });
    events.push({ type: 'DEVICE_ACTIVE', service: 'device', at: localTime(day, 22, 30) });
  }
  const model = Smart.buildHabitModel(events, now, baseConfig());
  assert.equal(model.sleep.wakeMinute, 420);
  assert.equal(model.sleep.sleepMinute, 1380);
  assert.equal(model.sleep.confidence, 1);
});

test('context inference labels wake, evening, and sleep states', () => {
  const events = [];
  for (let day = 10; day < 20; day += 1) {
    events.push({ type: 'DEVICE_ACTIVE', service: 'device', at: localTime(day, 7) });
    events.push({ type: 'DEVICE_ACTIVE', service: 'device', at: localTime(day, 22, 30) });
  }
  const morningNow = localTime(20, 7, 20);
  let model = Smart.buildHabitModel(events, morningNow, baseConfig());
  let context = Smart.inferContext(model, {
    screenInteractive: true,
    lastDeviceActiveAt: morningNow - 60000,
  }, morningNow);
  assert.ok(context.states.includes('JUST_WOKE_UP'));
  assert.ok(context.states.includes('MORNING_WINDOW'));

  const eveningNow = localTime(20, 18);
  model = Smart.buildHabitModel(events, eveningNow, baseConfig());
  context = Smart.inferContext(model, { screenInteractive: true,
    lastDeviceActiveAt: eveningNow - 60000 }, eveningNow);
  assert.ok(context.states.includes('EVENING_WINDOW'));

  const nightNow = localTime(20, 23, 30);
  model = Smart.buildHabitModel(events, nightNow, baseConfig());
  context = Smart.inferContext(model, { screenInteractive: false }, nightNow);
  assert.equal(context.likelySleeping, true);
  assert.equal(context.receptive, 0);
});

test('engine never intervenes while disabled', () => {
  const now = localTime(20, 12);
  const decision = Smart.chooseIntervention([candidate()], [], {}, now,
    baseConfig({ enabled: false }));
  assert.equal(decision.selected, null);
  assert.equal(decision.blocked[0].reason, 'ENGINE_DISABLED');
});

test('quiet hours and likely sleep are hard safety gates', () => {
  const now = localTime(20, 23, 30);
  let decision = Smart.chooseIntervention([candidate({ allowDuringQuiet: true })], [], {
    screenInteractive: true,
    lastDeviceActiveAt: now,
    typicalSleepMinute: 60,
    typicalWakeMinute: 420,
  }, now, baseConfig());
  assert.equal(decision.selected, null);
  assert.equal(decision.blocked[0].reason, 'QUIET_HOURS');

  decision = Smart.chooseIntervention([candidate({ allowDuringSleep: true })], [], {
    screenInteractive: false,
    typicalSleepMinute: 22 * 60,
    typicalWakeMinute: 7 * 60,
  }, now, baseConfig({ quietStart: '01:00', quietEnd: '05:00' }));
  assert.equal(decision.selected, null);
  assert.equal(decision.blocked[0].reason, 'LIKELY_SLEEPING');
});

test('daily cap and cooldown prevent notification pressure', () => {
  const now = localTime(20, 15);
  const shown = [
    { type: 'NOTIFICATION_SHOWN', service: 'wird', at: localTime(20, 8) },
    { type: 'NOTIFICATION_SHOWN', service: 'adhkar_morning', at: localTime(20, 10) },
    { type: 'NOTIFICATION_SHOWN', service: 'tajweed', at: localTime(20, 12) },
  ];
  let decision = Smart.chooseIntervention([candidate()], shown, {
    screenInteractive: true, lastDeviceActiveAt: now,
  }, now, baseConfig());
  assert.equal(decision.blocked[0].reason, 'DAILY_CAP');

  decision = Smart.chooseIntervention([candidate()], [
    { type: 'NOTIFICATION_SHOWN', service: 'adhkar', at: now - 30 * 60000 },
  ], { screenInteractive: true, lastDeviceActiveAt: now }, now, baseConfig());
  assert.equal(decision.blocked[0].reason, 'COOLDOWN');
});

test('a completed service is suppressed for the rest of its day', () => {
  const now = localTime(20, 15);
  const decision = Smart.chooseIntervention([candidate()], [
    { type: 'READ_PAGE', service: 'wird', at: localTime(20, 9) },
  ], { screenInteractive: true, lastDeviceActiveAt: now }, now, baseConfig());
  assert.equal(decision.selected, null);
  assert.equal(decision.blocked[0].reason, 'ALREADY_COMPLETED');
});

test('a strong cold-start candidate can be selected without pretending it is learned', () => {
  const now = localTime(20, 12);
  const decision = Smart.chooseIntervention([candidate()], [], {
    screenInteractive: true, lastDeviceActiveAt: now,
    typicalSleepMinute: 23 * 60, typicalWakeMinute: 7 * 60,
  }, now, baseConfig());
  assert.ok(decision.selected);
  assert.equal(decision.selected.learned, false);
  assert.ok(decision.selected.reasons.includes('COLD_START'));
});

test('learned habit breaks an otherwise equal tie', () => {
  const now = localTime(30, 20);
  const events = [];
  for (let day = 20; day < 30; day += 1) {
    events.push({ type: 'READ_PAGE', service: 'wird', at: localTime(day, 20) });
    events.push({ type: 'OPEN_TAJWEED', service: 'tajweed', at: localTime(day, 9) });
  }
  const candidates = [candidate({ id: 'read', service: 'wird', completionTypes: [] }),
    candidate({ id: 'learn', service: 'tajweed', completionTypes: [] })];
  const decision = Smart.chooseIntervention(candidates, events, {
    screenInteractive: true, lastDeviceActiveAt: now,
  }, now, baseConfig());
  assert.equal(decision.selected.candidate.id, 'read');
  assert.equal(decision.selected.learned, true);
  assert.ok(decision.selected.reasons.includes('HABIT_MATCH'));
});

test('positive and negative feedback change the contextual response score', () => {
  const now = localTime(30, 20);
  const positive = [];
  const negative = [];
  for (let day = 20; day < 30; day += 1) {
    positive.push({ type: 'NOTIFICATION_OPEN', service: 'wird', at: localTime(day, 20) });
    negative.push({ type: 'NOTIFICATION_DISMISS', service: 'wird', at: localTime(day, 20) });
  }
  const positiveModel = Smart.buildHabitModel(positive, now, baseConfig());
  const negativeModel = Smart.buildHabitModel(negative, now, baseConfig());
  assert.ok(Smart.responseScore(positiveModel, 'wird', now) > 0.75);
  assert.ok(Smart.responseScore(negativeModel, 'wird', now) < 0.25);
  assert.ok(Smart.banditScore(positiveModel, 'wird', now)
    > Smart.banditScore(negativeModel, 'wird', now));
});

test('required state and explicit time window are enforced', () => {
  const now = localTime(20, 18);
  let decision = Smart.chooseIntervention([
    candidate({ requiredStates: ['MORNING_WINDOW'] }),
  ], [], { screenInteractive: true, lastDeviceActiveAt: now }, now, baseConfig());
  assert.equal(decision.blocked[0].reason, 'STATE_MISMATCH');

  decision = Smart.chooseIntervention([
    candidate({ notBefore: now + 60000 }),
  ], [], { screenInteractive: true, lastDeviceActiveAt: now }, now, baseConfig());
  assert.equal(decision.blocked[0].reason, 'TOO_EARLY');
});

test('wrapped time windows work across midnight', () => {
  assert.equal(Smart.isWithinWrapped(23 * 60, 22 * 60, 6 * 60), true);
  assert.equal(Smart.isWithinWrapped(5 * 60, 22 * 60, 6 * 60), true);
  assert.equal(Smart.isWithinWrapped(12 * 60, 22 * 60, 6 * 60), false);
});

test('SmartContextEngine persists a minimal snapshot and supports reset', () => {
  let now = localTime(20, 12);
  const engine = new Smart.SmartContextEngine({ config: baseConfig(), events: [] }, {
    now: () => now,
  });
  const recorded = engine.record({
    type: 'READ_PAGE', service: 'wird', context: { page: 9, text: 'discard' },
  });
  assert.equal(recorded.context.page, 9);
  assert.equal('text' in recorded.context, false);
  engine.markShown(candidate(), 'notice-1');
  now += 60000;
  engine.feedback('wird', 'open', 'notice-1');
  const state = engine.snapshot();
  assert.equal(state.schema, 1);
  assert.equal(state.events.length, 3);
  assert.equal(JSON.stringify(state).includes('discard'), false);
  engine.reset();
  assert.equal(engine.snapshot().events.length, 0);
});

test('invalid feedback actions and malformed candidates fail closed', () => {
  const now = localTime(20, 12);
  const engine = new Smart.SmartContextEngine({ config: baseConfig() }, { now: () => now });
  assert.equal(engine.feedback('wird', 'share_everything', 'x'), null);
  const decision = engine.evaluate([{ id: 'bad', service: '!!!' }], {
    screenInteractive: true, lastDeviceActiveAt: now,
  });
  assert.equal(decision.selected, null);
  assert.equal(decision.ranked.length, 0);
});
