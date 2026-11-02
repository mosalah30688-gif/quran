'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const readJson = (name) => JSON.parse(fs.readFileSync(path.join(ROOT, name), 'utf8'));
const candidates = readJson('audit/tajweed-source-candidates.json');
const analysis = readJson('audit/tajweed-candidates/warsh-al-azraq-qud-v1.analysis.json');

test('all non-Hafs source candidates remain explicitly non-publishable', () => {
  assert.equal(candidates.purpose, 'QUARANTINE_ONLY_NOT_RUNTIME_DATA');
  assert.equal(candidates.policy.candidateMayBeShownAsApproved, false);
  assert.deepEqual(candidates.riwayat.map((entry) => entry.settingId).sort(),
    ['duri', 'qalun', 'warsh']);
  for (const entry of candidates.riwayat) {
    assert.equal(entry.publishableAsApproved, false);
    assert.ok(Object.values(entry.gates).includes('FAIL'));
    assert.ok(entry.blockedReasonsAr.length >= 2);
  }
});

test('Warsh technical report records complete integrity but unsafe text binding', () => {
  assert.equal(analysis.scope.riwayah, 'warsh-an-nafi');
  assert.equal(analysis.scope.tariq, 'al-azraq');
  assert.equal(analysis.technicalChecks.pages, 604);
  assert.equal(analysis.technicalChecks.uniqueAyahs, 6214);
  assert.equal(analysis.technicalChecks.ruleIdentifiers, 46);
  assert.equal(analysis.technicalChecks.ruleAssignments, 212214);
  assert.equal(analysis.technicalChecks.textHashFailures, 0);
  assert.equal(analysis.technicalChecks.invalidAnnotationSpans, 0);
  assert.equal(analysis.projectBinding.unresolvedTextDifferences, 250);
  assert.equal(analysis.projectBinding.pageDifferences, 58);
  assert.equal(analysis.projectBinding.safeAutomaticOffsetTransfer, false);
  assert.equal(analysis.releaseGate.status, 'QUARANTINED_NOT_PUBLISHABLE');
  assert.equal(analysis.releaseGate.publishableAsApproved, false);
});

test('quarantine report contains metadata only, not Quran or annotation payloads', () => {
  const forbidden = new Set(['text', 'ayahs', 'spans', 'words', 'annotations']);
  const stack = [analysis];
  while (stack.length) {
    const value = stack.pop();
    if (Array.isArray(value)) stack.push(...value);
    else if (value && typeof value === 'object') {
      for (const [key, nested] of Object.entries(value)) {
        assert.equal(forbidden.has(key), false, `forbidden report field ${key}`);
        stack.push(nested);
      }
    }
  }
});

test('source quarantine verifier passes and analyzer rejects an unpinned archive', () => {
  const verified = spawnSync('python3', ['scripts/verify_tajweed_source_candidates.py'], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(verified.status, 0, verified.stderr || verified.stdout);
  assert.match(verified.stdout, /runtime curricula leaked: 0/);

  const badArchive = path.join(os.tmpdir(), `siraj-bad-warsh-${process.pid}.zip`);
  fs.writeFileSync(badArchive, 'not a pinned archive');
  try {
    const rejected = spawnSync('python3', [
      'scripts/analyze_warsh_tajweed_candidate.py', badArchive,
    ], { cwd: ROOT, encoding: 'utf8' });
    assert.notEqual(rejected.status, 0);
    assert.match(rejected.stderr, /audit failed/);
  } finally {
    fs.rmSync(badArchive, { force: true });
  }
});

test('quarantined source material is absent from runtime and curriculum directories', () => {
  for (const relative of [
    'warsh-tajweed-v1.zip',
    'www/warsh-tajweed-v1.zip',
    'tajweed-curricula/warsh-al-azraq.json',
    'www/tajweed-curricula/warsh-al-azraq.json',
  ]) assert.equal(fs.existsSync(path.join(ROOT, relative)), false, relative);
});
