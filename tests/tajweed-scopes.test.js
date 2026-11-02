'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const readJson = (name) => JSON.parse(fs.readFileSync(path.join(ROOT, name), 'utf8'));
const sha256 = (name) => crypto.createHash('sha256')
  .update(fs.readFileSync(path.join(ROOT, name))).digest('hex');

const registry = readJson('tajweed-scope-registry.json');
const catalog = readJson('tajweed-learning-catalog.json');
const schema = readJson('tajweed-curriculum.schema.json');

test('scope registry covers every selectable mushaf once and forbids fallback', () => {
  const expected = new Set([
    'quran-uthmani', 'quran-simple', 'quran-uthmani-min', 'quran-tajweed',
    'warsh', 'qalun', 'duri',
  ]);
  const seen = new Set();
  assert.equal(registry.scopeKey, 'riwayah/tariq/wajh/edition');
  assert.equal(registry.fallbackPolicy, 'FORBIDDEN_BETWEEN_SCOPES');
  for (const entry of registry.settings) {
    for (const settingId of entry.settingIds) {
      assert.equal(seen.has(settingId), false, `duplicate setting ${settingId}`);
      seen.add(settingId);
    }
  }
  assert.deepEqual(seen, expected);
});

test('Warsh, Qalun and Duri fail closed without Hafs curricula', () => {
  for (const settingId of ['warsh', 'qalun', 'duri']) {
    const entry = registry.settings.find((item) => item.settingIds.includes(settingId));
    assert.ok(entry);
    assert.equal(entry.status, 'BLOCKED_NO_APPROVED_CORPUS');
    assert.deepEqual(entry.curricula, []);
    assert.match(entry.blockedReasonAr, /حفص/);
    assert.ok(entry.unresolvedFields.includes('tariq'));
    assert.ok(entry.unresolvedFields.includes('wajh'));
    assert.ok(entry.unresolvedFields.includes('qualified-review'));
  }
});

test('registry fingerprints bind text assets and the isolated Hafs draft', () => {
  for (const entry of registry.settings) {
    assert.equal(entry.textEdition.sha256, sha256(entry.textEdition.asset));
  }
  const hafs = registry.settings.find((item) => item.riwayah.id === 'hafs-an-asim');
  assert.equal(hafs.curricula.length, 1);
  const pointer = hafs.curricula[0];
  assert.equal(pointer.sha256, sha256(pointer.artifact));
  assert.equal(pointer.status, 'PENDING_SCHOLARLY_REVIEW');
  assert.equal(pointer.publishableAsApproved, false);
  assert.deepEqual(pointer.scope, catalog.curricula[0].scope);
});

test('curriculum schema keeps source, annotation and two-person review gates', () => {
  assert.equal(schema.additionalProperties, false);
  assert.ok(schema.required.includes('scope'));
  assert.ok(schema.required.includes('sources'));
  assert.ok(schema.required.includes('annotations'));
  assert.ok(schema.required.includes('review'));
  assert.equal(schema.properties.annotations.minItems, 1);
  assert.ok(schema.properties.textBinding.required.includes('sha256'));
  assert.ok(schema.properties.textBinding.required.includes('dataset'));
  assert.deepEqual(schema.allOf[0].else.properties.review.properties.status.enum,
    ['NOT_REVIEWED', 'CHANGES_REQUESTED']);
  const serialized = JSON.stringify(schema);
  for (const marker of ['reviewerQualification', 'reviewedSha256', 'releaseApprover']) {
    assert.ok(serialized.includes(marker));
  }
});

test('Python scope verifier passes the repository and rejects a weakened fallback policy', () => {
  const good = spawnSync('python3', ['scripts/verify_tajweed_scopes.py'], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(good.status, 0, good.stderr || good.stdout);
  assert.match(good.stdout, /cross-scope fallback: forbidden/);

  const negativeProgram = String.raw`
import copy, importlib.util
from pathlib import Path
root = Path.cwd()
spec = importlib.util.spec_from_file_location('gate', root / 'scripts/verify_tajweed_scopes.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
registry = gate.load_json(gate.REGISTRY_PATH)
catalog = gate.load_json(gate.CATALOG_PATH)
registry = copy.deepcopy(registry)
registry['fallbackPolicy'] = 'ALLOW_HAFS_FALLBACK'
try:
    gate.verify_registry(registry, catalog)
except gate.VerificationError:
    raise SystemExit(0)
raise SystemExit('weakened fallback policy was accepted')
`;
  const bad = spawnSync('python3', ['-c', negativeProgram], {
    cwd: ROOT,
    encoding: 'utf8',
  });
  assert.equal(bad.status, 0, bad.stderr || bad.stdout);
});

test('runtime requires an exact registry pointer before exposing a curriculum', () => {
  const app = fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8');
  assert.match(app, /FORBIDDEN_BETWEEN_SCOPES/);
  assert.match(app, /sameTajweedScope\(item\.scope, candidate\.scope\)/);
  assert.match(app, /item\.status === candidate\.status/);
  assert.match(app, /item\.publishableAsApproved === candidate\.publishableAsApproved/);
  assert.match(app, /لا تُعرض أحكام حفص أو أي طبقة عامة/);
});
