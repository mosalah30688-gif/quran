# إشعارات المصادر والمكونات الخارجية — سراج Linux AppImage

رخصة MIT في جذر المستودع تخص **الكود والنصوص الأصلية لسراج فقط**. لا تعيد ترخيص القرآن أو التفاسير أو التسجيلات أو الخطوط أو الأيقونة أو بيانات ومكتبات الطرف الثالث. تبقى الحقوق والشروط لأصحابها.

> هذا الملف إشعار مصدر وحقوق، وليس اعتمادًا علميًا. حالة الاعتماد وموانع الإصدار في `audit/THIRD_PARTY_REVIEW.md` و`audit/SCHOLARLY_REVIEW.md`.

## نصوص وبيانات القرآن

| المحتوى | المصدر/الإصدار | الإسناد والشروط |
|---|---|---|
| حفص العثماني والمبسّط، البحث، السور والأجزاء | AlQuran Cloud editions مقفلة بتاريخ 2026-10-28 | الاستجابات الخام وبصماتها والمولد في `audit/sources/alquran-cloud/2026-10-28/`؛ <https://alquran.cloud/terms-and-conditions> |
| معاني الكلمات | dump رسمي من الموسوعة القرآنية، نسخة 2026-10-24 | المصدر: «الموسوعة القرآنية quranpedia.net»؛ <https://quranpedia.net/dumps>؛ الرخصة والرابط وبصمة الأصل محفوظة في الناتج والدليل |
| مصاحف ورش وقالون والدوري | dumps رسمية من الموسوعة القرآنية، manifest 2026-10-27 | المصدر: «الموسوعة القرآنية quranpedia.net»؛ تحفظ أرقام المصاحف والإصدارات وبصمات الأصل |
| الأذكار | HisnElMuslim عند commit `872764ca013116c905f7fc9c3dc972c27cd37d4a` تحت MIT، وآيات من المصدر المقفول | لكل عنصر مرجع ظاهر؛ `audit/sources/adhkar-curation-1.1.0.json` |
| شروح قواعد التجويد `tajweed.json` | نص واجهة أصلي للمشروع | `audit/sources/project-authored-data.json`؛ ما زال الاعتماد العلمي البشري مطلوبًا |

خريطة المنشأ والبصمات لكل JSON في `audit/DATA_PROVENANCE.md`. لا يدعي سراج ملكية النص القرآني أو المواد التراثية.

## التفاسير الحية

- تبقى طبعات AlQuran Cloud الخمس المدققة: `ar.muyassar`, `ar.jalalayn`, `ar.baghawi`, `ar.qurtubi`, `ar.miqbas`. السجل: `audit/alquran-edition-rights-2026-10-28.json`. حُجبت `ar.waseet` لعدم ثبوت إذن خاص.
- أضيف فهرس **73 كتاب تفسير تراثيًا** من dump خدمة Quranpedia الرسمي، نسخة المحتوى `2026-10-24` ولقطة manifest `2026-10-28`. تحفظ الأدلة والرخصة والبصمة في `audit/sources/quranpedia-tafsir/2026-10-28/`، والمولد في `scripts/generate_quranpedia_tafsir_catalog.py`.
- معيار الاختيار المعلن: عمل تراثي أولي، وفاة المؤلف المسجلة لا تتجاوز 1350هـ، مع حذف التجميعات الحديثة والطبعات المكررة والكتب المكافئة الموجودة أصلًا في قائمة AlQuran. لا تعتمد الإتاحة في الشاملة دليلًا للحق ولا تُنسخ نصوص منها.
- لا يشحن AppImage قاعدة كتب التفسير: المضمّن فهرس وصفي صغير فقط، ويُطلب النص حيًا عند اختيار الآية من `api.quranpedia.net`. رخصة المصدر تجيز استعمال البيانات داخل التطبيقات، ويعرض سراج اسم Quranpedia ورقم النسخة في واجهة التفسير.

لا يحوّل العرض أو التخزين المؤقت أثناء جلسة التشغيل ملكية أي نص إلى المشروع، ولا يمثل وجود الكتاب اعتمادًا علميًا لكل ما فيه.

## التلاوات

### حفص — Islamic Network / AlQuran Cloud

تُبث 17 تلاوة من `cdn.islamic.network` بمعرّفات الطبعات والسرعات المنشورة. تنص شروط الخدمة على أنها مرخصة للخدمة من القراء أو ورثتهم لإعادة التوزيع المجاني غير التجاري، وتبقى الحقوق لأصحاب التسجيلات:

