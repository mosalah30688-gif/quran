'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const AUDIT = 'audit/sources/tajweed-riwayat/2026-11-02';
const readJson = (relative) => JSON.parse(fs.readFileSync(path.join(ROOT, relative), 'utf8'));
const sources = readJson(`${AUDIT}/SOURCE.json`);
const inventory = readJson(`${AUDIT}/RULE_INVENTORY.json`);
const countAudit = readJson(`${AUDIT}/DURI_COUNT_AUDIT.json`);
const candidates = readJson('audit/tajweed-source-candidates.json');

test('exact non-Hafs routes are documented while every wajh stays blocked', () => {
  const expected = {
    warsh: ['warsh-an-nafi', 'al-azraq-via-al-shatibiyyah'],
    qalun: ['qalun-an-nafi', 'abu-nashit-via-al-shatibiyyah'],
    duri: ['al-duri-an-abi-amr', 'abu-al-zaraa-via-al-shatibiyyah'],
  };
  const scopeById = Object.fromEntries(sources.scopes.map((scope) => [scope.settingId, scope]));
  const candidateById = Object.fromEntries(candidates.riwayat.map((entry) => [entry.settingId, entry]));
  for (const [settingId, [riwayah, tariq]] of Object.entries(expected)) {
    const scope = scopeById[settingId];
    assert.equal(scope.riwayah, riwayah);
    assert.equal(scope.tariq, tariq);
    assert.equal(scope.tariqEvidenceStatus, 'PASS');
    assert.match(scope.wajhStatus, /^BLOCKED_/);
    assert.equal(scope.annotationCorpusStatus, 'MISSING');

    const candidate = candidateById[settingId];
    assert.equal(candidate.targetScope.riwayah, riwayah);
    assert.equal(candidate.targetScope.tariq, tariq);
    assert.equal(candidate.gates.documentedTariq, 'PASS');
    assert.equal(candidate.gates.documentedWajh, 'FAIL');
    assert.equal(candidate.publishableAsApproved, false);
  }
});

test('rule inventory is a locator-only topic map, never an extracted curriculum', () => {
  assert.equal(inventory.purpose, 'REFERENCE_TOPIC_MAP_ONLY_NOT_A_RULESET_OR_CURRICULUM');
  assert.equal(inventory.metadataOnly, true);
  assert.equal(inventory.containsQuranText, false);
  assert.equal(inventory.containsCopiedRuleProse, false);
  assert.equal(inventory.containsAnnotationSpans, false);
  assert.equal(inventory.containsTrainingExamples, false);
  assert.deepEqual(
    Object.fromEntries(inventory.scopes.map((scope) => [scope.settingId, scope.topics.length])),
    { warsh: 17, qalun: 14, duri: 12 },
  );
  for (const scope of inventory.scopes) {
    assert.equal(scope.ruleExtractionStatus, 'NOT_STARTED');
    assert.equal(scope.completeRuleInventoryGate, 'FAIL');
    assert.equal(scope.scope.wajh, 'not-yet-fixed');
  }

  const forbidden = new Set([
    'text', 'quranText', 'ruleText', 'example', 'examples', 'ayah', 'ayahs',
    'annotations', 'spans',
  ]);
  const stack = [inventory];
  while (stack.length) {
    const value = stack.pop();
    if (Array.isArray(value)) stack.push(...value);
    else if (value && typeof value === 'object') {
      for (const [key, nested] of Object.entries(value)) {
        assert.equal(forbidden.has(key), false, `forbidden topic-map field ${key}`);
        stack.push(nested);
      }
    }
  }
});

test('Duri count audit keeps the official conflict separate from the 67:9 regression', () => {
  const totals = Object.fromEntries(countAudit.observations.map((entry) => [
    entry.observationId, entry.totalAyahs,
  ]));
  assert.deepEqual(totals, {
    'official-introduction-count': 6214,
    'official-data-package-count': 6217,
    'rendered-archive-embedded-count': 6217,
    'quranpedia-current-dump-count': 6218,
  });
  assert.equal(countAudit.quranpedia67Regression.status, 'CONFIRMED');
  assert.equal(countAudit.quranpedia67Regression.officialSurahCount, 30);
  assert.equal(countAudit.quranpedia67Regression.currentDumpSurahCount, 31);
  assert.equal(countAudit.quranpedia67Regression.safeAutomaticRepair, false);

  const differences = countAudit.comparisonAgainstOfficialWarshAndQalun6214Datasets.rows;
  assert.equal(differences.length, 12);
  assert.equal(differences.reduce((sum, row) => sum + row.delta, 0), 3);
  assert.equal(countAudit.countingTraditionContext.resolutionStatus, 'NOT_RESOLVED');
  assert.equal(countAudit.runtimeAction, 'NONE');
});

test('reference PDFs remain remote metadata and runtime curricula stay empty', () => {
  const pdfs = fs.readdirSync(path.join(ROOT, AUDIT), { recursive: true })
    .filter((name) => String(name).toLowerCase().endsWith('.pdf'));
  assert.deepEqual(pdfs, []);
  assert.equal(sources.releaseConclusion.status, 'QUARANTINED_NOT_PUBLISHABLE');
  assert.equal(sources.releaseConclusion.runtimeChanges, 0);
  assert.equal(sources.releaseConclusion.approvedCurricula, 0);

  const registry = readJson('tajweed-scope-registry.json');
  for (const settingId of ['warsh', 'qalun', 'duri']) {
    const matches = registry.settings.filter((entry) => entry.settingIds.includes(settingId));
    assert.equal(matches.length, 1);
    assert.equal(matches[0].status, 'BLOCKED_NO_APPROVED_CORPUS');
    assert.deepEqual(matches[0].curricula, []);
  }
});

test('pinned reference-source verifier passes', () => {
  const result = spawnSync('python3', ['scripts/verify_tajweed_reference_sources.py'], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.match(result.stdout, /Abu Nashit via al-Shatibiyyah documented/);
  assert.match(result.stdout, /Quranpedia Duri 67:9 split regression: quarantined/);
  assert.match(result.stdout, /runtime curricula activated: 0/);
});
