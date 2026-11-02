const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const root = path.join(__dirname, '..');
const auditDir = path.join(root, 'audit', 'sources', 'tajweed-riwayat', '2026-11-02');
const packetPath = path.join(auditDir, 'WAJH_REVIEW_PACKET.json');
const guidePath = path.join(auditDir, 'WAJH_REVIEW_GUIDE.ar.md');
const packet = JSON.parse(fs.readFileSync(packetPath, 'utf8'));

function bySetting(settingId) {
  const scope = packet.scopes.find((item) => item.settingId === settingId);
  assert.ok(scope, `missing scope ${settingId}`);
  return scope;
}

function runVerifier(args = []) {
  return spawnSync(
    'python3',
    ['scripts/verify_tajweed_wajh_review_packet.py', ...args],
    { cwd: root, encoding: 'utf8', maxBuffer: 4 * 1024 * 1024 },
  );
}

test('wajh packet covers every inventoried topic exactly once', () => {
  const inventory = JSON.parse(fs.readFileSync(path.join(auditDir, 'RULE_INVENTORY.json'), 'utf8'));
  assert.deepEqual(packet.scopes.map((item) => item.settingId), ['warsh', 'qalun', 'duri']);

  for (const inventoryScope of inventory.scopes) {
    const scope = bySetting(inventoryScope.settingId);
    const expected = inventoryScope.topics.map((topic) => topic.topicId);
    const actual = scope.decisionItems.map((item) => item.topicId);
    assert.deepEqual(actual, expected);
    assert.equal(new Set(actual).size, expected.length);
  }
  assert.equal(bySetting('warsh').decisionItems.length, 17);
  assert.equal(bySetting('qalun').decisionItems.length, 14);
  assert.equal(bySetting('duri').decisionItems.length, 12);
});

test('all scholarly choices, assignments, and approvals remain blank and blocked', () => {
  assert.equal(packet.status, 'AWAITING_QUALIFIED_REVIEWER');
  assert.equal(packet.publishableAsApproved, false);
  assert.equal(packet.releaseGate.status, 'BLOCKED');
  assert.equal(packet.releaseGate.runtimeChanges, 0);
  assert.equal(packet.releaseGate.approvedCurricula, 0);
  assert.equal(packet.reviewContract.machineMaySelectOrApprove, false);
  assert.equal(packet.reviewContract.runtimeActivationAllowed, false);

  for (const scope of packet.scopes) {
    assert.equal(scope.wajhStatus, 'NOT_SELECTED');
    assert.equal(scope.reviewAssignment.status, 'NOT_ASSIGNED');
    assert.equal(scope.reviewAssignment.reviewerName, null);
    assert.equal(scope.finalDecision.status, 'PENDING');
    assert.equal(scope.finalDecision.selectedWajhId, null);
    assert.equal(scope.finalDecision.selectedEditionId, null);
    assert.equal(scope.finalDecision.selectedEditionSha256, null);
    assert.equal(scope.finalDecision.selectedCountTraditionId, null);
    assert.equal(scope.finalDecision.selectedTotalAyahs, null);
    assert.equal(scope.finalDecision.selectedSurahCountTableSha256, null);
    assert.equal(scope.finalDecision.reviewEvidenceSha256, null);
    assert.equal(scope.secondPersonReleaseApproval.status, 'NOT_STARTED');
    assert.equal(scope.publishableAsApproved, false);
    for (const decision of scope.decisionItems) {
      assert.equal(decision.status, 'PENDING');
      assert.equal(decision.selectedPracticeId, null);
      assert.equal(decision.reviewerSourceLocator, null);
    }
  }
});

