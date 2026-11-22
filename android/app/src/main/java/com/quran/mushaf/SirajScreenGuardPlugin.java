package com.quran.mushaf;

import android.app.KeyguardManager;
import android.app.admin.DevicePolicyManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.PowerManager;
import android.view.WindowManager;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * جسر «حارس الشاشة»: الطبقة الويب تقرّر متى يترك المستخدم الهاتف (الخوارزمية في prayer-ui.js)،
 * وهذا الجسر ينفّذ القرار بإطفاء الشاشة فعليًا، ويرفع علم إبقاء الشاشة مضاءة عند الحاجة.
 *
 * مسارات التنفيذ بالترتيب:
 *  1) مدير الجهاز (force-lock) ⇒ lockNow() تُطفئ الشاشة فورًا.
 *  2) بلا إذن ⇒ تُرفع أعلام إبقاء الشاشة وتُترك للمهلة التي حدّدها المستخدم في النظام.
 */
@CapacitorPlugin(name = "SirajScreenGuard")
public class SirajScreenGuardPlugin extends Plugin {

    private BroadcastReceiver screenReceiver;

    static ComponentName adminComponent(Context context) {
        return new ComponentName(context, SirajDeviceAdmin.class);
    }

    static boolean adminActive(Context context) {
        DevicePolicyManager dpm =
                (DevicePolicyManager) context.getSystemService(Context.DEVICE_POLICY_SERVICE);
        try {
            return dpm != null && dpm.isAdminActive(adminComponent(context));
        } catch (Exception error) {
            return false;
        }
    }

    static boolean interactive(Context context) {
        PowerManager power = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        if (power == null) return true;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH) {
            return power.isInteractive();
        }
        return power.isScreenOn();
    }

    private static java.lang.ref.WeakReference<SirajScreenGuardPlugin> live;

    /** يُبلّغ الواجهة بتغيّر القدرات (بعد تفعيل/إلغاء مدير الجهاز مثلًا). */
    static void publishCapabilities(Context context) {
        SirajScreenGuardPlugin plugin = live == null ? null : live.get();
        if (plugin == null) return;
        JSObject payload = new JSObject();
        payload.put("admin", adminActive(context));
        plugin.notifyListeners("capabilities", payload, true);
    }

    @Override
    protected void handleOnDestroy() {
        unRegisterScreenReceiver();
        super.handleOnDestroy();
    }

    private void registerScreenReceiver() {
        if (screenReceiver != null) return;
        screenReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String action = intent == null ? null : intent.getAction();
                if (action == null) return;
                JSObject payload = new JSObject();
                payload.put("interactive", Intent.ACTION_SCREEN_ON.equals(action));
                notifyListeners("screen", payload, true);
            }
        };
        IntentFilter filter = new IntentFilter();
        filter.addAction(Intent.ACTION_SCREEN_ON);
        filter.addAction(Intent.ACTION_SCREEN_OFF);
        try {
            getContext().registerReceiver(screenReceiver, filter);
        } catch (Exception error) {
            screenReceiver = null;
        }
    }

    private void unRegisterScreenReceiver() {
        if (screenReceiver == null) return;
        try {
            getContext().unregisterReceiver(screenReceiver);
        } catch (Exception error) {
            // أُزيل مسبقًا
        }
        screenReceiver = null;
    }

    @PluginMethod
    public void capabilities(PluginCall call) {
        Context context = getContext();
        // المستمع يُسجَّل مرة واحدة عند أول استدعاء (لا حاجة لاعتراض دورة حياة النشاط).
        live = new java.lang.ref.WeakReference<>(this);
        registerScreenReceiver();
        JSObject out = new JSObject();
        boolean admin = adminActive(context);
        boolean screenOn = interactive(context);
        out.put("admin", admin);
        out.put("interactive", screenOn);
        out.put("api", Build.VERSION.SDK_INT);
        out.put("lockable", admin);
        // معنى lockable=false: الشاشة تُترك لمهلة النظام بعد رفع أعلام الإبقاء.
        call.resolve(out);
    }

    @PluginMethod
    public void requestAdmin(PluginCall call) {
        Context context = getContext();
        JSObject out = new JSObject();
        if (adminActive(context)) {
            out.put("admin", true);
            out.put("requested", false);
            call.resolve(out);
            return;
        }
        try {
            Intent intent = new Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN);
            intent.putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, adminComponent(context));
            intent.putExtra(DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                    context.getString(R.string.siraj_device_admin_explanation));
            if (getActivity() != null) {
                getActivity().startActivity(intent);
            } else {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(intent);
            }
            out.put("admin", false);
            out.put("requested", true);
            call.resolve(out);
        } catch (Exception error) {
            call.reject("تعذّر فتح شاشة إذن القفل", error);
        }
    }

    @PluginMethod
    public void revokeAdmin(PluginCall call) {
        Context context = getContext();
        DevicePolicyManager dpm =
                (DevicePolicyManager) context.getSystemService(Context.DEVICE_POLICY_SERVICE);
        try {
            if (dpm != null) dpm.removeActiveAdmin(adminComponent(context));
        } catch (Exception error) {
            // غير مفعّل أصلًا
        }
        JSObject out = new JSObject();
        out.put("admin", adminActive(context));
        call.resolve(out);
    }

    /** إطفاء الشاشة الآن. يفشل بأمان حين لا يوجد إذن مدير الجهاز. */
    @PluginMethod
    public void lockNow(PluginCall call) {
        Context context = getContext();
        JSObject out = new JSObject();
        out.put("interactive", interactive(context));
        KeyguardManager keyguard =
                (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        boolean secure = false;
        try {
            secure = keyguard != null && keyguard.isKeyguardSecure();
        } catch (Exception error) {
            secure = false;
        }
        out.put("secure", secure);
        DevicePolicyManager dpm =
                (DevicePolicyManager) context.getSystemService(Context.DEVICE_POLICY_SERVICE);
        boolean admin = adminActive(context);
        if (dpm != null && admin) {
            try {
                clearKeepAwake();
                dpm.lockNow();
                out.put("ok", true);
                out.put("method", "admin");
                call.resolve(out);
                return;
            } catch (Exception error) {
                // نكمل إلى المسار الآمن أدناه
            }
        }
        // بلا إذن: لا يوجد في أندرويد طريق لإطفاء الشاشة قسرًا؛ نرفع أعلام الإبقاء
        // فتقفل الشاشة عند مهلة النظام، ونبلّغ الواجهة بهذا حتى تشرحه للمستخدم.
        clearKeepAwake();
        out.put("ok", false);
        out.put("method", admin ? "admin-failed" : "no-admin");
        call.resolve(out);
    }

    /** تشغيل/إيقاف إبقاء الشاشة مضاءة من ناحية النشاط (مستقل عن wakeLock في الويب). */
    @PluginMethod
    public void setKeepAwake(PluginCall call) {
        Boolean on = call.getBoolean("on");
        if (Boolean.TRUE.equals(on)) keepAwake();
        else clearKeepAwake();
        JSObject out = new JSObject();
        out.put("keepAwake", Boolean.TRUE.equals(on));
        call.resolve(out);
    }

    private void keepAwake() {
        runOnUi(() -> {
            if (getActivity() != null) {
                getActivity().getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            }
        });
    }

    private void clearKeepAwake() {
        runOnUi(() -> {
            if (getActivity() != null) {
                getActivity().getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            }
        });
    }

    private void runOnUi(Runnable action) {
        if (getActivity() == null) return;
        getActivity().runOnUiThread(action);
    }
}
