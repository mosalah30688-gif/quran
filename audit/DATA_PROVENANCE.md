# سلسلة منشأ بيانات سراج 1.1.0

**تاريخ القفل:** 2026-10-28  
**النطاق:** كل ملفات JSON المضمّنة في Windows Portable وLinux AppImage

يمكن إعادة التحقق بالأمر:

```bash
python scripts/verify_data_provenance.py
python scripts/generate_alquran_data.py --verify
python scripts/generate_quranpedia_data.py --verify
python scripts/generate_quranpedia_tafsir_catalog.py --verify
python scripts/generate_adhkar_data.py --verify
```

## خريطة الملفات

| الملفات | المصدر المقفول | التحويل/الدليل |
|---|---|---|
| `hafs.json`, `quran-search.json`, `quran-tajweed.json`, `surahs.json`, `juz.json` | استجابات AlQuran Cloud الرسمية للطبعات `quran-uthmani`, `quran-simple`, `quran-simple-clean`, `quran-tajweed` | `audit/sources/alquran-cloud/2026-10-28/SOURCE.json` و`scripts/generate_alquran_data.py`؛ تحفظ الاستجابات الخام مضغوطة وبصماتها وتثبت 114 سورة و6236 آية و30 جزءًا |
| `quran-meanings.json` | dump رسمي `meanings.json.gz` من Quranpedia | `audit/sources/quranpedia/2026-10-27/` و`scripts/generate_quranpedia_data.py`؛ الملف الناتج يحمل رابط المصدر والنسخة والرخصة وبصمة الأصل |
| `quran-riwayat.json` | dumps الرسمية للمصاحف 4 (ورش) و7 (قالون) و6 (الدوري) من Quranpedia | الدليل والسكربت نفسيهما؛ يحتفظ التحويل بترقيم كل رواية وصفحتها ونصها ويثبت 114 سورة لكل مصحف |
| `tafsir-catalog.json` (Linux) | فهرس خدمة التفسير الرسمي `tafsir.json.gz` من Quranpedia، نسخة المحتوى `2026-10-24` ولقطة manifest بتاريخ `2026-10-28` | `audit/sources/quranpedia-tafsir/2026-10-28/` و`scripts/generate_quranpedia_tafsir_catalog.py`؛ يوحّد 6236 سجل آية و149 كتابًا، ثم يحتفظ بـ73 عملًا تراثيًا أوليًا حتى وفاة مؤلف 1350هـ، ويحذف التجميعات الحديثة والطبعات المكررة. الملف المضمّن **بيانات وصفية فقط**؛ نص التفسير يُطلب حيًا من API ولا يُعاد نشر قاعدة النصوص داخل AppImage |
| `adhkar.json` | مجموعة `asellam/HisnElMuslim` عند commit `872764ca013116c905f7fc9c3dc972c27cd37d4a` تحت MIT، مع آيتين من مصدر القرآن المقفول | `audit/sources/hisn-el-muslim/.../SOURCE.json`, `audit/sources/adhkar-curation-1.1.0.json`, و`scripts/generate_adhkar_data.py`؛ لكل عنصر مرجع ظاهر في التطبيق |
| `tajweed.json` | شروح واجهة أصلية كتبها المشروع لرموز مصدر التجويد | `audit/sources/project-authored-data.json`؛ حقوقها واضحة، لكن اعتماد دقتها العلمية ما زال ضمن المراجعة البشرية |

## شروط المصادر

- شروط AlQuran Cloud المقفلة وروابطها مسجلة في `SOURCE.json` وسجل الطبعات؛ النص لا يُنسب إلى المشروع ولا يُخلط بغير القرآن.
- رخصة Quranpedia الأصلية محفوظة في `audit/sources/quranpedia/2026-10-27/LICENSE.md` وفي `audit/sources/quranpedia-tafsir/2026-10-28/LICENSE.md`. تظهر عبارة «الموسوعة القرآنية quranpedia.net» ورقم النسخة في البيانات والواجهة. يوزع سراج فهرس التفاسير الصغير مع الإسناد، بينما يعرض نصوص الكتب مباشرة من API وفق إذن الاستعمال داخل التطبيقات ولا يجمد قاعدة النصوص.
- ترخيص MIT لمجموعة الأذكار محفوظ بجوار المصدر المقفول؛ لا يعني ذلك أن المشروع يدّعي ملكية نصوص القرآن أو الحديث التراثية.

## الحد العلمي

تطابق البصمات والبنية يثبت المنشأ وعدم التحريف في التحويل الآلي، لكنه لا يستبدل مراجعة بشرية مؤهلة للرسم والروايات والتجويد ومعاني الكلمات والأذكار. تبقى بوابة الإصدار مغلقة إلى أن تُسجل تلك المراجعة على **البصمات النهائية**.