test('Duri count conflict, 67:9 regression, and riwayah separation are independent blockers', () => {
  const duri = bySetting('duri');
  assert.equal(duri.textBindingCandidate.status, 'REJECTED_AS_OFFSET_AUTHORITY_KNOWN_67_9_SPLIT');
  assert.equal(
    duri.countAudit.status,
    'QUARANTINED_PUBLISHER_OR_QUALIFIED_SCHOLAR_CLARIFICATION_REQUIRED',
  );
  assert.deepEqual(duri.countAudit.observedTotals, [6214, 6217, 6218]);
  assert.equal(duri.countAudit.automaticRepairAllowed, false);

  const gates = new Map(duri.specialGates.map((gate) => [gate.gateId, gate]));
  assert.equal(gates.get('duri-count-tradition').status, 'BLOCKED_EXTERNAL_CLARIFICATION');
  assert.equal(gates.get('duri-quranpedia-67-9-regression').status, 'BLOCKED_SOURCE_CORRECTION_OR_REPLACEMENT');
  assert.equal(gates.get('duri-large-idgham-separation').status, 'PENDING_QUALIFIED_REVIEW');
  assert.equal(gates.get('duri-rule-and-derived-data-rights').status, 'BLOCKED_NO_REDISTRIBUTION_GRANT');
});

test('packet remains metadata-only and outside runtime assets', () => {
  assert.equal(packet.containsQuranText, false);
  assert.equal(packet.containsCopiedRuleProse, false);
  assert.equal(packet.containsTrainingExamples, false);
  assert.equal(packet.containsAnnotationSpans, false);

  const forbiddenKeys = new Set([
    'text', 'quranText', 'ruleText', 'example', 'examples', 'ayah', 'ayahs',
    'annotations', 'spans', 'ruleProse',
  ]);
  const queue = [packet];
  while (queue.length) {
    const value = queue.pop();
    if (Array.isArray(value)) {
      queue.push(...value);
    } else if (value && typeof value === 'object') {
      for (const [key, child] of Object.entries(value)) {
        assert.equal(forbiddenKeys.has(key), false, `forbidden payload key: ${key}`);
        queue.push(child);
      }
    }
  }

  for (const relative of ['www', 'update', 'windows_app/data', 'mushaf_app/data', 'tajweed-curricula']) {
    const directory = path.join(root, relative);
    if (!fs.existsSync(directory)) continue;
    const stack = [directory];
    while (stack.length) {
      const current = stack.pop();
      for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
        const fullPath = path.join(current, entry.name);
        if (entry.isDirectory()) stack.push(fullPath);
        else assert.equal(entry.name.toLowerCase().includes('wajh-review'), false, fullPath);
      }
    }
  }
});

test('Arabic reviewer guide requires exact-route credentials and second approval', () => {
  const guide = fs.readFileSync(guidePath, 'utf8');
  for (const marker of [
    'مراجعة كاملة لا بالعينة',
    'ورش عن نافع — طريق الأزرق من الشاطبية',
    'قالون عن نافع — طريق أبي نشيط من الشاطبية',
    'الدوري عن أبي عمرو — طريق أبي الزعراء من الشاطبية',
    'المؤهل العلمي',
    'معرّف الوجه المختار',
    'بصمة دليل المراجعة',
    'اعتماد شخص ثانٍ مستقل',
  ]) {
    assert.match(guide, new RegExp(marker));
  }
});

test('deterministic verifier accepts committed packet and rejects a machine-filled choice', () => {
  const valid = runVerifier();
  assert.equal(valid.status, 0, valid.stderr || valid.stdout);

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'siraj-wajh-packet-'));
  try {
    const tampered = JSON.parse(JSON.stringify(packet));
    tampered.scopes[0].decisionItems[0].selectedPracticeId = 'machine-guessed-choice';
    const tamperedPath = path.join(tempDir, 'WAJH_REVIEW_PACKET.json');
    fs.writeFileSync(tamperedPath, `${JSON.stringify(tampered, null, 2)}\n`);
    const invalid = runVerifier(['--packet', tamperedPath]);
    assert.notEqual(invalid.status, 0, 'tampered packet unexpectedly passed');
    assert.match(invalid.stderr, /review packet drift/);
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});
