/*
 * Siraj Smart Services v1
 *
 * Pure mapping between Siraj's local service state and generic candidates for
 * smart-context.js. No storage, network, DOM, or device permissions live here.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.SirajSmartServices = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERSION = 1;

  const REASON_TEXT = Object.freeze({
    HABIT_MATCH: 'هذا وقت اعتدت استخدام هذه الخدمة فيه.',
    COLD_START: 'اقتراح مبدئي حتى تتكوّن عادتك المحلية؛ ليس استنتاجًا عنك.',
    DUE_NOW: 'الخدمة مناسبة لهذا الوقت أو مستحقة الآن.',
    SERVICE_NEED: 'هناك متابعة مفيدة لم تُنجز اليوم.',
    CONTENT_RELEVANCE: 'الاقتراح مرتبط بما تستخدمه داخل سراج.',
    JUST_WOKE_UP: 'ظهر في نافذة الاستيقاظ المعتادة.',
    PREPARING_FOR_SLEEP: 'ظهر قبل نافذة النوم، وليس خلالها.',
  });

  const BLOCK_TEXT = Object.freeze({
    ENGINE_DISABLED: 'الاقتراحات الذكية متوقفة.',
    CANDIDATE_DISABLED: 'هذه الخدمة مستبعدة من الاقتراحات.',
    LIKELY_SLEEPING: 'لم يظهر شيء لأن الوقت يقع داخل نافذة النوم المحتملة.',
    QUIET_HOURS: 'لم يظهر شيء لأن الوقت داخل ساعات الهدوء.',
    DAILY_CAP: 'اكتفى سراج بعدد اقتراحات اليوم.',
    COOLDOWN: 'لن يظهر اقتراح جديد قبل انتهاء فترة التهدئة.',
    ALREADY_COMPLETED: 'أُنجزت هذه الخدمة اليوم.',
    STATE_MISMATCH: 'الوقت الحالي لا يلائم هذه الخدمة.',
    TOO_EARLY: 'موعد هذه الخدمة لم يحن بعد.',
    TOO_LATE: 'انتهت نافذة هذه الخدمة.',
    BELOW_THRESHOLD: 'لم تكن فائدة الاقتراح كافية لعرضه.',
  });

  function number(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function integer(value, fallback = 0, low = 0, high = 1000000) {
    return Math.min(high, Math.max(low, Math.round(number(value, fallback))));
  }

  function completedSet(value) {
    if (value instanceof Set) return value;
    return new Set(Array.isArray(value) ? value.map(String) : []);
  }

  function knownSet(value) {
    if (value instanceof Set) return value;
    return new Set(Array.isArray(value) ? value.map(String) : []);
  }

  function baseCandidate(value) {
    return {
      defaultHabit: 0.62,
      continuity: 0.55,
      relevance: 0.7,
      priority: 0.5,
      ...value,
    };
  }

  function buildCandidates(input, nowValue = Date.now()) {
    const state = input && typeof input === 'object' ? input : {};
    const completed = completedSet(state.completedServices);
    const known = knownSet(state.knownServices);
    const readToday = integer(state.readToday, 0, 0, 604);
    const pointer = integer(state.wirdPointer, 1, 1, 604);
    const average = Math.max(0, number(state.readingAverage, 0));
    const memoDue = integer(state.memoDue, 0, 0, 10000);
    const candidates = [];

    if (!readToday && !completed.has('wird')) {
      candidates.push(baseCandidate({
        id: 'continue_wird',
        service: 'wird',
        due: 0.92,
        need: average > 0 ? 0.88 : 0.72,
        continuity: pointer > 1 ? 0.85 : 0.58,
        relevance: 0.82,
        priority: 0.72,
        defaultHabit: 0.68,
        completionTypes: ['READ_PAGE'],
        title: 'وردك اليوم',
        body: `تابع بهدوء من الصفحة ${pointer}، واقرأ ما تيسر دون إلزام.`,
        cta: 'متابعة القراءة',
        action: 'open_wird',
      }));
    }

    if (!completed.has('adhkar_wake')) {
      candidates.push(baseCandidate({
        id: 'adhkar_after_wake',
        service: 'adhkar_wake',
        due: 0.9,
        need: 0.76,
        priority: 0.9,
        defaultHabit: 0.72,
        requiredStates: ['JUST_WOKE_UP'],
        completionTypes: ['SERVICE_COMPLETE', 'COMPLETE_ADHKAR'],
        title: 'أذكار الاستيقاظ',
        body: 'أذكار قصيرة لبداية يومك.',
        cta: 'فتح الأذكار',
        action: 'open_adhkar:wake',
      }));
    }

    if (!completed.has('adhkar_morning')) {
      candidates.push(baseCandidate({
        id: 'adhkar_morning',
        service: 'adhkar_morning',
        due: 0.88,
        need: 0.8,
        priority: 0.82,
        defaultHabit: 0.68,
        requiredStates: ['MORNING_WINDOW'],
        completionTypes: ['SERVICE_COMPLETE', 'COMPLETE_ADHKAR'],
        title: 'أذكار الصباح',
        body: 'هذا وقت مناسب لأذكار الصباح.',
        cta: 'فتح أذكار الصباح',
        action: 'open_adhkar:morning',
      }));
    }

    if (!completed.has('adhkar_evening')) {
      candidates.push(baseCandidate({
        id: 'adhkar_evening',
        service: 'adhkar_evening',
        due: 0.88,
        need: 0.8,
        priority: 0.82,
        defaultHabit: 0.68,
        requiredStates: ['EVENING_WINDOW'],
        completionTypes: ['SERVICE_COMPLETE', 'COMPLETE_ADHKAR'],
        title: 'أذكار المساء',
        body: 'هذا وقت مناسب لأذكار المساء.',
        cta: 'فتح أذكار المساء',
        action: 'open_adhkar:evening',
      }));
    }

    if (memoDue > 0 && !completed.has('memorization')) {
      candidates.push(baseCandidate({
        id: 'memorization_due',
        service: 'memorization',
        due: 0.98,
        need: Math.min(1, 0.78 + memoDue * 0.04),
        continuity: 0.9,
        priority: 0.94,
        defaultHabit: 0.64,
        completionTypes: ['COMPLETE_MEMORIZATION'],
        title: 'مراجعة الحفظ',
        body: memoDue === 1 ? 'لديك مقطع واحد للمراجعة اليوم.'
          : `لديك ${memoDue} مقاطع للمراجعة اليوم.`,
        cta: 'بدء المراجعة',
        action: 'open_memorization',
      }));
    }

    // لا نقترح خدمات استكشافية في البداية الباردة؛ تظهر فقط بعد أن يستخدمها
    // الشخص فعلاً، ثم يحدد المحرك توقيتها محليًا.
    if (known.has('recitation')) {
      candidates.push(baseCandidate({
        id: 'continue_recitation',
        service: 'recitation',
        due: 0.46,
        need: 0.4,
        continuity: 0.7,
        relevance: 0.64,
        priority: 0.34,
        defaultHabit: 0.5,
        title: 'استمع إلى التلاوة',
        body: 'يمكنك متابعة الاستماع من موضعك المحفوظ.',
        cta: 'فتح المصحف',
        action: 'open_recitation',
      }));
    }

    if (known.has('tajweed') && !completed.has('tajweed')) {
      candidates.push(baseCandidate({
        id: 'continue_tajweed',
        service: 'tajweed',
        due: 0.5,
        need: 0.48,
        continuity: 0.65,
        relevance: 0.7,
        priority: 0.36,
        defaultHabit: 0.52,
        completionTypes: ['COMPLETE_TAJWEED_LESSON'],
        title: 'مراجعة التجويد',
        body: 'راجع حكمًا قصيرًا في الوقت الذي يناسب عادتك.',
        cta: 'فتح أحكام التجويد',
        action: 'open_tajweed',
      }));
    }

    // Keep the function deterministic for equal input; nowValue is accepted so
    // future service windows can be added without changing the public contract.
    void nowValue;
    return candidates;
  }

  function explainSelection(selection) {
    if (!selection || !selection.candidate) return '';
    const reasons = Array.isArray(selection.reasons) ? selection.reasons : [];
    const parts = reasons.map((reason) => REASON_TEXT[reason]).filter(Boolean);
    if (!parts.length) parts.push('اختير لأنه الأنسب بين الخدمات المتاحة الآن.');
    return `${parts.slice(0, 2).join(' ')} تتم المعالجة من سجل محدود محفوظ على هذا الجهاز فقط.`;
  }

  function describeBlock(reason) {
    return BLOCK_TEXT[String(reason || '').toUpperCase()] || 'لا يوجد اقتراح مناسب الآن.';
  }

  function serviceForAdhkar(category) {
    const token = String(category || '').trim().toLowerCase();
    return /^[a-z][a-z0-9_-]{0,31}$/.test(token) ? `adhkar_${token}` : 'adhkar';
  }

  function planNextDecision(candidatesAt, evaluateAt, options) {
    if (typeof candidatesAt !== 'function' || typeof evaluateAt !== 'function') return null;
    const input = options && typeof options === 'object' ? options : {};
    const now = number(input.now, Date.now());
    const stepMinutes = integer(input.stepMinutes, 30, 15, 120);
    const minDelayMinutes = integer(input.minDelayMinutes, 30, 15, 720);
    const horizonHours = integer(input.horizonHours, 30, 1, 48);
    const stepMs = stepMinutes * 60 * 1000;
    const endAt = now + horizonHours * 60 * 60 * 1000;
    let at = Math.ceil((now + minDelayMinutes * 60 * 1000) / stepMs) * stepMs;
    for (; at <= endAt; at += stepMs) {
      try {
        const candidates = candidatesAt(at);
        if (!Array.isArray(candidates) || !candidates.length) continue;
        const decision = evaluateAt(candidates, at);
        if (decision && decision.selected) {
          return { at, selection: decision.selected, context: decision.context || null };
        }
      } catch (error) {
        // Planning must fail closed; a bad optional candidate cannot schedule a notification.
        void error;
        return null;
      }
    }
    return null;
  }

  return Object.freeze({
    VERSION,
    REASON_TEXT,
    BLOCK_TEXT,
    buildCandidates,
    explainSelection,
    describeBlock,
    serviceForAdhkar,
    planNextDecision,
  });
});
