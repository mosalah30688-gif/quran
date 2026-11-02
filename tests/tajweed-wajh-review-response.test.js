const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const root = path.join(__dirname, '..');
const auditDir = path.join(root, 'audit', 'sources', 'tajweed-riwayat', '2026-11-02');
const packet = JSON.parse(fs.readFileSync(path.join(auditDir, 'WAJH_REVIEW_PACKET.json'), 'utf8'));
const schema = JSON.parse(fs.readFileSync(path.join(auditDir, 'WAJH_REVIEW_RESPONSE.schema.json'), 'utf8'));
const template = JSON.parse(fs.readFileSync(path.join(auditDir, 'WAJH_REVIEW_RESPONSE_TEMPLATE.json'), 'utf8'));

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
}

function reviewedScopeHash(scope) {
  const payload = clone(scope);
  payload.responseStatus = 'SUBMITTED_FOR_SECOND_APPROVAL';
  delete payload.secondPersonApproval;
  return crypto.createHash('sha256').update(canonicalJson(payload), 'utf8').digest('hex');
}

function runVerifier(args = []) {
  return spawnSync(
    'python3',
    ['scripts/verify_tajweed_wajh_review_response.py', ...args],
    { cwd: root, encoding: 'utf8', maxBuffer: 4 * 1024 * 1024 },
  );
}

