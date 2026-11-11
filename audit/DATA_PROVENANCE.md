# سلسلة منشأ بيانات سراج 1.4.4

**تاريخ القفل:** 2026-11-02
**النطاق:** ملفات JSON وقاعدة التفسير SQLite وطبقات التعلم المضمّنة في Android وWindows وLinux

يمكن إعادة التحقق بالأمر:

```bash
python scripts/verify_data_provenance.py
python scripts/generate_alquran_data.py --verify
python scripts/generate_quranpedia_data.py --verify
python scripts/generate_quranpedia_tafsir_catalog.py --verify
python scripts/fetch_offline_tafsir_data.py --verify
python scripts/build_offline_tafsir.py --verify
python scripts/generate_adhkar_data.py --verify
python scripts/verify_tajweed_learning.py
python scripts/verify_tajweed_scopes.py
python scripts/verify_tajweed_source_candidates.py
python scripts/verify_tajweed_reference_sources.py
python scripts/verify_tajweed_wajh_review_packet.py
python scripts/verify_tajweed_wajh_review_response.py
```

## نص المصحف المعروض في `hafs.json` (2026-11-06، أُقفل في 1.4.9)

النص المعروض في المصحف (`hafs.json` في الجذر، و`mushaf_app/data/hafs.json`، و`windows_app/data/hafs.json`)
يُبنى الآن من **«مصحف حفص» في Quranpedia.net** (`mushafs-1`) — وهو نفس مصدر روايات ورش وقالون والدوري
في التطبيق — أي رسم مصحف المدينة بعلامات الوقف الست. البصمة المقفولة:
`caa2d0d091a0e6f8758b2852bc36895d579d362558b778bfd4dcb973483bd9ec` (2,823,508 بايت، 6,236 آية).

إعادة البناء والتحقق:

```bash
python3 scripts/build_hafs_text.py --check
```

ثوابت الناتج (يفشل السكربت إن اختلّت):

* علامات الوقف الست موجودة في المتن: ۖ 1651 · ۗ 511 · ۚ 2083 · ۘ 21 · ۛ 6 (وۜ 7)، ومعها ۞ 199 و۩ 15.
* **علامة الحزب `۞` موجودة** كما في مصحف المدينة: 199 موضعًا، ملصقة بأول كلمة في الآية
  التي يبدأ عندها ربع الحزب حتى لا يتغيّر عدد الكلمات ولا تقسيم الأسطر.
* **علامة السجدة `۩` في نهاية الآية** في المواضع الخمسة عشر فقط: `7:206 · 13:15 · 16:50 ·
  17:109 · 19:58 · 22:18 · 22:77 · 25:60 · 27:26 · 32:15 · 38:24 · 41:38 · 53:62 · 84:21 · 96:19`.
* ترقيم الصفحات (604) لم يتغيّر، وعدد كلمات كل آية لم يتغيّر، حتى يبقى تقسيم الأسطر في
  `quran-madani-lines.json` صالحًا (الاستثناء الوحيد: فصل «لَّوۡمَا» في 15:7 إلى كلمتين كما كان).
* `simple` (الرسم الإملائي): أُزيل BOM من 1:1، وأُزيلت البسملة المكرّرة داخل الآية الأولى من 112 سورة.

### ما تغيّر عن نص 1.4.7/1.4.8
كان 1.4.5–1.4.8 يعرض نص Tanzil منزوع علامات الوقف والحزب والميم الصغيرة. طلب المالك (2026-11-06)
رجوع علامات التوقيف وضبط الرسم كنسخة ورش، فأُبدل المصدر إلى Quranpedia واعتُمد خط **Scheherazade New**
افتراضيًا لرسم المصحف، لأن خط Amiri Quran المعروض سابقًا كان يفصل حركات الضبط عن حروفها في المتصفح.

## خريطة الملفات

