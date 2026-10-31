# سياسة الأمان | Security Policy

## الإصدارات المدعومة

تحصل القنوات المستقرة الحالية فقط على إصلاحات أمان جديدة:

| المنصة | القناة المدعومة |
|---|---:|
| Android | `1.4.x` |
| Windows | `4.1.x` فوق الحزمة الكاملة `4.1.1` |
| Linux | `4.1.x` فوق AppImage `4.1.1` |

تبقى الإصدارات الأقدم سجلات immutable ولا تُعدّل؛ يُنشر الإصلاح في إصدار جديد.

## الإبلاغ الخاص

لا تفتح Issue عامة لثغرة غير معالجة، ولا ترفق مفاتيح أو رموز وصول أو بيانات مستخدمين.

أرسل البلاغ عبر [صفحة التواصل الرسمية](https://elkatebmohamadsalah.blogspot.com/p/blog-page_827.html) مع:

- المنصة والإصدار.
- وصف الأثر وشروط الاستغلال.
- خطوات إعادة إنتاج محدودة وآمنة.
- إثبات مفهوم لا يمس بيانات الغير.
- وسيلة مناسبة للرد إن رغبت.

سيُراجع البلاغ، وقد يُطلب توضيح إضافي. لا تُنشر تفاصيل الاستغلال قبل إتاحة الإصلاح ومنح المستخدمين وقتًا معقولًا للتحديث.

## النطاق

يشمل النطاق كود سراج الأصلي، التحديثات، التحقق من التوقيع والبصمات، تخزين بيانات المستخدم محليًا، وتكاملات الشبكة التي ينفذها التطبيق. أما ثغرات GitHub أو نظام التشغيل أو مزود تلاوات خارجي فتُبلغ كذلك إلى الجهة المالكة للخدمة.

يُحظر اختبار يؤدي إلى تعطيل خدمة، أو الوصول إلى بيانات شخص آخر، أو تجاوز حسابات، أو نشر حزمة معدلة باسم سراج.

---

## Supported versions

Only the current stable lines receive new security fixes: Android `1.4.x`, Windows `4.1.x` on the `4.1.1` full baseline, and Linux `4.1.x` on the `4.1.1` AppImage baseline. Older immutable releases are not edited; fixes are published as new versions.

## Private reporting

Do not open a public Issue for an unpatched vulnerability and do not attach credentials, tokens, or user data. Report it through the [official contact page](https://elkatebmohamadsalah.blogspot.com/p/blog-page_827.html), including platform, version, impact, safe reproduction steps, and a non-destructive proof of concept.

Please withhold exploit details until a fix is available and users have had reasonable time to update. The scope covers original Siraj code, update integrity, local data handling, and application network integrations. Report vulnerabilities in GitHub, an operating system, or an external provider to that provider as well.
