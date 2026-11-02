(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.SirajTajweedCurriculumLoader = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';

  const TOKEN_RE = /^[a-z0-9][a-z0-9._-]*$/;
  const SHA256_RE = /^[0-9a-f]{64}$/;
  const PACKAGE_RE = /^tajweed-curricula\/[a-z0-9][a-z0-9._-]*\.json$/;
  const ROOT_ASSET_RE = /^[a-z0-9][a-z0-9._-]*\.json$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  const COLOR_RE = /^#[0-9a-fA-F]{6}$/;
  const PACKAGE_FIELDS = [
    'schemaVersion', 'packageId', 'status', 'publishableAsApproved', 'scope',
    'textBinding', 'sources', 'rules', 'annotations', 'review',
  ];
  const SCOPE_FIELDS = ['riwayah', 'tariq', 'wajh', 'edition'];
  const REVIEW_FIELDS = [
    'status', 'reviewerName', 'reviewerQualification', 'reviewDate',
    'reviewedSha256', 'releaseApprover', 'evidence',
  ];
  const MAX_PACKAGE_CHARS = 96 * 1024 * 1024;
  const MAX_TEXT_ASSET_CHARS = 32 * 1024 * 1024;

  class CurriculumError extends Error {
    constructor(code) {
      super(code);
      this.name = 'CurriculumError';
      this.code = code;
    }
  }

  function fail(code) {
    throw new CurriculumError(code);
  }

  function isObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function exactKeys(value, expected) {
    if (!isObject(value)) return false;
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    return actual.length === wanted.length && actual.every((key, index) => key === wanted[index]);
  }

  function hasOnlyKeys(value, allowed) {
    return isObject(value) && Object.keys(value).every((key) => allowed.includes(key));
  }

  function validToken(value) {
    return typeof value === 'string' && TOKEN_RE.test(value);
  }

  function validSha256(value) {
    return typeof value === 'string' && SHA256_RE.test(value);
  }

  function normalizeScope(value) {
    if (!exactKeys(value, SCOPE_FIELDS)) return null;
    const scope = {};
    for (const field of SCOPE_FIELDS) {
      if (!validToken(value[field])) return null;
      scope[field] = value[field];
    }
    return scope;
  }

  function scopeKey(value) {
    const scope = normalizeScope(value);
    return scope ? SCOPE_FIELDS.map((field) => scope[field]).join('/') : '';
  }

  function sameScope(left, right) {
    const leftKey = scopeKey(left);
    return !!leftKey && leftKey === scopeKey(right);
  }

  function stableStringify(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']';
    return '{' + Object.keys(value).sort().map((key) => (
      JSON.stringify(key) + ':' + stableStringify(value[key])
    )).join(',') + '}';
  }

  async function sha256Text(text, cryptoApi) {
    if (typeof text !== 'string') fail('HASH_INPUT_NOT_TEXT');
    const api = cryptoApi || root.crypto;
    if (!api || !api.subtle || typeof api.subtle.digest !== 'function'
        || typeof TextEncoder === 'undefined') fail('SHA256_UNAVAILABLE');
    const digest = await api.subtle.digest('SHA-256', new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  function parseJson(text, code) {
    if (typeof text !== 'string' || !text.trim()) fail(code + '_EMPTY');
    try { return JSON.parse(text); } catch (_) { fail(code + '_INVALID_JSON'); }
  }

  function requireNonemptyText(value, code) {
    if (typeof value !== 'string' || !value.trim()) fail(code);
    return value.trim();
  }

  function validateRefs(value, known, code) {
    if (!Array.isArray(value) || !value.length) fail(code);
    const seen = new Set();
    for (const ref of value) {
      if (!validToken(ref) || !known.has(ref) || seen.has(ref)) fail(code);
      seen.add(ref);
    }
  }

  function resolveRows(asset, dataset, payload) {
    if (asset === 'quran-tajweed.json' && dataset === 'quran-tajweed' && Array.isArray(payload)) {
      return payload;
    }
    if (asset === 'quran-riwayat.json' && isObject(payload)
        && isObject(payload.riwayat) && Array.isArray(payload.riwayat[dataset])) {
      return payload.riwayat[dataset];
    }
    if (asset === 'quran-hafs.json' && isObject(payload) && Array.isArray(payload[dataset])) {
      return payload[dataset];
    }
    fail('TEXT_DATASET_MISSING');
  }

  function verseIndex(rows, expectedRecords, normalization) {
    if (!Number.isInteger(expectedRecords) || expectedRecords < 1 || rows.length !== expectedRecords) {
      fail('TEXT_RECORD_COUNT_MISMATCH');
    }
    const verses = new Map();
    for (const row of rows) {
      if (!Array.isArray(row) || row.length < 4
          || !Number.isInteger(row[0]) || row[0] < 1 || row[0] > 114
          || !Number.isInteger(row[1]) || row[1] < 1 || typeof row[3] !== 'string') {
        fail('TEXT_ROW_INVALID');
      }
      const key = row[0] + ':' + row[1];
      if (verses.has(key)) fail('TEXT_REFERENCE_DUPLICATE');
      const text = normalization === 'NFC' ? row[3].normalize('NFC') : row[3];
      verses.set(key, text);
    }
    return verses;
  }

  function validateSources(sources) {
    if (!Array.isArray(sources) || !sources.length) fail('SOURCES_MISSING');
    const ids = new Set();
    for (const source of sources) {
      if (!exactKeys(source, [
        'sourceId', 'title', 'uri', 'snapshotDate', 'sha256', 'licenseEvidence',
      ])) fail('SOURCE_FIELDS_INVALID');
      if (!validToken(source.sourceId) || ids.has(source.sourceId)) fail('SOURCE_ID_INVALID');
      ids.add(source.sourceId);
      requireNonemptyText(source.title, 'SOURCE_TITLE_MISSING');
      if (typeof source.uri !== 'string' || !source.uri.includes('://')) fail('SOURCE_URI_INVALID');
      if (typeof source.snapshotDate !== 'string' || !DATE_RE.test(source.snapshotDate)) {
        fail('SOURCE_DATE_INVALID');
      }
      if (!validSha256(source.sha256)) fail('SOURCE_HASH_INVALID');
      requireNonemptyText(source.licenseEvidence, 'SOURCE_LICENSE_MISSING');
    }
    return ids;
  }

  function validateRules(rules, sourceIds) {
    if (!Array.isArray(rules) || !rules.length) fail('RULES_MISSING');
    const ids = new Set();
    return rules.map((rule, index) => {
      if (!exactKeys(rule, ['id', 'nameAr', 'summaryAr', 'detailAr', 'color', 'sourceRefs'])) {
        fail('RULE_FIELDS_INVALID');
      }
      if (!validToken(rule.id) || ids.has(rule.id)) fail('RULE_ID_INVALID');
      ids.add(rule.id);
      const name = requireNonemptyText(rule.nameAr, 'RULE_NAME_MISSING');
      const summary = requireNonemptyText(rule.summaryAr, 'RULE_SUMMARY_MISSING');
      const detail = requireNonemptyText(rule.detailAr, 'RULE_DETAIL_MISSING');
      if (typeof rule.color !== 'string' || !COLOR_RE.test(rule.color)) fail('RULE_COLOR_INVALID');
      validateRefs(rule.sourceRefs, sourceIds, 'RULE_SOURCE_REFS_INVALID');
      return {
        id: rule.id,
        order: index + 1,
        name,
        prompt: `اشرح حكم «${name}» ثم قارنه بالجواب.`,
        answer: summary === detail ? detail : `${summary} ${detail}`,
        color: rule.color.toUpperCase(),
        example: null,
      };
    });
  }

  function validateReview(packageData, digestText) {
    const status = packageData.status;
    const publishable = packageData.publishableAsApproved;
    const review = packageData.review;
    if (!hasOnlyKeys(review, REVIEW_FIELDS) || typeof review.status !== 'string') {
      fail('REVIEW_FIELDS_INVALID');
    }
    if (status === 'APPROVED') {
      if (publishable !== true || review.status !== 'APPROVED' || !exactKeys(review, REVIEW_FIELDS)) {
        fail('APPROVAL_STATE_INVALID');
      }
      for (const field of [
        'reviewerName', 'reviewerQualification', 'reviewDate', 'reviewedSha256',
        'releaseApprover', 'evidence',
      ]) requireNonemptyText(review[field], 'APPROVAL_FIELD_MISSING');
      if (!DATE_RE.test(review.reviewDate) || !validSha256(review.reviewedSha256)) {
        fail('APPROVAL_VALUE_INVALID');
      }
      if (review.reviewerName === review.releaseApprover) fail('SECOND_APPROVER_REQUIRED');
      const reviewPayload = {};
      for (const field of ['scope', 'textBinding', 'sources', 'rules', 'annotations']) {
        reviewPayload[field] = packageData[field];
      }
      return Promise.resolve(digestText(stableStringify(reviewPayload))).then((actual) => {
        if (actual !== review.reviewedSha256) fail('REVIEWED_HASH_MISMATCH');
      });
    }
    if (!['DRAFT', 'PENDING_SCHOLARLY_REVIEW'].includes(status)
        || publishable !== false
        || !['NOT_REVIEWED', 'CHANGES_REQUESTED'].includes(review.status)) {
      fail('UNAPPROVED_STATE_INVALID');
    }
    return Promise.resolve();
  }

  async function loadOne(pointer, entry, getText, digestText) {
    if (!isObject(pointer) || !PACKAGE_RE.test(pointer.artifact || '')) fail('ARTIFACT_PATH_UNSAFE');
    if (!validSha256(pointer.sha256)) fail('ARTIFACT_HASH_INVALID');
    if (!['DRAFT', 'PENDING_SCHOLARLY_REVIEW', 'APPROVED'].includes(pointer.status)
        || typeof pointer.publishableAsApproved !== 'boolean') fail('POINTER_STATE_INVALID');
    const pointerScope = normalizeScope(pointer.scope);
    if (!pointerScope || pointerScope.riwayah !== entry.riwayah.id) fail('POINTER_SCOPE_INVALID');

    const raw = await getText(pointer.artifact);
    if (typeof raw !== 'string' || raw.length > MAX_PACKAGE_CHARS) fail('PACKAGE_SIZE_INVALID');
    if (await digestText(raw) !== pointer.sha256) fail('PACKAGE_HASH_MISMATCH');
    const packageData = parseJson(raw, 'PACKAGE');
    if (!exactKeys(packageData, PACKAGE_FIELDS) || packageData.schemaVersion !== 1
        || !validToken(packageData.packageId)) fail('PACKAGE_FIELDS_INVALID');
    if (!sameScope(packageData.scope, pointerScope)
        || packageData.status !== pointer.status
        || packageData.publishableAsApproved !== pointer.publishableAsApproved) {
      fail('PACKAGE_POINTER_MISMATCH');
    }

    const binding = packageData.textBinding;
    if (!exactKeys(binding, ['asset', 'dataset', 'sha256', 'offsetUnit', 'normalization'])
        || !ROOT_ASSET_RE.test(binding.asset || '') || !validToken(binding.dataset)
        || !validSha256(binding.sha256) || binding.offsetUnit !== 'unicode-code-point'
        || !['NONE', 'NFC'].includes(binding.normalization)) fail('TEXT_BINDING_INVALID');
    const registryBinding = entry.textEdition;
    if (!isObject(registryBinding)
        || binding.asset !== registryBinding.asset
        || binding.dataset !== registryBinding.dataset
        || binding.sha256 !== registryBinding.sha256) fail('TEXT_REGISTRY_MISMATCH');

    const sourceIds = validateSources(packageData.sources);
    const learningRules = validateRules(packageData.rules, sourceIds);
    const rulesById = new Map(learningRules.map((rule) => [rule.id, rule]));
    await validateReview(packageData, digestText);

    const textRaw = await getText(binding.asset);
    if (typeof textRaw !== 'string' || textRaw.length > MAX_TEXT_ASSET_CHARS) fail('TEXT_SIZE_INVALID');
    if (await digestText(textRaw) !== binding.sha256) fail('TEXT_HASH_MISMATCH');
    const textPayload = parseJson(textRaw, 'TEXT');
    const rows = resolveRows(binding.asset, binding.dataset, textPayload);
    const verses = verseIndex(rows, registryBinding.verseRecords, binding.normalization);
    const codePoints = new Map();

    if (!Array.isArray(packageData.annotations) || !packageData.annotations.length) {
      fail('ANNOTATIONS_MISSING');
    }
    for (const annotation of packageData.annotations) {
      if (!isObject(annotation)) fail('ANNOTATION_INVALID');
      const required = ['surah', 'ayah', 'start', 'end', 'ruleId', 'sourceRefs'];
      const allowed = [...required, 'noteAr'];
      if (!required.every((field) => Object.prototype.hasOwnProperty.call(annotation, field))
          || !hasOnlyKeys(annotation, allowed)) fail('ANNOTATION_FIELDS_INVALID');
      if (!Number.isInteger(annotation.surah) || annotation.surah < 1 || annotation.surah > 114
          || !Number.isInteger(annotation.ayah) || annotation.ayah < 1
          || !Number.isInteger(annotation.start) || !Number.isInteger(annotation.end)
          || annotation.start < 0 || annotation.start >= annotation.end
          || !rulesById.has(annotation.ruleId)) fail('ANNOTATION_VALUE_INVALID');
      validateRefs(annotation.sourceRefs, sourceIds, 'ANNOTATION_SOURCE_REFS_INVALID');
      if (Object.prototype.hasOwnProperty.call(annotation, 'noteAr')
          && typeof annotation.noteAr !== 'string') fail('ANNOTATION_NOTE_INVALID');
      const ref = annotation.surah + ':' + annotation.ayah;
      if (!verses.has(ref)) fail('ANNOTATION_REFERENCE_MISSING');
      let points = codePoints.get(ref);
      if (!points) {
        points = Array.from(verses.get(ref));
        codePoints.set(ref, points);
      }
      if (annotation.end > points.length) fail('ANNOTATION_SPAN_INVALID');
      const rule = rulesById.get(annotation.ruleId);
      if (!rule.example) {
        rule.example = {
          text: points.slice(annotation.start, annotation.end).join(''),
          ayahText: points.join(''),
          surah: annotation.surah,
          ayah: annotation.ayah,
        };
      }
    }

    const label = requireNonemptyText(entry.riwayah.labelAr, 'RIWAYAH_LABEL_MISSING');
    return {
      id: packageData.packageId,
      artifact: pointer.artifact,
      artifactSha256: pointer.sha256,
      displayName: `${label} — ${pointerScope.tariq}`,
      scope: pointerScope,
      appliesToSettings: [...entry.settingIds],
      status: packageData.status,
      publishableAsApproved: packageData.publishableAsApproved,
      scopeWarning: packageData.status === 'APPROVED'
        ? 'حزمة مستقلة مرتبطة بهذه الطبعة ومثبتة المراجعة في سجلها.'
        : 'هذه الحزمة قيد المراجعة العلمية ولا تُعرض بوصفها اعتمادًا نهائيًا.',
      rules: learningRules,
    };
  }

  async function loadRegistryCurricula(options) {
    const registry = options && options.registry;
    const getText = options && options.getText;
    const digestText = options && options.digestText
      ? options.digestText : (text) => sha256Text(text, options && options.crypto);
    if (!isObject(registry) || registry.fallbackPolicy !== 'FORBIDDEN_BETWEEN_SCOPES'
        || !Array.isArray(registry.settings) || typeof getText !== 'function'
        || typeof digestText !== 'function') fail('REGISTRY_INVALID');

    const curricula = [];
    const errors = [];
    const seenArtifacts = new Set();
    const seenScopes = new Set();
    for (const entry of registry.settings) {
      if (!isObject(entry) || !Array.isArray(entry.settingIds) || !entry.settingIds.length
          || entry.settingIds.some((item) => !validToken(item))
          || !isObject(entry.riwayah) || !validToken(entry.riwayah.id)
          || !Array.isArray(entry.curricula)) {
        errors.push({ artifact: '', code: 'REGISTRY_ENTRY_INVALID' });
        continue;
      }
      for (const pointer of entry.curricula) {
        if (pointer && pointer.artifact === 'tajweed-learning-catalog.json') continue;
        const artifact = pointer && typeof pointer.artifact === 'string' ? pointer.artifact : '';
        try {
          if (seenArtifacts.has(artifact)) fail('ARTIFACT_DUPLICATE');
          const curriculum = await loadOne(pointer, entry, getText, digestText);
          const key = scopeKey(curriculum.scope);
          if (seenScopes.has(key)) fail('SCOPE_DUPLICATE');
          seenArtifacts.add(artifact);
          seenScopes.add(key);
          curricula.push(curriculum);
        } catch (error) {
          errors.push({
            artifact,
            code: error instanceof CurriculumError ? error.code : 'LOAD_FAILED',
          });
        }
      }
    }
    return { curricula, errors };
  }

  return Object.freeze({
    CurriculumError,
    normalizeScope,
    scopeKey,
    sameScope,
    stableStringify,
    sha256Text,
    loadRegistryCurricula,
  });
}));