| الملفات | المصدر المقفول | التحويل/الدليل |
|---|---|---|
| `hafs.json`, `quran-search.json`, `quran-tajweed.json`, `surahs.json`, `juz.json` | استجابات AlQuran Cloud الرسمية للطبعات `quran-uthmani`, `quran-simple`, `quran-simple-clean`, `quran-tajweed` | `audit/sources/alquran-cloud/2026-10-28/SOURCE.json` و`scripts/generate_alquran_data.py`؛ تحفظ الاستجابات الخام مضغوطة وبصماتها وتثبت 114 سورة و6236 آية و30 جزءًا |
| `quran-meanings.json` | dump رسمي `meanings.json.gz` من Quranpedia | `audit/sources/quranpedia/2026-10-27/` و`scripts/generate_quranpedia_data.py`؛ الملف الناتج يحمل رابط المصدر والنسخة والرخصة وبصمة الأصل |
| `quran-riwayat.json` | dumps الرسمية للمصاحف 4 (ورش) و7 (قالون) و6 (الدوري) من Quranpedia | الدليل والسكربت نفسيهما؛ يحتفظ التحويل بترقيم كل رواية وصفحتها ونصها ويثبت 114 سورة لكل مصحف |
| `tafsir-catalog.json` | فهرس خدمة التفسير الرسمي `tafsir.json.gz` من Quranpedia، نسخة المحتوى `2026-10-24` ولقطة manifest بتاريخ `2026-10-28` | `audit/sources/quranpedia-tafsir/2026-10-28/` و`scripts/generate_quranpedia_tafsir_catalog.py`؛ يوحّد 6236 سجل آية و149 كتابًا، ثم يحتفظ بـ73 عملًا تراثيًا أوليًا حتى وفاة مؤلف 1350هـ، ويحذف التجميعات الحديثة والطبعات المكررة |
| `tafsir-offline.sqlite3` | 73 ملف كتاب رسميًا من Quranpedia (إصدار `2026-08-10`، مجموع مضغوط 663,702,274 بايت) و5 لقطات تفسير من AlQuran Cloud بتاريخ `2026-10-28` | قائمة ملفات الكتب وبصماتها في `audit/sources/quranpedia-tafsir/2026-10-28/OFFLINE_SOURCE.json`، ولقطات AlQuran في `audit/sources/alquran-tafsir/2026-10-28/SOURCE.json`؛ ينظف `scripts/build_offline_tafsir.py` HTML إلى Unicode ويضغط مجموعات 16 آية داخل SQLite بذاكرة محدودة. قفل الناتج في `audit/offline-tafsir-data.json`: 78 طبعة، 344,410 نصًا غير فارغ، SHA-256 `66ce7736d44679a2b6fc536635a556881d8c7f98bad47fa5622a155700c1900c` |
| `adhkar.json` | مجموعة `asellam/HisnElMuslim` عند commit `872764ca013116c905f7fc9c3dc972c27cd37d4a` تحت MIT، مع آيتين من مصدر القرآن المقفول | `audit/sources/hisn-el-muslim/.../SOURCE.json`, `audit/sources/adhkar-curation-1.1.0.json`, و`scripts/generate_adhkar_data.py`؛ لكل عنصر مرجع ظاهر في التطبيق |
| `tajweed.json` | شروح واجهة أصلية كتبها المشروع لرموز مصدر التجويد | `audit/sources/project-authored-data.json`؛ حقوقها واضحة، لكن اعتماد دقتها العلمية ما زال ضمن المراجعة البشرية |
| `tajweed-learning-catalog.json` ونسختاه المتطابقتان في بيانات Windows/Linux | تحويل منظم لشروح `tajweed.json` وأكواد علامات لقطة `quran-tajweed.json` المقفلة، مع تصنيف تعليمي من ثلاث مراحل دون إدخال حكم خارجي جديد | `scripts/verify_tajweed_learning.py` يثبت التطابق وبنية الفهم/التمييز/التطبيق ووجود الأمثلة ويقفل النطاق على حفص بقيمتي طريق/وجه صريحتين بأن المصدر غير محدد، و`verify_android_bundle.py` يمنع انجراف نسخ المنصات؛ الحالة `PENDING_SCHOLARLY_REVIEW` والروايات الأخرى تفشل مغلقًا |
| `tajweed-scope-registry.json`, `tajweed-curriculum.schema.json` | سجل وعقد أنشأهما المشروع لتنظيم المصادر؛ لا يضيفان حكمًا شرعيًا أو علامة تجويد | `scripts/verify_tajweed_scopes.py` يطابق كل اختيار مصحف مع روايته ونصه وبصمته، يمنع fallback بين النطاقات، ويفرض على أي حزمة مستقبلية مصدرًا مرخصًا مقفولًا ومراجعة مؤهلة واعتماد نشر ثانٍ |
| `tajweed-curricula/*.json` | حزمة مستقلة لكل `riwayah/tariq/wajh/edition` بعد تثبيت المصدر والترخيص | المجلد فارغ حاليًا عمدًا؛ `tajweed-curriculum-loader.js` يطابق بصمة artifact وبصمة طبعة النص والنطاق والمراجعة ويفحص حدود Unicode، وقنوات Android/PWA/update تنقل الملفات ديناميكيًا عند اعتمادها فقط. لا تُنشأ حزمة لورش أو قالون أو الدوري من تخمين أو من قواعد حفص |
| `audit/tajweed-source-candidates.json` و`audit/tajweed-candidates/*.analysis.json` | بيانات وصفية لمرشحات بحثية فقط؛ لا تحتوي متن القرآن أو corpus العلامات | `scripts/verify_tajweed_source_candidates.py` يثبت بقاء المرشحات في الحجر وعدم تسربها إلى runtime. حلل `scripts/analyze_warsh_tajweed_candidate.py` حزمة ورش/الأزرق ذات البصمة المقفلة: 6,214 آية و46 معرف حكم؛ فشلت بوابات الحقوق والربط النصي والمراجعة، ولذلك لا تنشر |
| `audit/sources/tajweed-riwayat/2026-11-02/` و`audit/sources/quranpedia/2026-11-02/` | سجل مراجع مؤرخ، وخريطة موضوعات بلا متن قواعد، ولقطة مرخصة لنصوص ورش وقالون والدوري لأغراض التدقيق فقط | `scripts/verify_tajweed_reference_sources.py` يثبت ورش/الأزرق، وقالون/أبي نشيط، والدوري عن أبي عمرو/أبي الزعراء من طريق الشاطبية، مع إبقاء الوجه وcorpus العلامات والمراجعة محجورة. يثبت أيضًا تعارض الدوري الرسمي 6214/6217 وخطأ شطر `67:9` الذي رفع dump الحالي إلى 6218، ويؤكد صفر مناهج runtime مفعلة |
| `WAJH_REVIEW_PACKET.json` و`WAJH_REVIEW_GUIDE.ar.md` | حزمة قرار مشتقة آليًا من خريطة الموضوعات، بلا قرآن أو متن قواعد أو أمثلة أو علامات؛ مخصصة لمراجع مؤهل في النطاق الدقيق | `scripts/verify_tajweed_wajh_review_packet.py` يثبت تغطية 17 قرارًا لورش و14 لقالون و12 للدوري، وفراغ جميع الاختيارات والتواقيع، واستقلال بوابات العدد والحقوق والاعتماد الثاني، وعدم تسرب الحزمة إلى runtime |
| `WAJH_REVIEW_RESPONSE.schema.json` و`WAJH_REVIEW_RESPONSE_TEMPLATE.json` | عقد وقالب metadata-only لاستقبال جواب المراجع وربطه ببصمة الحزمة، من دون افتراض صحة علمية آلية | `scripts/verify_tajweed_wajh_review_response.py` يفرض اكتمال كل قرار والوجه والطبعة والعد وبصمات الأدلة، ويفصل المراجع عن المعتمد الثاني، ويرفض 6218 للدوري، مع إبقاء `publishableAsApproved=false` وruntime مغلقًا دائمًا |

