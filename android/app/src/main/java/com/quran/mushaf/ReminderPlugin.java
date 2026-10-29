package com.quran.mushaf;

import android.os.Build;

import androidx.core.app.NotificationManagerCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

@CapacitorPlugin(
        name = "Reminder",
        permissions = @Permission(alias = "notifications", strings = { "android.permission.POST_NOTIFICATIONS" })
)
public class ReminderPlugin extends Plugin {

    @PluginMethod
    public void schedule(PluginCall call) {
        Integer hourValue = call.getInt("hour");
        Integer minuteValue = call.getInt("minute");
        int hour = hourValue == null ? -1 : hourValue;
        int minute = minuteValue == null ? -1 : minuteValue;
        if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
            call.reject("invalid time");
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && getPermissionState("notifications") != PermissionState.GRANTED) {
            requestPermissionForAlias("notifications", call, "notificationPermissionResult");
            return;
        }
        finishSchedule(call);
    }

    @PermissionCallback
    private void notificationPermissionResult(PluginCall call) {
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
        Integer hourValue = call.getInt("hour");
        Integer minuteValue = call.getInt("minute");
        int hour = hourValue == null ? 20 : hourValue;
        int minute = minuteValue == null ? 0 : minuteValue;
        String title = call.getString("title", "سراج — ورد القرآن");
        String body = call.getString("body", "موعد وردك اليوم. اقرأ ما تيسر دون إلزام.");
        ReminderScheduler.preferences(getContext()).edit()
                .putBoolean(ReminderScheduler.ENABLED, true)
                .putInt(ReminderScheduler.HOUR, hour)
                .putInt(ReminderScheduler.MINUTE, minute)
                .putString(ReminderScheduler.TITLE, title)
                .putString(ReminderScheduler.BODY, body)
                .apply();
        ReminderScheduler.schedule(getContext());
        JSObject result = new JSObject();
        result.put("scheduled", true);
        result.put("exact", false);
        result.put("nextAt", ReminderScheduler.nextTrigger(hour, minute));
        call.resolve(result);
    }

    @PluginMethod
    public void cancel(PluginCall call) {
        ReminderScheduler.cancel(getContext());
        call.resolve();
    }

    @PluginMethod
    public void status(PluginCall call) {
        boolean enabled = ReminderScheduler.preferences(getContext())
                .getBoolean(ReminderScheduler.ENABLED, false);
        JSObject result = new JSObject();
        result.put("enabled", enabled);
        result.put("permission", Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                || getPermissionState("notifications") == PermissionState.GRANTED);
        call.resolve(result);
    }
}
