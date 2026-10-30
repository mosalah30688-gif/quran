# سراج — قرآن كريم لنظام Windows

هذا هو مسار Windows الجديد المستقل في الإصدار والترقيم، مع الحفاظ على خصائص تطبيق Android: المصحف والروايات والتلاوة والتفسير والترجمات والبحث والمعاني والتجويد والأذكار والحفظ والورد والعلامات والإحصاءات والتنزيل دون اتصال ومشاركة الآيات.

## النظام المستهدف

- Windows 10 إصدار 1809 أو أحدث.
- Windows 11.
- x64.

## تجربة القراءة

- خط **Amiri Quran** هو الافتراضي.
- خطوط مضمّنة للاختيار: Amiri، Noto Naskh Arabic، Scheherazade New.
- يستفيد من Arabic Typesetting وTraditional Arabic عند وجودهما في Windows.
- تحديد النص بالفأرة ولوحة المفاتيح ونسخه بـ `Ctrl+C`.
- زر نسخ للآية مع مرجعها، وقائمة سياق بزر الفأرة الأيمن.
- تظليل آيات دائم بأربعة ألوان.
- فهرس سورة/جزء/آية منسدل لا يحجز مساحة دائمة.
- عرض حفص يحاكي تنسيق الشاملة: مساحة قراءة واسعة، عنوان وبسملة في المنتصف، وآيات في فقرة متصلة بأسطر متقاربة وعلامات آيات زخرفية. عدد الأسطر يتجاوب مع عرض النافذة وحجم الخط؛ وفي العرض العريض تظهر صفحة الحجر الأولى في نحو ثلاثة أسطر كما في المرجع البصري.
- تنقل بـ Page Up/Page Down والأسهم والسحب الأفقي المقصود؛ العجلة ولوحة اللمس تمرران الصفحة رأسيًا ولا تقلبان صفحات المصحف.
- البسملة مستقلة أسفل عنوان السورة في السور التي لا تعدّها آية، وتُفصل من بداية نص الآية الأولى في بيانات حفص لبقية السور، فتظهر مرة واحدة فقط. هذا تغيير عرض لا تغيير نص؛ لا يغيّر التطبيق ترقيم الفاتحة أو بيانات المصدر أو ربط التلاوة والتفسير.

## تشغيل التطوير

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r windows_app\requirements.txt
.venv\Scripts\python windows_app\main.py
```

اختبار سريع:

```powershell
.venv\Scripts\python windows_app\main.py --selftest
```

اختبار الواجهة الكامل:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python windows_app\tests\ui_test.py
```

## بناء Windows Portable

يتطلب Python 3.13 و7-Zip فقط؛ لا يُبنى أي مثبّت:

```powershell
windows_app\packaging\build_windows.ps1
```

النواتج غير المتتبعة داخل Git:

- `windows_app/release/Siraj-Quran-X.Y.Z-windows-portable-x64.zip`
- `windows_app/release/SHA256SUMS.txt`
- ويضيف CI ملف `SBOM.cdx.json`.

## النسخة المحمولة

- فك ZIP كاملًا ثم شغّل `Siraj.exe`؛ لا تحتاج إلى تثبيت أو صلاحية مدير.
- تحتوي `portable.flag` وتحفظ كل شيء في `UserData` بجوار البرنامج، ولا تستخدم Registry للإعدادات.
- مساعد `SirajPortableUpdater.exe` يحدّثها مع إبقاء `UserData` والرجوع إلى النسخة السابقة عند فشل الاستبدال.
- يختبر CI التشغيل العادي بلا Console كما لو نقر المستخدم الملف من Explorer، بالإضافة إلى self-test من الملف المضغوط.

## التحديث

يقرأ التطبيق قناة:

```text
update/windows/stable.json
```

ويتحقق من توقيع Manifest عبر Ed25519، ثم المنتج والإصدار والحجم وSHA-256 قبل تطبيق ZIP المحمول. لا تُستخدم شهادة Authenticode حاليًا، وقد يظهر تحذير SmartScreen المعتاد؛ أمان قناة التحديث يعتمد على توقيع Ed25519 والبصمة والحجم. مفتاح `WINDOWS_UPDATE_SIGNING_SEED` الخاص محفوظ في GitHub Secrets فقط ولا يدخل المستودع.

## مصدر الإصدار

`windows_app/version.py` هو المصدر الوحيد لرقم الإصدار. يجب أن يطابق Tag الصيغة:

```text
siraj-windows-vX.Y.Z
```
