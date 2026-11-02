'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const BASE = [
  'index.html', 'smart-context.js', 'smart-services.js', 'tajweed-learning.js',
  'tajweed-curriculum-loader.js', 'tajweed-learning-catalog.json',
  'tajweed-scope-registry.json', 'app.js',
];
const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function makeFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'siraj-update-overlay-'));
  fs.mkdirSync(path.join(root, 'scripts'), { recursive: true });
  fs.mkdirSync(path.join(root, 'tajweed-curricula'), { recursive: true });
  fs.mkdirSync(path.join(root, 'update', 'tajweed-curricula'), { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'scripts/publish-update.sh'), path.join(root, 'scripts/publish-update.sh'));
  for (const name of BASE) fs.copyFileSync(path.join(ROOT, name), path.join(root, name));
  fs.writeFileSync(path.join(root, 'quran-riwayat.json'), '{"riwayat":{"warsh":[]}}\n');
  fs.writeFileSync(path.join(root, 'tajweed-curricula/test-package.json'),
    '{"textBinding":{"asset":"quran-riwayat.json"}}\n');
  fs.writeFileSync(path.join(root, 'update/manifest.json'),
    '{"desktop":{"preserve":true},"features":["ميزة مستخدم"]}\n');
  fs.writeFileSync(path.join(root, 'update/tajweed-curricula/stale.json'), '{}\n');
  return root;
}

test('update publisher locks shell, curricula, and their bound text assets', () => {
  const root = makeFixture();
  try {
    const result = spawnSync('bash', ['scripts/publish-update.sh', '9.8.7'], {
      cwd: root,
      encoding: 'utf8',
    });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    const manifest = JSON.parse(fs.readFileSync(path.join(root, 'update/manifest.json'), 'utf8'));
    assert.equal(manifest.version, '9.8.7');
    assert.deepEqual(manifest.desktop, { preserve: true });
    assert.deepEqual(manifest.features, ['ميزة مستخدم']);
    assert.ok(manifest.files.includes('tajweed-curricula/test-package.json'));
    assert.ok(manifest.files.includes('quran-riwayat.json'));
    assert.equal(fs.existsSync(path.join(root, 'update/tajweed-curricula/stale.json')), false);
    assert.deepEqual(Object.keys(manifest.sha256).sort(), [...manifest.files].sort());
    for (const name of manifest.files) {
      assert.equal(manifest.sha256[name], sha256(path.join(root, 'update', name)), name);
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('update publisher rejects a non-semantic version before touching the channel', () => {
  const root = makeFixture();
  try {
    const before = fs.readFileSync(path.join(root, 'update/manifest.json'), 'utf8');
    const result = spawnSync('bash', ['scripts/publish-update.sh', 'latest'], {
      cwd: root,
      encoding: 'utf8',
    });
    assert.notEqual(result.status, 0);
    assert.equal(fs.readFileSync(path.join(root, 'update/manifest.json'), 'utf8'), before);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