## شروط المصادر

- شروط AlQuran Cloud المقفلة وروابطها مسجلة في `SOURCE.json` وسجل الطبعات؛ النص لا يُنسب إلى المشروع ولا يُخلط بغير القرآن.
- رخصة Quranpedia الأصلية محفوظة في `audit/sources/quranpedia/2026-10-27/LICENSE.md` و`audit/sources/quranpedia/2026-11-02/LICENSE.md` وفي `audit/sources/quranpedia-tafsir/2026-10-28/LICENSE.md`. تظهر عبارة «الموسوعة القرآنية Quranpedia.net» ورقم النسخة مع رابط المصدر؛ لقطة الروايات التدقيقية القابلة للتنزيل تنسب الإصدار `2026-11-02` صراحةً، وملفات كتب التفسير تنسب إصدارها `2026-08-10`. تسمح الرخصة بالاستعمال داخل التطبيقات، وتوجب النسبة والرابط ورقم الإصدار عند نشر أصل البيانات القابل للتنزيل.
- ترخيص MIT لمجموعة الأذكار محفوظ بجوار المصدر المقفول؛ لا يعني ذلك أن المشروع يدّعي ملكية نصوص القرآن أو الحديث التراثية.

## الحد العلمي

تطابق البصمات والبنية يثبت المنشأ وعدم التحريف في التحويل الآلي، لكنه لا يستبدل مراجعة بشرية مؤهلة للرسم والروايات والتجويد ومعاني الكلمات والأذكار. تبقى بوابة الإصدار مغلقة إلى أن تُسجل تلك المراجعة على **البصمات النهائية**.

