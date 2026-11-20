# سراج لينكس 4.3.0 — نقل نظام أندرويد إلى لينكس بلا مساس بالشكل

**التاريخ:** 2026-11-05
**الإصدار:** `4.3.0` (ترقيع موقّع فوق AppImage 4.1.1، `runtime_api: 1` بلا تغيير)
**القناة:** `update/linux/patch-stable.json` · الوسم `siraj-linux-patch-v4.3.0`

---

## ما نُقل من أندرويد 1.12.3 (بناء 188)

| # | الميزة | التنفيذ في لينكس |
|---|---|---|
| ١ | **قائمة قرّاء واحدة بلا تقسيم آية/سورة** | `Main.reciter_options()` صارت تبني قائمة واحدة: قرّاء التلاوة المتزامنة أولًا ثم مصاحف المكتبة (mp3quran) لنفس الرواية. حُذف زر «مكتبة القرّاء» ونافذتها ووضع `voice/library` و`voice_mode`. |
| ٢ | **لا خلط روايات** | فلترة بـ`family` عبر `RIW_FAMILY`: حفص = ١٧ قارئًا صوتيًا + ١٦٦ مصحفًا حفصيًا = **١٨٣**؛ ورش ١٦ · قالون ١٦ · الدوري ١١. |
| ٣ | **البحث داخل القائمة نفسها** | القائمة صارت قابلة للكتابة مع `QCompleter` (`MatchContains`) — بحث بلا نافذة ثانية، و`restore_reciter_text()` يعيد النص عند الكتابة بلا اختيار. |
| ٤ | **المنشاوي الجديد (تسجيل ١٣٨٧هـ/١٩٦٧م)** | ظاهر في قائمة حفص مع المرتل والمجود والمعلم. |
| ٥ | **تحميل بصوت القارئ المختار** | بطاقة التحميل لم يبقَ فيها قائمة قارئ خاصة: زر «⬇ السورة» وزر «⬇ المصحف كاملًا» يعملان على `download_reciter_id()`، مع اختيار السورة والتخزين، وتقدير الحجم، وحذف تحميلات القارئ نفسه. |
| ٦ | **تمرير نافذة القراءة إلى الآية الجارية** | الآية الجارية تُوسم `id="ayah-play"` في `render_page()`، و`scroll_to_highlight()` يمرّرها لمنتصف الشاشة عند كل ملف آية. |

## ما حُفظ كما هو (طلب المالك)

- شكل صفحة المصحف: نفس الرسم والورقة والزخارف وترقيم المصاحف — بلا مساس.
- شاشة كبيرة: نفس التخطيط العريض، والفهرس يبقى مطويًا في حفص.
- **التبويبات على الجانب**: نفس شريط الجانب الأيمن وأيقوناته و«عن التطبيق» في آخره.
- كل ما في 4.2.0 (مواقيت + قبلة + أذان + تذكير + ورد + شارات + سرعة تلاوة) داخل هذا الترقيع نفسه.

## الأدلة (تشغيل محلي فعلي)

```
python -m unittest discover -s mushaf_app/tests  →  92 tests OK (skipped=1)
python mushaf_app/tests/ui_test.py                →  76 فحصًا OK، والفشلان المعتادان فقط
                                                     (tafsir-offline.sqlite3 غير منزَّل هنا؛ CI ينزّله)
python -m py_compile mushaf_app/*.py …             →  ok
python scripts/read_update_features.py mushaf_app/version.py → خمس ميزات صالحة
```

فحوص القائمة الجديدة داخل `ui_test.py`: `hafs voices come first` · `one list holds library mushafs too` ·
`library mushafs live inside the same reciter list` · `choosing a library mushaf activates it` ·
`synced reciter restores the same list` · `downloading follows the chosen reciter`.

## الترقيع

- الحجم المتوقع: كود فقط (`main.py`, `version.py`, الاختبارات) ≈ ٦٠ كيلوبايت داخل سقف 128 ميجابايت / 2000 ملف.
- البيانات لم تتغيّر: `mushaf_app/data/quran-reciters.json` = ٢٢٧ مصحفًا / ١٨٧ قارئًا (بصمته مثبّتة مسبقًا في `audit/sources/project-authored-data.json`).
- لا تغيير في `runtime_api` ولا `patch_runtime.py` ولا قناة Ed25519.
