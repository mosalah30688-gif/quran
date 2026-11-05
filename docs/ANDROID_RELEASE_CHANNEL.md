# قناة تحديث Android — كيف تعمل وكيف تُنشر نسخة جديدة

آخر تحديث لهذا الملف: 2026-11-05 — بعد تشخيص تعطّل نشر Android 1.4.4/1.4.5/1.4.6.

## الحقيقة الواحدة (مصدر الحقيقة)

ترتيب البناء في GitHub Actions هو:

```
index.html + app.js + smart-*.js + tajweed-*.js + quran-*.json   ← المصدر في جذر المستودع
        │  scripts/build-www.sh  (يمسح www/ ويعيد بناءها من الجذر)
        ▼
      www/            ← ما يُغلَّف داخل APK (assets/public)
        │
        ▼
   APK موقّع  ←  GitHub Release (immutable)  ←  update/manifest.json (قناة التحديث داخل التطبيق)
```

القاعدة الذهبية: **لا تُعدَّل ملفات `www/` أو `update/` يدويًا.** أي تعديل يُكتب في الجذر فقط:

```bash
# 1) عدّل في الجذر: index.html, app.js, sw.js, quran-*.json ...
# 2) أعد بناء الحزمة وقناة الواجهة
bash scripts/build-www.sh
bash scripts/publish-update.sh <الإصدار> "ميزة أولى" "ميزة ثانية"
# 3) ارفع الإصدار في ثلاثة أماكن (الملف scripts/verify_release_channel.py يمنع أي تفاوت بينها)
#    package.json  +  android/app/build.gradle  +  index.html (APP_BUNDLE_VERSION و«الإصدار x.y.z»)
```

`versionCode` يتبع القاعدة `major*100 + minor*10 + patch`، أي `1.4.7 → 147`.

## لماذا لم تصل تحديثاتك إلى 1.4.4؟ (تشخيص 2026-11-05)

1. **بناء CI كان يفشل دائمًا**: خطوة `npm run android:sync` كانت تنفّذ `cp quran-madani-lines.json`
   والملف غير موجود في الجذر (كان في `www/` و`update/` فقط) ⇒
   `cp: cannot stat 'quran-madani-lines.json'` ⇒ لا APK جديد منذ 2026-11-05 21:13.
2. **قناة الواجهة (1.4.5) لا تصلح للنسخة المثبَّتة 1.4.4**: التطبيق 1.4.4 يحمل محدِّثًا قديمًا
   يخزّن كل ملفات التحديث في مفتاح `localStorage` واحد، وكانت القناة تنشر ‎3.49 م.ب‎ من البيانات
   (quran-hafs.json وحده ‎2.82 م.ب‎ ⇒ ‎5.6 م.ب‎ بترميز UTF‑16) ⇒ تجاوز الحصة ⇒ رسالة
   «تعذّر التحديث» بلا سبب ظاهر. المحدِّث الجديد (IndexedDB + بصمات SHA‑256) موجود فقط في الواجهة الجديدة.
3. **مسار «نسخة APK كاملة» كان مسدودًا**: آخر تعديل أعاد `manifest.apk.version` إلى `1.4.4`
   (أي مساوٍ للمثبَّت ⇒ لا يُعرض تحديث)، والإصدار `siraj-android-v1.4.6` كان يحتوي فعليًا على
   APK بـ `versionName 1.3.1` وواجهة `1.2.0`، و`siraj-android-v1.4.6-full` كان نسخة بايت‑ببايت من APK 1.4.4.
4. **أحدث واجهة كانت في `www/` وحدها**: الفرق بين الجذر و`www` كان 14 ك.ب في `app.js`
   (خطوط المدينة، التحديد الحر، معلومات شاشة القفل، حذف حزمة التفاسير المحلية من الإعدادات).
   أي بناء من الجذر كان سيمحو هذه الإضافات.

## نص القرآن المعتمد

`quran-hafs.json` هو **نص عرض نظيف** بقرار موثّق: بلا علامات وقف، وبلا علامة حزب `۞`، وبلا علامة
سجدة `۩`. البصمة المقفولة في `audit/sources/alquran-cloud/2026-10-28/SOURCE.json`
(`display_normalization`) والتوثيق في `audit/DATA_PROVENANCE.md`.
لا تُعِد هذه العلامات، ولا تُعدّل الملف يدويًا؛ أي تغيير يحتاج إصدارًا جديدًا وبصمة جديدة.

## النشر (workflow: Build Android Release)

النشر لا يتم تلقائيًا بالدفع؛ يحتاج تشغيلًا يدويًا:

* `publish` = `true`
* `confirmation` = `PUBLISH IMMUTABLE siraj-android-v<الإصدار>` (مثال: `PUBLISH IMMUTABLE siraj-android-v1.4.7`)
* `features` = من 1 إلى 5 ميزات للمستخدم مفصولة بـ `|`، **ويجب أن تختلف نصًا** عن الميزات
  المسجّلة حاليًا في `update/manifest.json` وإلا أوقف `publish-update.sh` النشر.

خطوات الـ workflow تفرض: بناء موقّع بنفس شهادة `update/app.apk`، `versionCode` أكبر منها،
وسم إصدار جديد غير موجود، إصدار GitHub **immutable**، ثم تحديث `update/manifest.json`
بمؤشر APK الجديد (الرابط + SHA‑256) حتى يُعرض التحديث على النسخ المثبَّتة.

## حرّاس لا تُحذف

| الحارس | ما يمنعه |
|---|---|
| `scripts/verify_release_channel.py` | تفاوت الإصدار بين package.json/gradle/index.html/القناة، انحراف `update/` عن الجذر، بصمات خاطئة، رابط APK لا يطابق رقم إصداره |
| `scripts/verify_android_bundle.py` | نقص ملفات الحزمة، انحراف نصوص القرآن، تعارض النسخ بين التطبيقات |
| `scripts/verify_tajweed_scopes.py` | عرض طبعة مصحف غير مسجّلة بنطاق تجويد مستقل (fail-closed) |
| `tests/smart-ui.test.js` | فقدان محرّكات الذكاء والتجويد أو أوضاع القناة |
