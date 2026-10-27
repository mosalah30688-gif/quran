# سراج — قرآن كريم لنظام Linux

تطبيق Qt أصلي يوزّع كملف **AppImage x86_64** واحد، دون DEB أو RPM أو صلاحيات مدير.

## التشغيل من المصدر

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## الاختبارات

```bash
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p 'test_*.py' -v
QT_QPA_PLATFORM=offscreen python tests/ui_test.py
QT_QPA_PLATFORM=offscreen python main.py --selftest
```

## بناء AppImage

يتطلب البناء Linux x86_64 ومكتبات Qt/X11 المذكورة في `.github/workflows/linux-appimage.yml`:

```bash
bash build_appimage.sh
```

الناتج داخل `release/`:

- `Siraj-Quran-1.0.0-linux-x86_64.AppImage`
- `SHA256SUMS.txt`

يُنزّل السكربت `appimagetool` 1.9.1 وType-2 runtime الثابت `20251108` من إصدارات محددة، ويتحقق من SHA-256 لكليهما قبل الاستعمال. لا يعتمد AppImage الناتج على FUSE 2 في جهاز المستخدم. يضيف CI ملف CycloneDX SBOM، ويفحص metadata، ثم يشغّل AppImage نفسه بلا arguments تحت Xvfb ويتحقق من نافذة «سراج».

## التشغيل بعد التنزيل

امنح الملف صلاحية التنفيذ مرة واحدة ثم افتحه بالنقر المزدوج:

```bash
chmod +x Siraj-Quran-1.0.0-linux-x86_64.AppImage
```

تُحفظ الإعدادات والملفات المؤقتة وفق مسارات XDG الخاصة بالمستخدم، ولا تُكتب بيانات داخل AppImage. عند غياب streams في تشغيل سطح المكتب، يوجد سجل تشخيص في:

```text
~/.local/state/siraj/logs/siraj-startup.log
```

النشر العام المستقر غير مفعّل إلى أن تكتمل مراجعة تراخيص المحتوى والمراجعة العلمية. راجع `THIRD_PARTY_NOTICES.md`.