function withTempResponse(response, callback) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'siraj-wajh-response-'));
  try {
    const responsePath = path.join(tempDir, 'review-response.json');
    fs.writeFileSync(responsePath, `${JSON.stringify(response, null, 2)}\n`);
    return callback(responsePath);
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function buildCompleteStructuralFixture() {
  const response = clone(template);
  response.responseId = 'test-only-structural-review-response';
  response.updatedAt = '2026-11-02';
  response.status = 'SCIENTIFIC_REVIEW_COMPLETE';

  for (const scope of response.scopeResponses) {
    scope.responseStatus = 'SCIENTIFICALLY_APPROVED';
    scope.reviewer = {
      name: `مراجع اختباري ${scope.settingId}`,
      qualification: 'بيانات اختبار بنيوي وليست اعتمادًا علميًا',
      qualificationEvidenceLocator: `test://${scope.settingId}/qualification`,
      exactRouteExperience: 'خبرة اختبارية وهمية لا تستخدم للنشر',
      organization: 'جهة اختبارية',
      reviewStartedAt: '2026-10-30',
      reviewCompletedAt: '2026-11-01',
      evidenceLocator: `test://${scope.settingId}/review-evidence`,
      evidenceSha256: 'a'.repeat(64),
      attestationFullReviewNotSampling: true,
      attestationExactRoute: true,
      attestationNoCrossScopeInference: true,
    };
    for (const decision of scope.decisionResponses) {
      decision.status = 'APPROVED';
      decision.selectedPracticeId = `test-${decision.topicId}`;
      decision.selectedPracticeLabelAr = 'اختيار اختباري بنيوي غير صالح للنشر';
      decision.sourceLocator = `test://${scope.settingId}/${decision.topicId}`;
      decision.reviewerNoteAr = null;
    }
    scope.selectedProfile = {
      status: 'APPROVED_BY_REVIEWER',
      wajhId: `test-${scope.settingId}-wajh`,
      wajhLabelAr: 'وجه اختباري بنيوي غير صالح للنشر',
      editionId: scope.candidateEdition,
      editionSha256: 'b'.repeat(64),
      editionEvidenceLocator: `test://${scope.settingId}/edition`,
      countTraditionId: `test-${scope.settingId}-count`,
      totalAyahs: 6214,
      surahCountTableSha256: 'c'.repeat(64),
      compatibilityAttestationAr: 'إقرار اختباري بنيوي بالتوافق، وليس حكمًا علميًا.',
    };
    scope.secondPersonApproval = {
      status: 'APPROVED',
      approverName: `معتمد اختباري مستقل ${scope.settingId}`,
      approverQualification: 'بيانات اختبار بنيوي وليست اعتمادًا علميًا',
      approvalDate: '2026-11-02',
      reviewedScopePayloadSha256: reviewedScopeHash(scope),
      evidenceLocator: `test://${scope.settingId}/second-approval`,
      evidenceSha256: 'd'.repeat(64),
    };
  }
  return response;
}

test('response schema is bound to the exact blank decision packet', () => {
  const packetHash = crypto.createHash('sha256')
    .update(fs.readFileSync(path.join(auditDir, 'WAJH_REVIEW_PACKET.json')))
    .digest('hex');
  assert.equal(schema.properties.packetBinding.properties.packetId.const, packet.packetId);
  assert.equal(schema.properties.packetBinding.properties.packetSha256.const, packetHash);
  assert.equal(template.packetBinding.packetId, packet.packetId);
  assert.equal(template.packetBinding.packetSha256, packetHash);
});

test('blank response covers every decision while selecting nothing', () => {
  assert.equal(template.status, 'DRAFT');
  assert.equal(template.publishableAsApproved, false);
  assert.equal(template.runtimeActivationRequested, false);
  assert.equal(template.scholarlyAccuracyDeterminedBySoftware, false);
  assert.deepEqual(template.scopeResponses.map((scope) => scope.settingId), ['warsh', 'qalun', 'duri']);

  for (const packetScope of packet.scopes) {
    const responseScope = template.scopeResponses.find((scope) => scope.settingId === packetScope.settingId);
    assert.ok(responseScope);
    assert.deepEqual(
      responseScope.decisionResponses.map((decision) => decision.decisionId),
      packetScope.decisionItems.map((decision) => decision.decisionId),
    );
    assert.equal(responseScope.responseStatus, 'PENDING');
    assert.equal(responseScope.reviewer.name, null);
    assert.equal(responseScope.selectedProfile.wajhId, null);
    assert.equal(responseScope.secondPersonApproval.approverName, null);
    for (const decision of responseScope.decisionResponses) {
      assert.equal(decision.status, 'PENDING');
      assert.equal(decision.selectedPracticeId, null);
    }
  }
});

test('verifier accepts a partially filled in-progress response without promoting it', () => {
  const response = clone(template);
  response.updatedAt = '2026-11-02';
  response.status = 'IN_PROGRESS';
  const warsh = response.scopeResponses[0];
  warsh.responseStatus = 'IN_PROGRESS';
  warsh.reviewer.name = 'مراجع قيد التعيين';
  warsh.reviewer.qualification = 'بيانات أولية غير مكتملة';
  const decision = warsh.decisionResponses[0];
  decision.status = 'APPROVED';
  decision.selectedPracticeId = 'reviewer-recorded-practice';
  decision.selectedPracticeLabelAr = 'اختيار سجله المراجع';
  decision.sourceLocator = 'المرجع الأساسي، الصفحة المثبتة في الحزمة';

  withTempResponse(response, (responsePath) => {
    const result = runVerifier(['--response', responsePath]);
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.match(result.stdout, /publishable as approved: no/);
  });
});

test('complete synthetic fixture proves the two-person transition structurally', () => {
  const response = buildCompleteStructuralFixture();
  withTempResponse(response, (responsePath) => {
    const result = runVerifier(['--response', responsePath, '--print-review-hashes']);
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.match(result.stdout, /scholarly accuracy determined by software: no/);
    assert.match(result.stdout, /warsh: [0-9a-f]{64}/);
    assert.match(result.stdout, /qalun: [0-9a-f]{64}/);
    assert.match(result.stdout, /duri: [0-9a-f]{64}/);
  });
});

test('second approver cannot be the original reviewer', () => {
  const response = buildCompleteStructuralFixture();
  const warsh = response.scopeResponses[0];
  warsh.secondPersonApproval.approverName = warsh.reviewer.name;
  warsh.secondPersonApproval.reviewedScopePayloadSha256 = reviewedScopeHash(warsh);

  withTempResponse(response, (responsePath) => {
    const result = runVerifier(['--response', responsePath]);
    assert.notEqual(result.status, 0, 'same-person approval unexpectedly passed');
    assert.match(result.stderr, /must be independent/);
  });
});

test('Duri 6218 regression cannot be recorded as the reviewed count', () => {
  const response = buildCompleteStructuralFixture();
  const duri = response.scopeResponses.find((scope) => scope.settingId === 'duri');
  duri.selectedProfile.totalAyahs = 6218;
  duri.secondPersonApproval.reviewedScopePayloadSha256 = reviewedScopeHash(duri);

  withTempResponse(response, (responsePath) => {
    const result = runVerifier(['--response', responsePath]);
    assert.notEqual(result.status, 0, 'Duri 6218 unexpectedly passed');
    assert.match(result.stderr, /6214 or 6217; 6218 is rejected/);
  });
});

test('packet hash tampering and premature approval fail closed', () => {
  const badHash = clone(template);
  badHash.packetBinding.packetSha256 = '0'.repeat(64);
  withTempResponse(badHash, (responsePath) => {
    const result = runVerifier(['--response', responsePath]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /packetSha256 does not match/);
  });

  const premature = clone(template);
  premature.updatedAt = '2026-11-02';
  premature.status = 'IN_PROGRESS';
  premature.scopeResponses[0].responseStatus = 'SCIENTIFICALLY_APPROVED';
  withTempResponse(premature, (responsePath) => {
    const result = runVerifier(['--response', responsePath]);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /is required|requires every decision approved/);
  });
});

test('committed response verifier and guide retain the structural-only warning', () => {
  const result = runVerifier();
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const guide = fs.readFileSync(path.join(auditDir, 'WAJH_REVIEW_GUIDE.ar.md'), 'utf8');
  assert.match(guide, /التحقق البنيوي لا يثبت صحة الاختيار علميًا/);
  assert.match(guide, /SUBMITTED_FOR_SECOND_APPROVAL/);
  assert.match(guide, /reviewedScopePayloadSha256/);
});
