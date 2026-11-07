package com.quran.mushaf;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * بعد إعادة تشغيل الهاتف أو تغيير الساعة أو تحديث التطبيق تُفقد منبّهات النظام،
 * فيعيد هذا المستقبل ضبط جدول الأذان من النسخة المحفوظة.
 */
public class AdhanBootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        if (action == null) return;
        if (Intent.ACTION_BOOT_COMPLETED.equals(action)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)
                || Intent.ACTION_TIME_CHANGED.equals(action)
                || Intent.ACTION_TIMEZONE_CHANGED.equals(action)
                || "android.intent.action.QUICKBOOT_POWERON".equals(action)
                || "android.intent.action.LOCKED_BOOT_COMPLETED".equals(action)) {
            try {
                AdhanScheduler.reschedule(context);
            } catch (Exception error) {
                // لا شيء: سيُعاد الجدول عند فتح التطبيق
            }
        }
    }
}
