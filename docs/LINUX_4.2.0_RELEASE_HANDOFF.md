# تسليم ترقيع لينكس الموحّد 4.2.0

**الحالة:** الكود والاختبارات والبيانات جاهزة ومُثبَّتة محليًا. الناقص خطوتان فقط:
رفع الـcommit (لا يوجد remote أو بيانات دخول في هذه المساحة)، ثم اعتماد البوابة.

- **HEAD:** `c86f2f4f46f489341c4a6bdbaef2c15644562e90`
- **الترقيعان المحليان:** `9f0ce2c` (الترقيع الكامل) ثم `c86f2f4` (وضوح حلقة الورد).
- **الإصدار:** `mushaf_app/version.py` = `4.2.0`، وخمس ميزات في `UPDATE_FEATURES`.
- **الوسم المطلوب:** `siraj-linux-patch-v4.2.0` (شرط السير: `Version(4.2.0) > 4.1.1` ✔).

## ما نُقل في هذا الترقيع

| التبويب/الشاشة | الملفات | الاختبارات |
|---|---|---|
| مواقيت الصلاة + القبلة + هجري أم القرى | `mushaf_app/prayer_times.py`, `data/prayer-cities.json`, `data/hijri-ummalqura.json`, `QiblaDial` في `main.py` | `tests/test_prayer_times.py` (١١) |
| الأذان والتذكير قبل الأذان | `mushaf_app/adhan_scheduler.py`, `AdhanWindow`, `run_adhan_reminder`, `data/adhan-catalog.json` | `tests/test_adhan_scheduler.py` (١١) |
| حلقة الورد + ١٠ شارات + دقائق القراءة | `reading_tracker.py` (دوال جديدة), `main.py` | فحوص UI |
| نقر الآية يشغّل التلاوة + توحيد بطاقة التحميل | `main.py` (`play_from_ayah`, `start_dl`, `update_dl_estimate`) | فحوص UI |
| إصلاح مسار البيانات | `scripts/generate_alquran_data.py`, `scripts/generate_quranpedia_tafsir_catalog.py`, `scripts/build_offline_tafsir.py`, `scripts/generate_hijri_table.py`, `audit/sources/project-authored-data.json`, `audit/sources/quranpedia-tafsir/2026-10-28/SOURCE.json` | فحوص البيانات الخمسة |

## نتائج الفحص المحلي

```
verify_data_provenance      → Verified provenance for 30 bundled JSON files
verify_asset_provenance     → Verified owner provenance and hashes for 34 icon assets
generate_alquran_data       → Verified 4 generated files from 4 locked editions
generate_quranpedia_data    → ok
generate_quranpedia_tafsir_catalog → Verified 73 licensed classical Quranpedia tafsir books
generate_adhkar_data        → ok
audit_alquran_editions      → ok
generate_hijri_table        → Verified Umm al-Qura table 1400-1500 AH for both desktop apps
verify_android_bundle       → 6,236 Hafs/tajweed rows, 604 pages, 80 licensed tafsirs, four fonts
verify_audio_sources        → 17 desktop Hafs reciters + five MP3Quran riwayat sources
unittest discover           → 82 tests OK (skipped=1)
ui_test                     → كل الفحوص OK ما عدا إخفاقين قديمين بسبب غياب
                              tafsir-offline.sqlite3 محليًا (ينزّلها CI قبل الفحص)
```

## ملاحظات لازمة قبل النشر

1. **حل مسار `hafs.json`:** كان سكربتان يكتبان نفس الملف. النص المحزوم هو نص
   `build_hafs_text.py` (مصحف المدينة من Quranpedia)؛ فأُخرج `hafs.json` من
   `generate_alquran_data.py` وبقي مالكه واحدًا. **لم يتغيّر حرف من نص المصحف.**
2. **كتالوج التفسير ٧٣ لا ٧٥:** التفسيران المعاصران `qp:70` و`qp:321` ليسا في
   المخزن النصي المقفول (بُني قبلهما)، فلا يُعرض كتاب بلا نص. الاستثناء مكتوب
   صراحة في السكربت (`DESKTOP_PENDING_STORE_IDS`)، ويعود ٧٥ عند إعادة بناء المخزن.
3. **تذكير ما قبل الأذان** إشعار نظام يذكر الصلاة والدقائق (لا يوجد نطق صوتي في
   سطح المكتب بلا محرك نطق، والإشعار يقوم بالمطلوب).
4. **الأذان يعمل والتطبيق مغلق** عبر مؤقتات `systemd --user` مع
   `Persistent=true`، ونافذة `--adhan <الصلاة>` تنزل الصوت عند أول مرة ثم
   تستعمله من الكاش.

## خطوات النشر بعد الاعتماد

```bash
# 1) رفع العمل (يحتاج remote + بيانات دخول سليمة؛ التوكن القديم ظاهر ويجب تدويره)
git remote add origin https://github.com/mosalah30688-gif/quran.git
git push origin main

# 2) اعتماد البوابة بالـcommit النهائي بعد الدفع (لا يُزوَّر)
#    اكتب في audit/RELEASE_GATE.json:
#    approved_commit = <sha بعد الدفع>, approved_tags += "siraj-linux-patch-v4.2.0"

# 3) الوسم ثم السير
git tag siraj-linux-patch-v4.2.0 && git push origin siraj-linux-patch-v4.2.0
python scripts/check_release_gate.py --tag siraj-linux-patch-v4.2.0 --commit <sha>
```

بعد نجاح السير: المخرجات تبقى **ترقيعًا** فقط (`runtime_api: 1`) فوق AppImage 4.1.1،
بلا تحزيم كامل جديد.