`ar.alafasy`, `ar.abdurrahmaansudais`, `ar.abdulsamad`, `ar.husary`, `ar.minshawi`, `ar.mahermuaiqly`, `ar.saoodshuraym`, `ar.muhammadayyoub`, `ar.muhammadjibreel`, `ar.abdullahbasfar`, `ar.ahmedajamy`, `ar.hanirifai`, `ar.ibrahimakhbar`, `ar.hudhaify`, `ar.shaatree`, `ar.aymanswoaid`, `ar.parhizgar`.

- الشروط: <https://alquran.cloud/terms-and-conditions>
- دليل 51 probe: `audit/audio-cdn-probe-2026-10-28.json`

### ورش وقالون والدوري — MP3Quran

تُبث ملفات السور من `cdn.mp3quran.net`. سياسة MP3Quran المنشورة تتيح للزائر والمطور استعمال المواد والروابط. لا يعيد سراج استضافة الملفات ولا يدعي ملكيتها. عبدالباسط عبدالصمد `r2` هو المصحف 52 «ورش عن نافع - مرتل»، كامل 114 سورة.

- السياسة: <https://www.mp3quran.net/ar/privacy>
- API: <https://www.mp3quran.net/api/v3/reciters?language=ar>
- دليل خمس مجموعات كاملة و15 probe: `audit/riwayat-audio-mp3quran-2026-10-28.json`

تشغيل الصوت يرسل طلب HTTPS إلى مقدم الخدمة، فيرى عنوان IP وبيانات الطلب التقنية وفق سياسته. لا يجمع سراج حسابًا أو سجل استماع مركزيًا.

## الخطوط

Amiri وAmiri Quran وNoto Naskh Arabic وScheherazade New مضمّنة تحت **SIL Open Font License 1.1**. ملفات الرخص الأصلية في `mushaf_app/fonts/` وتُنسخ إلى AppImage. يطبّق اختيار الخط والحجم نفسه على المصحف والتفسير.

## مكتبات Python وQt

الحزمة مبنية من PySide6/Qt for Python 6.12.0 وShiboken6 6.12.0 (LGPL-3.0-only)، PyInstaller 6.22.3 (GPL مع استثناء توزيع)، miniaudio 1.71 (MIT)، cffi/pycparser، packaging، وPyNaCl/libsodium. يجمع البناء نصوص رخص إغلاق التبعيات الفعلي في `usr/share/doc/siraj/licenses/` وينتج SBOM.

تبقى مكتبات Qt المشتركة داخل AppImage قابلة للاستخراج والاستبدال وإعادة الحزم. يرافق الإصدار الكامل `Siraj-Quran-<version>-linux-corresponding-source.zip` وفيه مصادر PySide/Shiboken وQtBase وQtSvg وQtWayland المطابقة، وبصماتها وتعليمات إعادة البناء.

## AppImage runtime ومكتبات النظام

AppImage type2 runtime `20251108` مبني من commit `dd6cebedcbddde9c82f89b011e8e1d40b6e43868`، ويستخدم libfuse 3.15.0 (LGPL-2.1-only)، squashfuse 0.5.2، zstd 1.5.6، zlib 1.3.1، mimalloc 2.1.7 وmusl 1.2.5. حزمة corresponding-source المرافقة تتضمن مصادرها وبصماتها وتعليمات إعادة ربط libfuse.

يجرد البناء كل مكتبة نظام نسخها PyInstaller، ويضم نص copyright للحزمة وقفل source package. لا يُعتمد إصدار نهائي إن بقي مدخل unmapped أو لم يطابق `.dsc` القفل أو اختلفت بصمة أحد ملفات المصدر.

## الأيقونة

أكد مالك المشروع أن **أيقونة التطبيق الأصلية** عمل يملكه وأجاز تضمينها وتوزيعها مع سراج؛ لم تُستبدل. الإقرار وبصمات الأصول في `audit/ICON_PROVENANCE.md`. هذا الإذن لا يضع الأيقونة تلقائيًا تحت MIT.

أيقونات الشريط الجانبي Fluent 3D رسوم SVG أصلية مضمّنة في كود Linux لسراج (تدرجات وظلال بلا حزمة أيقونات خارجية)، ولذلك لا تضيف مصدرًا خارجيًا أو ترخيص أيقونات جديدًا.

## عدم الضمان والاعتماد العلمي

نجاح فحوص البنية والبصمات لا يمثل اعتمادًا شرعيًا أو علميًا للرسم أو الروايات أو التجويد أو المعاني أو الأذكار. يلزم اعتماد بشري على البصمات النهائية في `audit/SCHOLARLY_REVIEW.md`.
