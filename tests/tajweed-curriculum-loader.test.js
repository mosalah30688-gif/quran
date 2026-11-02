'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const Loader = require('../tajweed-curriculum-loader.js');
const ROOT = path.resolve(__dirname, '..');
const digest = async (text) => crypto.createHash('sha256').update(text, 'utf8').digest('hex');

async function fixture(options = {}) {
  const textPayload = {
    riwayat: {
      warsh: [[1, 1, 1, 'ءَاب']],
    },
  };
  const textRaw = JSON.stringify(textPayload);
  const textHash = await digest(textRaw);
  const packageData = {
    schemaVersion: 1,
    packageId: 'warsh-al-azraq-test-v1',
    status: options.approved ? 'APPROVED' : 'PENDING_SCHOLARLY_REVIEW',
    publishableAsApproved: !!options.approved,
    scope: {
      riwayah: 'warsh-an-nafi',
      tariq: 'al-azraq',
      wajh: 'test-face',
      edition: 'test-edition-v1',
    },
    textBinding: {
      asset: 'quran-riwayat.json',
      dataset: 'warsh',
      sha256: textHash,
      offsetUnit: 'unicode-code-point',
      normalization: 'NFC',
    },
    sources: [{
      sourceId: 'licensed-source-v1',
      title: 'مصدر اختباري مرخص',
      uri: 'https://example.test/source',
      snapshotDate: '2026-11-02',
      sha256: '0'.repeat(64),
      licenseEvidence: 'https://example.test/license',
    }],
    rules: [{
      id: 'naql',
      nameAr: 'النقل',
      summaryAr: 'ملخص اختباري.',
      detailAr: 'تفصيل اختباري مستقل.',
      color: '#123ABC',
      sourceRefs: ['licensed-source-v1'],
    }],
    annotations: [{
      surah: 1,
      ayah: 1,
      start: 0,
      end: options.badSpan ? 99 : 2,
      ruleId: 'naql',
      sourceRefs: ['licensed-source-v1'],
    }],
    review: options.approved ? {
      status: 'APPROVED',
      reviewerName: 'المراجع الأول',
      reviewerQualification: 'متخصص في ورش من طريق الأزرق',
      reviewDate: '2026-11-02',
      reviewedSha256: '',
      releaseApprover: 'المعتمد الثاني',
      evidence: 'https://example.test/review',
    } : { status: 'NOT_REVIEWED' },
  };
  if (options.approved) {
    const reviewed = {};
    for (const key of ['scope', 'textBinding', 'sources', 'rules', 'annotations']) {
      reviewed[key] = packageData[key];
    }
    packageData.review.reviewedSha256 = await digest(Loader.stableStringify(reviewed));
  }
  const packageRaw = JSON.stringify(packageData);
  const packageHash = await digest(packageRaw);
  const artifact = 'tajweed-curricula/warsh-al-azraq-test-v1.json';
  const registry = {
    fallbackPolicy: 'FORBIDDEN_BETWEEN_SCOPES',
    settings: [{
      settingIds: ['warsh'],
      riwayah: { id: 'warsh-an-nafi', labelAr: 'ورش عن نافع' },
      textEdition: {
        asset: 'quran-riwayat.json',
        dataset: 'warsh',
        sha256: textHash,
        verseRecords: 1,
      },
      curricula: [{
        artifact,
        sha256: packageHash,
        status: packageData.status,
        publishableAsApproved: packageData.publishableAsApproved,
        scope: packageData.scope,
      }],
    }],
  };
  const files = new Map([
    [artifact, packageRaw],
    ['quran-riwayat.json', textRaw],
  ]);
  return {
    registry,
    packageData,
    artifact,
    files,
    getText: async (name) => {
      if (!files.has(name)) throw new Error(`missing ${name}`);
      return files.get(name);
    },
  };
}

test('browser-compatible SHA-256 helper hashes UTF-8 text deterministically', async () => {
  assert.equal(
    await Loader.sha256Text('abc', crypto.webcrypto),
    'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
  );
});

test('independent package loads only after artifact, scope, text, and span checks', async () => {
  const data = await fixture();
  const result = await Loader.loadRegistryCurricula({
    registry: data.registry,
    getText: data.getText,
    digestText: digest,
  });
  assert.deepEqual(result.errors, []);
  assert.equal(result.curricula.length, 1);
  const curriculum = result.curricula[0];
  assert.equal(curriculum.artifact, data.artifact);
  assert.equal(curriculum.artifactSha256, data.registry.settings[0].curricula[0].sha256);
  assert.deepEqual(curriculum.appliesToSettings, ['warsh']);
  assert.equal(curriculum.scope.tariq, 'al-azraq');
  assert.equal(curriculum.rules[0].name, 'النقل');
  assert.equal(curriculum.rules[0].color, '#123ABC');
  assert.equal(curriculum.rules[0].example.text, 'ءَ');
  assert.equal(curriculum.publishableAsApproved, false);
});

test('approved package requires a canonical reviewed hash and a second approver', async () => {
  const data = await fixture({ approved: true });
  const accepted = await Loader.loadRegistryCurricula({
    registry: data.registry,
    getText: data.getText,
    digestText: digest,
  });
  assert.equal(accepted.errors.length, 0);
  assert.equal(accepted.curricula[0].status, 'APPROVED');
  assert.equal(accepted.curricula[0].publishableAsApproved, true);

  data.packageData.review.releaseApprover = data.packageData.review.reviewerName;
  const badRaw = JSON.stringify(data.packageData);
  data.files.set(data.artifact, badRaw);
  data.registry.settings[0].curricula[0].sha256 = await digest(badRaw);
  const rejected = await Loader.loadRegistryCurricula({
    registry: data.registry,
    getText: data.getText,
    digestText: digest,
  });
  assert.equal(rejected.curricula.length, 0);
  assert.equal(rejected.errors[0].code, 'SECOND_APPROVER_REQUIRED');
});

test('artifact tampering and out-of-bounds Unicode spans fail closed', async () => {
  const tampered = await fixture();
  tampered.files.set(tampered.artifact, tampered.files.get(tampered.artifact) + ' ');
  const hashFailure = await Loader.loadRegistryCurricula({
    registry: tampered.registry,
    getText: tampered.getText,
    digestText: digest,
  });
  assert.equal(hashFailure.curricula.length, 0);
  assert.equal(hashFailure.errors[0].code, 'PACKAGE_HASH_MISMATCH');

  const badSpan = await fixture({ badSpan: true });
  const spanFailure = await Loader.loadRegistryCurricula({
    registry: badSpan.registry,
    getText: badSpan.getText,
    digestText: digest,
  });
  assert.equal(spanFailure.curricula.length, 0);
  assert.equal(spanFailure.errors[0].code, 'ANNOTATION_SPAN_INVALID');
});

test('cross-scope fallback policy is rejected before any package is read', async () => {
  const data = await fixture();
  data.registry.fallbackPolicy = 'ALLOW_HAFS_FALLBACK';
  await assert.rejects(
    Loader.loadRegistryCurricula({
      registry: data.registry,
      getText: data.getText,
      digestText: digest,
    }),
    (error) => error.code === 'REGISTRY_INVALID'
  );
});

test('current repository registry has no independent runtime package yet', async () => {
  const registry = JSON.parse(fs.readFileSync(path.join(ROOT, 'tajweed-scope-registry.json'), 'utf8'));
  const result = await Loader.loadRegistryCurricula({
    registry,
    getText: async () => { throw new Error('no independent artifact should be requested'); },
    digestText: digest,
  });
  assert.deepEqual(result, { curricula: [], errors: [] });
});
