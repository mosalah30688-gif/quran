# سراج — قرآن كريم لنظام Linux

تطبيق Qt أصلي يوزّع كملف **AppImage x86_64** واحد، دون DEB أو RPM أو صلاحيات مدير.

## تجربة قراءة حفص

- عرض واسع متجاوب يحاكي تنسيق المكتبة الشاملة: عنوان وبسملة في المنتصف، وفقرة آيات متصلة بأسطر متقاربة وعلامات زخرفية.
- الفهرس يفتح عند الحاجة ولا يحجز مساحة دائمة من النص؛ وفي نافذة عريضة تظهر صفحة الحجر الأولى في نحو ثلاثة أسطر كما في المرجع البصري.
- تُفصل البسملة المدمجة من أول آية في طبعات حفص للعرض فقط، فتظهر مرة واحدة دون تغيير ملفات المصدر أو ترقيم الآيات أو روابط التلاوة والتفسير.
- الروايات الأخرى تحتفظ بطريقة عرضها وبياناتها.

## التشغيل من المصدر

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python ../scripts/fetch_offline_tafsir_data.py
python main.py
```

## الاختبارات

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p 'test_*.py' -v
QT_QPA_PLATFORM=offscreen python tests/ui_test.py
QT_QPA_PLATFORM=offscreen python main.py --selftest
```

## بيانات التفسير المحلية

تُثبت `scripts/fetch_offline_tafsir_data.py` قاعدة SQLite المقفلة ببصمة SHA-256 في `data/`. تضم 78 خيارًا (73 كتابًا تراثيًا من Quranpedia و5 طبعات AlQuran Cloud)، وتفك ضغط مجموعة صغيرة من الآيات عند الطلب فقط، فلا تُحمّل الكتب الضخمة كاملة في الذاكرة. الآيات غير المغطاة في بعض المصنفات الجزئية تُعرض كغياب موثق في المصدر، لا كخطأ اتصال.

## بناء AppImage

يتطلب البناء Linux x86_64 ومكتبات Qt/X11 المذكورة في `.github/workflows/linux-appimage.yml`:

```bash
bash build_appimage.sh
```

الناتج داخل `release/`:

- `Siraj-Quran-4.1.2-linux-x86_64.AppImage`
- `SHA256SUMS.txt`

يضيف CI كذلك `Siraj-Quran-4.1.2-linux-corresponding-source.zip` و`SBOM.cdx.json` بعد جرد رخص الحزمة والتحقق من أقفال مصادر النظام الدقيقة.

يُنزّل السكربت `appimagetool` 1.9.1 وType-2 runtime الثابت `20251108` من إصدارات محددة، ويتحقق من SHA-256 لكليهما قبل الاستعمال. لا يعتمد AppImage الناتج على FUSE 2 في جهاز المستخدم. يضيف CI ملف CycloneDX SBOM، ويفحص metadata، ثم يشغّل AppImage نفسه بلا arguments تحت Xvfb ويتحقق من نافذة «سراج».

## التشغيل بعد التنزيل

امنح الملف صلاحية التنفيذ مرة واحدة ثم افتحه بالنقر المزدوج:

```bash
chmod +x Siraj-Quran-4.1.2-linux-x86_64.AppImage
```

تُحفظ الإعدادات والملفات المؤقتة وفق مسارات XDG الخاصة بالمستخدم، ولا تُكتب بيانات داخل AppImage. عند غياب streams في تشغيل سطح المكتب، يوجد سجل تشخيص في:

```text
~/.local/state/siraj/logs/siraj-startup.log
```

لا يُنشر أي إصدار جديد ولا تُحدّث القناة المستقرة قبل اكتمال مراجعة تراخيص المحتوى والمراجعة العلمية واجتياز بوابة الإصدار. راجع `THIRD_PARTY_NOTICES.md`.
