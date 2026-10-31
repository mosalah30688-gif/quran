# المساهمة في سراج | Contributing to Siraj

## العربية

نشكر اهتمامك بتحسين **سراج — قرآن كريم**. المشروع مملوك، وتُدار المساهمات بما يحافظ على سلامة النصوص وحقوق المصادر وسلسلة إصدار قابلة للتدقيق.

### ما الذي يمكن تقديمه؟

- بلاغ خلل واضح بخطوات إعادة الإنتاج والمنصة والإصدار.
- اقتراح تجربة استخدام يراعي العربية وRTL وإتاحة الاستخدام.
- إصلاح محدود ومختبر.
- تحسين توثيق أو اختبار أو تحقق من مصدر.
- بلاغ أمني خاص وفق [`SECURITY.md`](SECURITY.md).

لا تضع نصًا قرآنيًا أو تفسيرًا أو ترجمة أو تسجيلًا أو خطًا أو صورة أو بيانات من مصدر خارجي دون توثيق المصدر والإصدار والرخصة والإسناد المطلوب.

### قبل فتح Pull Request

1. افتح Issue يصف المشكلة أو المقترح، ما لم يكن التغيير تصحيحًا صغيرًا واضحًا.
2. أنشئ فرعًا محدود النطاق، ولا تجمع تغييرات غير مترابطة.
3. حافظ على استقلال أرقام Android وWindows وLinux.
4. لا تضع أسرارًا أو مفاتيح توقيع أو رموز وصول أو حزم بناء مولدة.
5. أضف الاختبارات المناسبة وشغّل فحوص المنصة.
6. اشرح أثر التغيير على المحتوى والحقوق والخصوصية والتحديث.
7. وافق صراحةً على [`CLA.md`](CLA.md) داخل Pull Request.

### عبارة CLA الإلزامية

أضف العبارة التالية دون تعديل:

> قرأت اتفاقية المساهم في سراج، الإصدار 1.0، وأوافق عليها، ولدي الصلاحية لتقديم هذه المساهمة.

لن تُدمج مساهمة برمجية قبل تسجيل هذه الموافقة والتحقق من حق مقدمها في المواد المرسلة.

### فحوص أساسية

```bash
npm ci
node --check app.js
python scripts/verify_android_bundle.py
python scripts/verify_audio_sources.py
python scripts/verify_asset_provenance.py
python scripts/verify_data_provenance.py
python -m unittest discover -s windows_app/tests -p 'test_*.py' -v
python -m unittest discover -s mushaf_app/tests -p 'test_*.py' -v
```

قد تحتاج اختبارات الواجهة وقاعدة التفاسير المقفلة إلى متطلبات منصة إضافية. GitHub Actions هو المرجع النهائي لبناء Windows وLinux.

### قواعد المحتوى

- لا تغيير لنص أو ترقيم أو رسم أو بيانات رواية بلا مصدر مقفول وبصمة ومراجعة مناسبة.
- لا إضافة لتفسير حديث أو غامض الحقوق.
- لا تقليل لقائمة التلاوات المعتمدة دون قرار صريح موثق.
- التحقق الآلي لا يُقدّم بوصفه اعتمادًا علميًا بشريًا.
- لا يُعدل Release منشور؛ يُنشأ إصدار جديد وفق بوابة الإصدار.

### أسلوب المراجعة

قد يطلب المشرف فصل التغيير أو إضافة اختبار أو إثبات منشأ أو توضيح ترخيص. قبول Issue أو مراجعة Pull Request لا يعد وعدًا بالدمج أو بموعد إصدار.

---

## English

Thank you for helping improve **Siraj — Quran Kareem**. Siraj is proprietary, and contributions are managed to protect textual integrity, source rights, and an auditable release chain.

### Welcome contributions

- Reproducible bug reports with platform and version details.
- UX proposals that respect Arabic, RTL, and accessibility.
- Focused, tested fixes.
- Documentation, test, and provenance improvements.
- Private security reports under [`SECURITY.md`](SECURITY.md).

Do not submit Quran text, exegesis, translations, recordings, fonts, images, or external data without the exact source, version, license, and required attribution.

### Before opening a pull request

1. Open an Issue first unless the correction is small and self-evident.
2. Keep the branch and pull request narrowly scoped.
3. Preserve independent Android, Windows, and Linux versioning.
4. Never commit secrets, signing keys, access tokens, or generated packages.
5. Add relevant tests and run the platform checks.
6. Describe effects on content, rights, privacy, and updating.
7. Explicitly accept [`CLA.md`](CLA.md) in the pull request.

### Required CLA statement

Include this exact statement:

> I have read and agree to the Siraj Contributor License Agreement version 1.0, and I am authorized to submit this contribution.

No code contribution is merged until this acceptance and the contributor’s authority to submit the material have been recorded.

### Core checks

Use the commands listed in the Arabic section above. UI tests and the locked offline-tafsir store may require additional platform dependencies; GitHub Actions is authoritative for Windows and Linux packaging.

### Content rules

- Do not alter Quran text, numbering, orthography, or recitation-variant data without a locked source, hashes, and appropriate review.
- Do not add modern or rights-uncertain exegesis.
- Do not reduce the approved reciter set without an explicit recorded decision.
- Do not describe automated verification as human scholarly certification.
- Never modify a published Release; publish a new version through the release gate.

Review may require a smaller change, more tests, provenance evidence, or licensing clarification. Review does not guarantee acceptance or a release date.
