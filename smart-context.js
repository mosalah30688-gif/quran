/*
 * Siraj Smart Context Engine v1
 *
 * A small, deterministic, privacy-preserving habit and intervention engine.
 * It stores event metadata only; it never accepts message text, URLs, audio,
 * contacts, or arbitrary payloads. The same file runs in a browser and in
 * Node.js so the decision logic can be tested independently of the UI.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SirajSmartContext = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SCHEMA_VERSION = 1;
  const DAY_MS = 24 * 60 * 60 * 1000;
  const BIN_MINUTES = 30;
  const BIN_COUNT = 48;
  const MAX_EVENTS = 4000;

  const EVENT_TYPES = new Set([
    'APP_OPEN', 'APP_FOREGROUND', 'DEVICE_ACTIVE', 'SCREEN_ON', 'SCREEN_OFF',
    'SERVICE_OPEN', 'SERVICE_COMPLETE', 'READ_PAGE', 'READING_SESSION_END',
    'PLAY_RECITATION', 'START_MEMORIZATION', 'COMPLETE_MEMORIZATION',
    'COMPLETE_ADHKAR', 'OPEN_TAFSIR', 'OPEN_TAJWEED',
    'COMPLETE_TAJWEED_LESSON', 'TAJWEED_ANSWER',
    'NOTIFICATION_SHOWN', 'NOTIFICATION_OPEN', 'NOTIFICATION_COMPLETE',
    'NOTIFICATION_SNOOZE', 'NOTIFICATION_NOT_NOW', 'NOTIFICATION_DISMISS',
  ]);

  const ACTIVITY_TYPES = new Set([
    'APP_OPEN', 'APP_FOREGROUND', 'DEVICE_ACTIVE', 'SCREEN_ON', 'SERVICE_OPEN',
    'SERVICE_COMPLETE', 'READ_PAGE', 'READING_SESSION_END', 'PLAY_RECITATION',
    'START_MEMORIZATION', 'COMPLETE_MEMORIZATION', 'COMPLETE_ADHKAR',
    'OPEN_TAFSIR', 'OPEN_TAJWEED', 'COMPLETE_TAJWEED_LESSON', 'TAJWEED_ANSWER',
  ]);

  const COMPLETION_TYPES = new Set([
    'SERVICE_COMPLETE', 'COMPLETE_MEMORIZATION', 'COMPLETE_ADHKAR',
    'COMPLETE_TAJWEED_LESSON', 'NOTIFICATION_COMPLETE',
  ]);

  const POSITIVE_FEEDBACK_TYPES = new Set([
    'NOTIFICATION_OPEN', 'NOTIFICATION_COMPLETE',
  ]);

  const NEGATIVE_FEEDBACK_TYPES = new Set([
    'NOTIFICATION_NOT_NOW', 'NOTIFICATION_DISMISS',
  ]);

  const ALLOWED_CONTEXT_KEYS = new Set([
    'page', 'riwayah', 'category', 'rule', 'notificationId', 'source',
    'correct', 'count', 'sessionMinutes',
  ]);

  const DEFAULT_CONFIG = Object.freeze({
    enabled: false,
    retentionDays: 35,
    halfLifeDays: 14,
    maxDailyInterventions: 3,
    cooldownMinutes: 120,
    quietStart: '22:30',
    quietEnd: '06:30',
    minimumScore: 0.58,
    minimumLearningSamples: 7,
  });

  function clamp(value, low = 0, high = 1) {
    const number = Number(value);
    if (!Number.isFinite(number)) return low;
    return Math.min(high, Math.max(low, number));
  }

  function validToken(value, fallback, max = 48) {
    const token = String(value == null ? '' : value).trim().toLowerCase();
    return /^[a-z][a-z0-9_-]*$/.test(token) && token.length <= max ? token : fallback;
  }

  function parseTime(value, fallback) {
    const match = /^(\d{2}):(\d{2})$/.exec(String(value || ''));
    if (!match) return fallback;
    const hour = Number(match[1]);
    const minute = Number(match[2]);
    if (hour > 23 || minute > 59) return fallback;
    return hour * 60 + minute;
  }

  function minuteOfDay(value) {
    const date = value instanceof Date ? value : new Date(value);
    return date.getHours() * 60 + date.getMinutes();
  }

  function timeBin(value) {
    return Math.floor(minuteOfDay(value) / BIN_MINUTES) % BIN_COUNT;
  }

  function dateKey(value) {
    const date = value instanceof Date ? value : new Date(value);
    return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
      String(date.getDate()).padStart(2, '0')].join('-');
  }

  function circularMinuteDistance(a, b) {
    const direct = Math.abs(a - b);
    return Math.min(direct, 1440 - direct);
  }

  function minutesAfter(value, start) {
    return (value - start + 1440) % 1440;
  }

  function isWithinWrapped(value, start, end) {
    if (start === end) return false;
    if (start < end) return value >= start && value < end;
    return value >= start || value < end;
  }

  function normalizeConfig(config) {
    const input = config || {};
    const value = (key) => input[key] == null ? DEFAULT_CONFIG[key] : input[key];
    return {
      enabled: input.enabled == null ? DEFAULT_CONFIG.enabled : !!input.enabled,
      retentionDays: Math.round(clamp(value('retentionDays'), 7, 90)),
      halfLifeDays: Math.round(clamp(value('halfLifeDays'), 3, 30)),
      maxDailyInterventions: Math.round(clamp(value('maxDailyInterventions'), 1, 8)),
      cooldownMinutes: Math.round(clamp(value('cooldownMinutes'), 30, 720)),
      quietStart: /^\d{2}:\d{2}$/.test(input.quietStart || '')
        ? input.quietStart : DEFAULT_CONFIG.quietStart,
      quietEnd: /^\d{2}:\d{2}$/.test(input.quietEnd || '')
        ? input.quietEnd : DEFAULT_CONFIG.quietEnd,
      minimumScore: clamp(value('minimumScore'), 0.3, 0.95),
      minimumLearningSamples: Math.round(clamp(value('minimumLearningSamples'), 3, 30)),
    };
  }

  function sanitizeContext(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    const output = {};
    Object.keys(value).forEach((key) => {
      if (!ALLOWED_CONTEXT_KEYS.has(key)) return;
      const item = value[key];
      if (typeof item === 'boolean') output[key] = item;
      else if (typeof item === 'number' && Number.isFinite(item)) {
        output[key] = clamp(item, -1000000, 1000000);
      } else if (typeof item === 'string' && item.length <= 64
          && /^[\w:.-]+$/u.test(item)) output[key] = item;
    });
    return output;
  }

  function sanitizeEvent(input, nowValue = Date.now(), retentionDays = 35) {
    if (!input || typeof input !== 'object') return null;
    const type = String(input.type || '').trim().toUpperCase();
    if (!EVENT_TYPES.has(type)) return null;
    const service = validToken(input.service, 'app');
    const now = Number(nowValue);
    const parsedAt = input.at instanceof Date ? input.at.getTime() : Number(input.at);
    const at = Number.isFinite(parsedAt) ? Math.round(parsedAt) : Math.round(now);
    if (at > now + 5 * 60 * 1000 || at < now - retentionDays * DAY_MS) return null;
    const durationMs = Math.round(clamp(input.durationMs || 0, 0, 12 * 60 * 60 * 1000));
    const result = { schema: SCHEMA_VERSION, type, service, at };
    if (durationMs) result.durationMs = durationMs;
    const context = sanitizeContext(input.context);
    if (Object.keys(context).length) result.context = context;
    if (typeof input.id === 'string' && /^[a-zA-Z0-9_.:-]{1,96}$/.test(input.id)) {
      result.id = input.id;
    }
    return result;
  }

  function pruneEvents(events, nowValue = Date.now(), config) {
    const cfg = normalizeConfig(config);
    const seen = new Set();
    const cleaned = [];
    (Array.isArray(events) ? events : []).forEach((item) => {
      const event = sanitizeEvent(item, nowValue, cfg.retentionDays);
      if (!event) return;
      const identity = event.id || [event.type, event.service, event.at,
        event.context && event.context.notificationId || ''].join('|');
      if (seen.has(identity)) return;
      seen.add(identity);
      cleaned.push(event);
    });
    cleaned.sort((a, b) => a.at - b.at || a.type.localeCompare(b.type));
    return cleaned.slice(-MAX_EVENTS);
  }

  function decayedWeight(at, now, halfLifeDays) {
    const ageDays = Math.max(0, (now - at) / DAY_MS);
    return Math.pow(0.5, ageDays / halfLifeDays);
  }

  function emptyProfile() {
    return {
      activity: Array(BIN_COUNT).fill(0),
      completions: Array(BIN_COUNT).fill(0),
      positive: Array(BIN_COUNT).fill(0),
      negative: Array(BIN_COUNT).fill(0),
      activityWeight: 0,
      completionWeight: 0,
      feedbackWeight: 0,
      rawSamples: 0,
    };
  }

  function weightedMedian(items, fallback) {
    if (!items.length) return fallback;
    const sorted = [...items].sort((a, b) => a.value - b.value);
    const total = sorted.reduce((sum, item) => sum + item.weight, 0);
    let cursor = 0;
    for (const item of sorted) {
      cursor += item.weight;
      if (cursor >= total / 2) return item.value;
    }
    return sorted[sorted.length - 1].value;
  }

  function estimateSleepWindow(events, now, config) {
    const days = new Map();
    const relevant = new Set(['DEVICE_ACTIVE', 'SCREEN_ON', 'APP_OPEN', 'APP_FOREGROUND']);
    events.forEach((event) => {
      if (!relevant.has(event.type)) return;
      const date = new Date(event.at);
      const minute = minuteOfDay(date);
      const key = dateKey(date);
      if (!days.has(key)) days.set(key, []);
      days.get(key).push({ minute, at: event.at });
    });
    const wakeSamples = [];
    const sleepSamples = [];
    days.forEach((rows) => {
      const minutes = rows.map((row) => row.minute).sort((a, b) => a - b);
      const morning = minutes.filter((minute) => minute >= 180 && minute <= 840);
      const evening = minutes.filter((minute) => minute >= 1080);
      const newest = Math.max(...rows.map((row) => row.at));
      const weight = decayedWeight(newest, now, config.halfLifeDays);
      if (morning.length) wakeSamples.push({ value: morning[0], weight });
      if (evening.length) sleepSamples.push({ value: evening[evening.length - 1], weight });
    });
    const wakeMinute = Math.round(weightedMedian(wakeSamples, 420));
    // Last activity is not sleep itself; allow a conservative 30-minute wind-down.
    const sleepMinute = Math.round((weightedMedian(sleepSamples, 1350) + 30) % 1440);
    const usableDays = Math.min(wakeSamples.length, sleepSamples.length);
    return {
      wakeMinute,
      sleepMinute,
      confidence: clamp(usableDays / 7),
      sampleDays: usableDays,
    };
  }

  function buildHabitModel(inputEvents, nowValue = Date.now(), config) {
    const cfg = normalizeConfig(config);
    const now = Number(nowValue);
    const events = pruneEvents(inputEvents, now, cfg);
    const profiles = {};
    const deviceActivity = Array(BIN_COUNT).fill(0);

    function profileFor(service) {
      if (!profiles[service]) profiles[service] = emptyProfile();
      return profiles[service];
    }

    events.forEach((event) => {
      const weight = decayedWeight(event.at, now, cfg.halfLifeDays);
      const bin = timeBin(event.at);
      const profile = profileFor(event.service);
      if (ACTIVITY_TYPES.has(event.type)) {
        profile.activity[bin] += weight;
        profile.activityWeight += weight;
        profile.rawSamples += 1;
      }
      if (COMPLETION_TYPES.has(event.type)) {
        profile.completions[bin] += weight;
        profile.completionWeight += weight;
      }
      if (POSITIVE_FEEDBACK_TYPES.has(event.type)) {
        profile.positive[bin] += weight;
        profile.feedbackWeight += weight;
      }
      if (NEGATIVE_FEEDBACK_TYPES.has(event.type)) {
        profile.negative[bin] += weight;
        profile.feedbackWeight += weight;
      }
      if (event.type === 'NOTIFICATION_SNOOZE') profile.feedbackWeight += weight * 0.2;
      if (['DEVICE_ACTIVE', 'SCREEN_ON', 'APP_OPEN', 'APP_FOREGROUND'].includes(event.type)) {
        deviceActivity[bin] += weight;
      }
    });

    return {
      schema: SCHEMA_VERSION,
      generatedAt: now,
      config: cfg,
      events,
      profiles,
      deviceActivity,
      sleep: estimateSleepWindow(events, now, cfg),
    };
  }

  function smoothedBin(values, bin) {
    const weights = [0.15, 0.35, 1, 0.35, 0.15];
    let total = 0;
    for (let offset = -2; offset <= 2; offset += 1) {
      const index = (bin + offset + BIN_COUNT) % BIN_COUNT;
      total += (values[index] || 0) * weights[offset + 2];
    }
    return total;
  }

  function habitScore(model, service, atValue) {
    const profile = model.profiles[service];
    if (!profile || !profile.activityWeight) return 0.5;
    const bin = timeBin(atValue);
    const current = smoothedBin(profile.activity, bin);
    let maximum = 0;
    for (let index = 0; index < BIN_COUNT; index += 1) {
      maximum = Math.max(maximum, smoothedBin(profile.activity, index));
    }
    return maximum ? clamp(current / maximum) : 0.5;
  }

  function responseScore(model, service, atValue) {
    const profile = model.profiles[service];
    if (!profile) return 0.5;
    const bin = timeBin(atValue);
    const positive = smoothedBin(profile.positive, bin);
    const negative = smoothedBin(profile.negative, bin);
    return clamp((1 + positive) / (2 + positive + negative));
  }

  function banditScore(model, service, atValue) {
    const profile = model.profiles[service];
    if (!profile) return 0.56;
    const bin = timeBin(atValue);
    const positive = smoothedBin(profile.positive, bin);
    const negative = smoothedBin(profile.negative, bin);
    const trials = positive + negative;
    const posterior = (1 + positive) / (2 + trials);
    // A bounded UCB exploration bonus: new, safe time windows can be tried
    // without allowing exploration to dominate the intervention score.
    const exploration = Math.min(0.12, 0.12 / Math.sqrt(trials + 1));
    return clamp(posterior + exploration);
  }

  function eventCountSince(events, type, since, service) {
    return events.reduce((count, event) => count + (
      event.type === type && event.at >= since && (!service || event.service === service) ? 1 : 0
    ), 0);
  }

  function lastEvent(events, types, service) {
    const wanted = new Set(Array.isArray(types) ? types : [types]);
    for (let index = events.length - 1; index >= 0; index -= 1) {
      const event = events[index];
      if (wanted.has(event.type) && (!service || event.service === service)) return event;
    }
    return null;
  }

  function serviceCompletedToday(events, service, completionTypes, nowValue) {
    const today = dateKey(nowValue);
    const wanted = new Set(completionTypes && completionTypes.length
      ? completionTypes : [...COMPLETION_TYPES]);
    return events.some((event) => event.service === service && wanted.has(event.type)
      && dateKey(event.at) === today);
  }

  function inferContext(model, input, nowValue = Date.now()) {
    const now = Number(nowValue);
    const cfg = model.config;
    const details = input || {};
    const currentMinute = minuteOfDay(now);
    const wakeMinute = Number.isFinite(details.typicalWakeMinute)
      ? Math.round(clamp(details.typicalWakeMinute, 0, 1439)) : model.sleep.wakeMinute;
    const sleepMinute = Number.isFinite(details.typicalSleepMinute)
      ? Math.round(clamp(details.typicalSleepMinute, 0, 1439)) : model.sleep.sleepMinute;
    const quietStart = parseTime(cfg.quietStart, 1350);
    const quietEnd = parseTime(cfg.quietEnd, 390);
    const screenInteractive = details.screenInteractive == null ? null : !!details.screenInteractive;
    const lastActiveAt = Number.isFinite(details.lastDeviceActiveAt)
      ? Number(details.lastDeviceActiveAt)
      : (lastEvent(model.events, ['DEVICE_ACTIVE', 'SCREEN_ON', 'APP_OPEN', 'APP_FOREGROUND']) || {}).at;
    const recentlyActive = Number.isFinite(lastActiveAt) && now - lastActiveAt <= 15 * 60 * 1000;
    const habitualSleep = isWithinWrapped(currentMinute, sleepMinute, wakeMinute);
    const likelySleeping = habitualSleep && !(screenInteractive === true && recentlyActive);
    const afterWake = minutesAfter(currentMinute, wakeMinute);
    const beforeSleep = minutesAfter(sleepMinute, currentMinute);
    const justWoke = !likelySleeping && afterWake <= 90 && (recentlyActive || screenInteractive === true);
    const morningWindow = !likelySleeping && afterWake <= 300;
    const eveningWindow = currentMinute >= 16 * 60 && currentMinute < 22 * 60 + 30;
    const preparingForSleep = !likelySleeping && beforeSleep <= 90;
    const quietHours = isWithinWrapped(currentMinute, quietStart, quietEnd);
    const dayStart = new Date(now);
    dayStart.setHours(0, 0, 0, 0);
    const shownToday = eventCountSince(model.events, 'NOTIFICATION_SHOWN', dayStart.getTime());
    const sixHoursAgo = now - 6 * 60 * 60 * 1000;
    const shownRecently = eventCountSince(model.events, 'NOTIFICATION_SHOWN', sixHoursAgo);
    const dismissedRecently = eventCountSince(model.events, 'NOTIFICATION_DISMISS', now - 7 * DAY_MS)
      + eventCountSince(model.events, 'NOTIFICATION_NOT_NOW', now - 7 * DAY_MS);
    const fatigue = clamp(
      shownToday / Math.max(1, cfg.maxDailyInterventions)
      + shownRecently * 0.14 + dismissedRecently * 0.05,
    );
    let receptive = 0.55;
    if (screenInteractive === true) receptive += 0.15;
    if (recentlyActive) receptive += 0.08;
    if (justWoke) receptive += 0.05;
    if (details.busy) receptive -= 0.35;
    receptive -= fatigue * 0.35;
    if (quietHours) receptive -= 0.5;
    if (likelySleeping) receptive = 0;
    receptive = clamp(receptive);

    const states = [];
    if (likelySleeping) states.push('LIKELY_SLEEPING');
    else {
      if (justWoke) states.push('JUST_WOKE_UP');
      if (morningWindow) states.push('MORNING_WINDOW');
      if (eveningWindow) states.push('EVENING_WINDOW');
      if (preparingForSleep) states.push('PREPARING_FOR_SLEEP');
      if (details.busy) states.push('BUSY');
      if (receptive >= 0.58) states.push('RECEPTIVE');
    }

    return {
      now,
      currentMinute,
      wakeMinute,
      sleepMinute,
      sleepConfidence: model.sleep.confidence,
      screenInteractive,
      recentlyActive,
      likelySleeping,
      justWoke,
      morningWindow,
      eveningWindow,
      preparingForSleep,
      quietHours,
      shownToday,
      shownRecently,
      dismissedRecently,
      fatigue,
      receptive,
      states,
    };
  }

  function normalizeCandidate(value, index) {
    if (!value || typeof value !== 'object') return null;
    const service = validToken(value.service, null);
    if (!service) return null;
    const id = validToken(value.id, `${service}_${index}`, 64);
    const completionTypes = Array.isArray(value.completionTypes)
      ? value.completionTypes.map((item) => String(item).toUpperCase())
        .filter((item) => EVENT_TYPES.has(item))
      : [];
    const requiredStates = Array.isArray(value.requiredStates)
      ? value.requiredStates.map((item) => String(item).toUpperCase()).slice(0, 8)
      : [];
    return {
      ...value,
      id,
      service,
      due: clamp(value.due == null ? 0.5 : value.due),
      need: clamp(value.need == null ? 0.5 : value.need),
      relevance: clamp(value.relevance == null ? 0.5 : value.relevance),
      continuity: clamp(value.continuity == null ? 0.5 : value.continuity),
      priority: clamp(value.priority == null ? 0.5 : value.priority),
      defaultHabit: clamp(value.defaultHabit == null ? 0.5 : value.defaultHabit),
      completionTypes,
      requiredStates,
    };
  }

  function safetyBlock(candidate, model, context, now) {
    const cfg = model.config;
    if (!cfg.enabled) return 'ENGINE_DISABLED';
    if (candidate.enabled === false) return 'CANDIDATE_DISABLED';
    // النوم وساعات الهدوء بوابتان قطعيّتان؛ لا يجوز لمرشح أن يتجاوزهما.
    if (context.likelySleeping) return 'LIKELY_SLEEPING';
    if (context.quietHours) return 'QUIET_HOURS';
    if (context.shownToday >= cfg.maxDailyInterventions) return 'DAILY_CAP';
    const latest = lastEvent(model.events, 'NOTIFICATION_SHOWN');
    if (latest && now - latest.at < cfg.cooldownMinutes * 60 * 1000) return 'COOLDOWN';
    if (serviceCompletedToday(model.events, candidate.service, candidate.completionTypes, now)) {
      return 'ALREADY_COMPLETED';
    }
    if (candidate.requiredStates.length
        && !candidate.requiredStates.some((state) => context.states.includes(state))) {
      return 'STATE_MISMATCH';
    }
    if (Number.isFinite(candidate.notBefore) && now < candidate.notBefore) return 'TOO_EARLY';
    if (Number.isFinite(candidate.notAfter) && now > candidate.notAfter) return 'TOO_LATE';
    return null;
  }

  function rankCandidates(inputCandidates, model, context, nowValue = Date.now()) {
    const now = Number(nowValue);
    const ranked = [];
    const blocked = [];
    (Array.isArray(inputCandidates) ? inputCandidates : []).forEach((value, index) => {
      const candidate = normalizeCandidate(value, index);
      if (!candidate) return;
      const block = safetyBlock(candidate, model, context, now);
      if (block) {
        blocked.push({ id: candidate.id, service: candidate.service, reason: block });
        return;
      }
      const profile = model.profiles[candidate.service];
      const learned = !!(profile && profile.rawSamples >= model.config.minimumLearningSamples);
      const habit = learned ? habitScore(model, candidate.service, now) : candidate.defaultHabit;
      const response = learned ? responseScore(model, candidate.service, now) : 0.5;
      const bandit = learned ? banditScore(model, candidate.service, now) : 0.56;
      const score = clamp(
        habit * 0.22
        + candidate.due * 0.2
        + candidate.need * 0.18
        + context.receptive * 0.14
        + response * 0.08
        + bandit * 0.08
        + candidate.continuity * 0.05
        + candidate.relevance * 0.05
        + candidate.priority * 0.05
        - context.fatigue * 0.22,
      );
      const reasons = [];
      if (learned && habit >= 0.65) reasons.push('HABIT_MATCH');
      if (!learned) reasons.push('COLD_START');
      if (candidate.due >= 0.7) reasons.push('DUE_NOW');
      if (candidate.need >= 0.7) reasons.push('SERVICE_NEED');
      if (candidate.relevance >= 0.7) reasons.push('CONTENT_RELEVANCE');
      if (context.justWoke) reasons.push('JUST_WOKE_UP');
      if (context.preparingForSleep) reasons.push('PREPARING_FOR_SLEEP');
      ranked.push({ candidate, score, habit, response, bandit, learned, reasons });
    });
    ranked.sort((a, b) => b.score - a.score
      || b.candidate.priority - a.candidate.priority
      || a.candidate.id.localeCompare(b.candidate.id));
    return { ranked, blocked };
  }

  function chooseIntervention(candidates, inputEvents, input, nowValue = Date.now(), config) {
    const model = buildHabitModel(inputEvents, nowValue, config);
    const context = inferContext(model, input, nowValue);
    const result = rankCandidates(candidates, model, context, nowValue);
    const top = result.ranked[0] || null;
    const selected = top && top.score >= model.config.minimumScore ? top : null;
    if (top && !selected) {
      result.blocked.push({ id: top.candidate.id, service: top.candidate.service,
        reason: 'BELOW_THRESHOLD', score: top.score });
    }
    return { selected, ranked: result.ranked, blocked: result.blocked, context, model };
  }

  const FEEDBACK_EVENTS = Object.freeze({
    open: 'NOTIFICATION_OPEN',
    complete: 'NOTIFICATION_COMPLETE',
    snooze: 'NOTIFICATION_SNOOZE',
    not_now: 'NOTIFICATION_NOT_NOW',
    dismiss: 'NOTIFICATION_DISMISS',
  });

  class SmartContextEngine {
    constructor(state, options) {
      const source = state && typeof state === 'object' ? state : {};
      this.clock = options && typeof options.now === 'function' ? options.now : () => Date.now();
      this.config = normalizeConfig(source.config);
      this.events = pruneEvents(source.events, this.clock(), this.config);
      this.sequence = Number.isInteger(source.sequence) ? source.sequence : this.events.length;
    }

    configure(patch) {
      this.config = normalizeConfig({ ...this.config, ...(patch || {}) });
      this.events = pruneEvents(this.events, this.clock(), this.config);
      return this.config;
    }

    record(value) {
      const now = this.clock();
      const event = sanitizeEvent(value, now, this.config.retentionDays);
      if (!event) return null;
      if (!event.id) {
        this.sequence += 1;
        event.id = `${event.at}:${event.type}:${event.service}:${this.sequence}`;
      }
      this.events.push(event);
      this.events = pruneEvents(this.events, now, this.config);
      return event;
    }

    evaluate(candidates, input) {
      return chooseIntervention(candidates, this.events, input, this.clock(), this.config);
    }

    markShown(candidate, notificationId) {
      if (!candidate || !candidate.service) return null;
      return this.record({
        type: 'NOTIFICATION_SHOWN',
        service: candidate.service,
        context: { notificationId: String(notificationId || candidate.id || '').slice(0, 64) },
      });
    }

    feedback(service, action, notificationId) {
      const type = FEEDBACK_EVENTS[action];
      if (!type) return null;
      return this.record({
        type,
        service,
        context: { notificationId: String(notificationId || '').slice(0, 64) },
      });
    }

    snapshot() {
      return {
        schema: SCHEMA_VERSION,
        config: { ...this.config },
        events: this.events.map((event) => ({ ...event,
          context: event.context ? { ...event.context } : undefined })),
        sequence: this.sequence,
      };
    }

    reset() {
      this.events = [];
      this.sequence = 0;
    }
  }

  return Object.freeze({
    SCHEMA_VERSION,
    BIN_MINUTES,
    BIN_COUNT,
    EVENT_TYPES,
    DEFAULT_CONFIG,
    SmartContextEngine,
    normalizeConfig,
    sanitizeEvent,
    pruneEvents,
    buildHabitModel,
    estimateSleepWindow,
    habitScore,
    responseScore,
    banditScore,
    inferContext,
    serviceCompletedToday,
    rankCandidates,
    chooseIntervention,
    parseTime,
    isWithinWrapped,
    minuteOfDay,
    timeBin,
    dateKey,
  });
});