## روايات إضافية (1.5.9)

- الروايات الأربع المضافة — شعبة (mushaf 9)، السوسي (10)، البزي (5)، قنبل (8) — مسحوبة من لقطة `audit/sources/quranpedia/2026-11-08/` (manifest موقّع بالبصمات: 414289/421838/414289/413392 بايت) ومسجَّلة في `additional_files` داخل `audit/sources/quranpedia/2026-10-27/SOURCE.json`.
- صفوف الروايات الثلاث المعتمدة سابقًا (ورش/قالون/الدوري) لم تتغير حرفًا واحدًا؛ ولذلك بقيت بصماتها القانونية (`canonicalPayloadSha256WithoutTopLevelLicense`) كما هي، وأُعيد تثبيت بصمة الملف فقط في سجل `tajweed-scope-registry.json` و`audit/SCHOLARLY_REVIEW.md` و`audit/tajweed-source-candidates.json` وبطاقة مراجعة الوجه.
- الأصوات الجديدة مثبتة في `audit/riwayat-audio-mp3quran-2026-11-05.json`: سبعة مصادر، لكل مصدر سبر مباشر لثلاث سور (١، ٥٠، ١١٤) مع `content_type` و`content_range` وبصمة مقطع.

## فيديو شاشة الأذان (1.6.0)

- `media/adhan/mosque-adhan.mp4` — ٢٤ ثانية، ٧٢٠×١٢٨٠، H.264 Main@4.0، حلقة سلسة (تقدّم ثم رجوع)، بلا صوت. SHA-256: `46c6ee02f33916d6dd48d0443a613fb1837c532b43fadc048a9f3dad7fda783d`.
- `media/adhan/mosque-adhan-poster.jpg` (ملصق أول لقطة). SHA-256: `1c41efc74e910d2fcdfb7ad657c496c6421da7e15e6408507d2d6bc842a3e9c5`.
- الصورة الأصلية المولّدة داخل المشروع `assets-source/mosque-adhan.png`، SHA-256: `5dc9eca92fef5246c5bff76632136ec02e0b2b478532ccd21a68b62f828e7b33` — لا حقوق طرف ثالث، ولا وجوه أشخاص، ولا موسيقى.
- الفيديو **زخرفة صامتة** (muted + loop + playsinline، بلا عناصر تحكم صوتية)؛ صوت الأذان يبقى في مشغّل منفصل حتى يعمل زرّا التخفيض والتعلية والإيقاف المؤقت على الصوت فقط.
- يُنسخ إلى `www/media/adhan/` في `scripts/build-www.sh` ويُخزَّن مسبقًا في `sw.js`، فيعمل دون إنترنت من أول تشغيل.
