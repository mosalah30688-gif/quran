package com.quran.mushaf;

import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.Build;
import android.os.PowerManager;

import androidx.core.app.NotificationManagerCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import org.json.JSONArray;

import java.util.TimeZone;

@CapacitorPlugin(
        name = "SmartDevice",
        permissions = @Permission(alias = "notifications", strings = { "android.permission.POST_NOTIFICATIONS" })
)
public class SmartDevicePlugin extends Plugin {
    private static final long MAX_SCHEDULE_AHEAD = 48L * 60L * 60L * 1000L;

    @PluginMethod
    public void getSignals(PluginCall call) {
        Context context = getContext();
        PowerManager power = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        KeyguardManager keyguard = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        Intent battery = context.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        int level = battery == null ? -1 : battery.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = battery == null ? -1 : battery.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        int status = battery == null ? -1 : battery.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
        boolean charging = status == BatteryManager.BATTERY_STATUS_CHARGING
                || status == BatteryManager.BATTERY_STATUS_FULL;
        int percent = level >= 0 && scale > 0 ? Math.round(level * 100f / scale) : -1;

        JSObject result = new JSObject();
        result.put("screenInteractive", power == null || power.isInteractive());
        result.put("deviceLocked", keyguard != null && keyguard.isKeyguardLocked());
        result.put("powerSave", power != null && power.isPowerSaveMode());
        result.put("charging", charging);
        result.put("batteryPercent", percent);
        result.put("notificationsEnabled", NotificationManagerCompat.from(context).areNotificationsEnabled());
        result.put("timezoneOffsetMinutes", TimeZone.getDefault().getOffset(System.currentTimeMillis()) / 60_000);
        result.put("now", System.currentTimeMillis());
        call.resolve(result);
    }

    @PluginMethod
    public void requestNotifications(PluginCall call) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && getPermissionState("notifications") != PermissionState.GRANTED) {
            requestPermissionForAlias("notifications", call, "notificationPermissionResult");
            return;
        }
        resolvePermission(call);
    }

    @PermissionCallback
    private void notificationPermissionResult(PluginCall call) {
        resolvePermission(call);
    }

    private void resolvePermission(PluginCall call) {
        boolean granted = (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                || getPermissionState("notifications") == PermissionState.GRANTED)
                && NotificationManagerCompat.from(getContext()).areNotificationsEnabled();
        JSObject result = new JSObject();
        result.put("granted", granted);
        call.resolve(result);
    }

    @PluginMethod
    public void schedule(PluginCall call) {
        Long atValue = call.getLong("at");
        long now = System.currentTimeMillis();
        long at = atValue == null ? 0L : atValue;
        if (at < now + 60_000L || at > now + MAX_SCHEDULE_AHEAD) {
            call.reject("invalid schedule time");
            return;
        }
        if (!validClock(call.getString("quietStart", "22:30"))
                || !validClock(call.getString("quietEnd", "06:30"))
                || !validClock(call.getString("sleepStart", "23:00"))
                || !validClock(call.getString("sleepEnd", "07:00"))) {
            call.reject("invalid safety window");
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && getPermissionState("notifications") != PermissionState.GRANTED) {
            requestPermissionForAlias("notifications", call, "schedulePermissionResult");
            return;
        }
        finishSchedule(call);
    }

    @PermissionCallback
    private void schedulePermissionResult(PluginCall call) {
        if (getPermissionState("notifications") != PermissionState.GRANTED) {
            call.reject("notification permission denied");
            return;
        }
        finishSchedule(call);
    }

    private void finishSchedule(PluginCall call) {
        if (!NotificationManagerCompat.from(getContext()).areNotificationsEnabled()) {
            call.reject("notifications disabled");
            return;
        }
        Long atValue = call.getLong("at");
        long at = atValue == null ? 0L : atValue;
        String title = bounded(call.getString("title", "سراج"), 80, "سراج");
        String body = bounded(call.getString("body", "لديك متابعة مناسبة الآن."), 240,
                "لديك متابعة مناسبة الآن.");
        String service = token(call.getString("service", "app"), "app");
        String suggestionId = identifier(call.getString("suggestionId", ""));
        String target = identifier(call.getString("target", ""));
        String quietStart = call.getString("quietStart", "22:30");
        String quietEnd = call.getString("quietEnd", "06:30");
        String sleepStart = call.getString("sleepStart", "23:00");
        String sleepEnd = call.getString("sleepEnd", "07:00");
        SmartNotificationScheduler.saveAndSchedule(getContext(), at, title, body, service,
                suggestionId, target, quietStart, quietEnd, sleepStart, sleepEnd);
        JSObject result = new JSObject();
        result.put("scheduled", true);
        result.put("exact", false);
        result.put("nextAt", at);
        call.resolve(result);
    }

    @PluginMethod
    public void cancel(PluginCall call) {
        SmartNotificationScheduler.cancel(getContext());
        call.resolve();
    }

    @PluginMethod
    public void status(PluginCall call) {
        boolean enabled = SmartNotificationScheduler.preferences(getContext())
                .getBoolean(SmartNotificationScheduler.ENABLED, false);
        long nextAt = SmartNotificationScheduler.preferences(getContext())
                .getLong(SmartNotificationScheduler.AT, 0L);
        JSObject result = new JSObject();
        result.put("supported", true);
        result.put("enabled", enabled);
        result.put("nextAt", nextAt);
        result.put("permission", (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                || getPermissionState("notifications") == PermissionState.GRANTED)
                && NotificationManagerCompat.from(getContext()).areNotificationsEnabled());
        call.resolve(result);
    }

    @PluginMethod
    public void consumeFeedback(PluginCall call) {
        JSONArray events = SmartFeedbackStore.consume(getContext());
        JSObject result = new JSObject();
        result.put("events", events);
        call.resolve(result);
    }

    private static boolean validClock(String value) {
        return SmartTimeWindow.parseMinute(value, -1) >= 0;
    }

    private static String bounded(String value, int max, String fallback) {
        if (value == null) return fallback;
        String text = value.trim();
        return text.isEmpty() ? fallback : text.substring(0, Math.min(max, text.length()));
    }

    private static String token(String value, String fallback) {
        String text = value == null ? "" : value.trim().toLowerCase();
        return text.matches("^[a-z][a-z0-9_-]{0,47}$") ? text : fallback;
    }

    private static String identifier(String value) {
        String text = value == null ? "" : value.trim();
        return text.matches("^[A-Za-z0-9_.:-]{0,64}$") ? text : "";
    }
}
