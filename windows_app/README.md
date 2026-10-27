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
- تنقل بـ Page Up/Page Down والأسهم والسحب والعجلة.
- البسملة مستقلة أسفل عنوان السورة في السور التي لا تعدّها آية، وتُفصل من بداية نص الآية الأولى في بيانات حفص لبقية السور. لا يغيّر التطبيق ترقيم الفاتحة في المصدر المختار حتى لا يختل ربط التلاوة والتفسير.

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

## بناء Windows

يتطلب Python 3.13 وInno Setup 6 و7-Zip:

```powershell
windows_app\packaging\build_windows.ps1
```

النواتج غير المتتبعة داخل Git:

- `windows_app/release/Siraj-Quran-Setup-X.Y.Z-x64.exe`
- `windows_app/release/Siraj-Quran-X.Y.Z-windows-portable-x64.zip`
- `windows_app/release/SHA256SUMS.txt`

## المثبّت والنسخة المحمولة

- المثبّت per-user داخل `%LOCALAPPDATA%\Programs\Siraj` ولا يحتاج صلاحية مدير.
- النسخة المحمولة تحتوي `portable.flag` وتحفظ كل شيء في `UserData` بجوار البرنامج.
- مساعد `SirajPortableUpdater.exe` يحدّث النسخة المحمولة مع إبقاء `UserData` والرجوع إلى النسخة السابقة عند فشل الاستبدال.

## التحديث

يقرأ التطبيق قناة:

```text
update/windows/stable.json
```

ويتحقق من توقيع Manifest عبر Ed25519، ثم المنتج والإصدار والحجم وSHA-256 قبل تشغيل أي ملف. المثبّت المستقر يجب توقيعه أيضًا بـ Authenticode؛ GitHub Actions يمنع نشر Tag مستقر إن لم تُضبط الأسرار:

- `WINDOWS_SIGNING_PFX_BASE64`
- `WINDOWS_SIGNING_PFX_PASSWORD`
- `WINDOWS_UPDATE_SIGNING_SEED` — مفتاح Ed25519 الخاص المشفّر في GitHub Secrets، ولا يدخل المستودع

## مصدر الإصدار

`windows_app/version.py` هو المصدر الوحيد لرقم الإصدار. يجب أن يطابق Tag الصيغة:

```text
siraj-windows-vX.Y.Z
```
