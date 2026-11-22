package com.quran.mushaf;

import android.app.admin.DeviceAdminReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * مدير جهاز مصغّر بسياسة واحدة فقط: قفل الشاشة (force-lock).
 * وجوده هو ما يسمح للتطبيق بإطفاء الشاشة بنفسه بعد انتهاء الأذان
 * حين يترك المستخدم الهاتف. لا يُمنح أي صلاحية أخرى (لا محو بيانات ولا كلمات مرور).
 */
public class SirajDeviceAdmin extends DeviceAdminReceiver {

    static String label(Context context) {
        return context.getString(R.string.siraj_device_admin_label);
    }

    @Override
    public CharSequence onDisableRequested(Context context, Intent intent) {
        return context.getString(R.string.siraj_device_admin_disable_warning);
    }

    @Override
    public void onDisabled(Context context, Intent intent) {
        super.onDisabled(context, intent);
        // الميزة تعود إلى الوضع الآمن: لا إطفاء فوري، وتُترك الشاشة لمهلة النظام.
        SirajScreenGuardPlugin.publishCapabilities(context);
    }

    @Override
    public void onEnabled(Context context, Intent intent) {
        super.onEnabled(context, intent);
        SirajScreenGuardPlugin.publishCapabilities(context);
    }
}
