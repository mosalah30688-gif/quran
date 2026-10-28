# إشعارات المصادر والمكونات الخارجية — سراج Windows Portable

رخصة MIT في جذر المستودع تخص **الكود والنصوص الأصلية لسراج فقط**. لا تعيد ترخيص القرآن أو التفاسير أو الترجمات أو التسجيلات أو الخطوط أو الأيقونة أو بيانات ومكتبات الطرف الثالث. تبقى الحقوق والشروط لأصحابها.

> هذا الملف إشعار مصدر وحقوق، وليس اعتمادًا علميًا. حالة الاعتماد وموانع الإصدار في `audit/THIRD_PARTY_REVIEW.md` و`audit/SCHOLARLY_REVIEW.md`.

## نصوص وبيانات القرآن

| المحتوى | المصدر/الإصدار | الإسناد والشروط |
|---|---|---|
| حفص العثماني والمبسّط، البحث، التجويد الملوّن، السور والأجزاء | AlQuran Cloud editions مقفلة بتاريخ 2026-10-28 | الاستجابات الخام وبصماتها والمولد في `audit/sources/alquran-cloud/2026-10-28/`؛ شروط الخدمة: <https://alquran.cloud/terms-and-conditions> |
| معاني الكلمات | dump رسمي من الموسوعة القرآنية، نسخة 2026-10-24 | المصدر: «الموسوعة القرآنية quranpedia.net»؛ <https://quranpedia.net/dumps>؛ تحفظ الرخصة والرابط وبصمة الأصل داخل الملف ودليل المصدر |
| مصاحف ورش وقالون والدوري | dumps رسمية من الموسوعة القرآنية، manifest 2026-10-27 | المصدر: «الموسوعة القرآنية quranpedia.net»؛ تحفظ أرقام المصاحف والإصدارات وبصمات الأصل داخل الملف ودليل المصدر |
| الأذكار | HisnElMuslim عند commit `872764ca013116c905f7fc9c3dc972c27cd37d4a` تحت MIT، وآيات من المصدر المقفول | لكل عنصر مرجع ظاهر؛ سجل الانتقاء في `audit/sources/adhkar-curation-1.1.0.json` |
| شروح قواعد التجويد `tajweed.json` | نص واجهة أصلي للمشروع | مسجل في `audit/sources/project-authored-data.json`؛ ما زال الاعتماد العلمي البشري مطلوبًا |

خريطة المنشأ والبصمات لكل JSON في `audit/DATA_PROVENANCE.md`. لا يدعي سراج ملكية النص القرآني أو المواد التراثية.

## التفاسير والترجمات الحية

تُطلب النصوص عند الاستخدام من AlQuran Cloud وقد تُخزن محليًا لتسريع العرض؛ لا يحوّل ذلك ملكيتها إلى المشروع. الطبعات المعروضة ذات الإسناد المسجل:

- التفاسير: `ar.muyassar`, `ar.jalalayn`, `ar.baghawi`, `ar.qurtubi`, `ar.miqbas`.
- الترجمات: `en.sahih`, `fr.hamidullah`, `ur.jalandhry`, `tr.diyanet`.

السجل التفصيلي: `audit/alquran-edition-rights-2026-10-28.json`. حُجبت `ar.waseet` لعدم ثبوت إذن خاص، و`id.indonesian` لأن المترجم في metadata غير معروف. اسم المترجم/المفسر ومعرّف الطبعة جزء من الإسناد ولا يجوز حذفه.

## التلاوات

### حفص — Islamic Network / AlQuran Cloud

تُبث 17 تلاوة من `cdn.islamic.network` بمعرّفات الطبعات والسرعات المنشورة. تنص شروط الخدمة على أنها مرخصة للخدمة من القراء أو ورثتهم لإعادة التوزيع المجاني غير التجاري، وتبقى الحقوق لأصحاب التسجيلات:

`ar.alafasy`, `ar.abdurrahmaansudais`, `ar.abdulsamad`, `ar.husary`, `ar.minshawi`, `ar.mahermuaiqly`, `ar.saoodshuraym`, `ar.muhammadayyoub`, `ar.muhammadjibreel`, `ar.abdullahbasfar`, `ar.ahmedajamy`, `ar.hanirifai`, `ar.ibrahimakhbar`, `ar.hudhaify`, `ar.shaatree`, `ar.aymanswoaid`, `ar.parhizgar`.

- الشروط: <https://alquran.cloud/terms-and-conditions>
- دليل 51 probe: `audit/audio-cdn-probe-2026-10-28.json`

### ورش وقالون والدوري — MP3Quran

تُبث ملفات السور من `cdn.mp3quran.net`. سياسة MP3Quran المنشورة تتيح للزائر والمطور استعمال المواد والروابط. لا يعيد سراج استضافة الملفات ولا يدعي ملكيتها. من ذلك عبدالباسط عبدالصمد `r2`: مصحف 52، «ورش عن نافع - مرتل»، 114 سورة.

- السياسة: <https://www.mp3quran.net/ar/privacy>
- API: <https://www.mp3quran.net/api/v3/reciters?language=ar>
- دليل خمس مجموعات كاملة و15 probe: `audit/riwayat-audio-mp3quran-2026-10-28.json`

تشغيل الصوت يرسل طلب HTTPS إلى مقدم الخدمة، فيرى عنوان IP وبيانات الطلب التقنية وفق سياسته. لا يجمع سراج حسابًا أو سجل استماع مركزيًا.

## الخطوط

Amiri وAmiri Quran وNoto Naskh Arabic وNoto Sans Arabic وScheherazade New مضمّنة تحت **SIL Open Font License 1.1**. ملفات الرخص الأصلية في `windows_app/fonts/` وتُنسخ إلى الحزمة.

## مكتبات التطبيق والمصدر المقابل

الحزمة مبنية من PySide6/Qt for Python 6.12.0 وShiboken6 6.12.0 (LGPL-3.0-only)، PyInstaller 6.22.3 (GPL مع استثناء توزيع)، miniaudio 1.71 (MIT)، cffi/pycparser، packaging، وPyNaCl/libsodium. يجمع البناء نصوص رخص **إغلاق التبعيات المثبت فعليًا** في `licenses/` وينتج SBOM.

تبقى مكتبات Qt المشتركة منفصلة وقابلة للاستبدال. يرافق الإصدار الكامل `Siraj-Quran-<version>-windows-corresponding-source.zip` وفيه مصادر PySide/Shiboken وQtBase وQtSvg المطابقة، وبصماتها وتعليمات إعادة البناء/الربط. SBOM أو رابط upstream وحدهما ليسا بديلًا عن الحزمة المرافقة.

## الأيقونة

أكد مالك المشروع أن الأيقونة عمل أصلي يملكه وأجاز تضمينها وتوزيعها مع سراج. الإقرار وبصمات أصول PNG/SVG/ICO في `audit/ICON_PROVENANCE.md`. هذا الإذن لا يضع الأيقونة تلقائيًا تحت MIT.

## عدم الضمان والاعتماد العلمي

نجاح فحوص البنية والبصمات لا يمثل اعتمادًا شرعيًا أو علميًا للرسم أو الروايات أو التجويد أو المعاني أو الأذكار. يلزم اعتماد بشري على البصمات النهائية المسجلة في `audit/SCHOLARLY_REVIEW.md`.
