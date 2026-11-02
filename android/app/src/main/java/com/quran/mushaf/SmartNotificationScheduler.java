package com.quran.mushaf;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

final class SmartNotificationScheduler {
    static final String PREFS = "siraj_smart_notification";
    static final String ENABLED = "enabled";
    static final String AT = "at";
    static final String TITLE = "title";
    static final String BODY = "body";
    static final String SERVICE = "service";
    static final String SUGGESTION_ID = "suggestion_id";
    static final String TARGET = "target";
    static final String QUIET_START = "quiet_start";
    static final String QUIET_END = "quiet_end";
    static final String SLEEP_START = "sleep_start";
    static final String SLEEP_END = "sleep_end";

    private static final int REQUEST_CODE = 14201;

    private SmartNotificationScheduler() {}

    static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static void saveAndSchedule(
            Context context,
            long at,
            String title,
            String body,
            String service,
            String suggestionId,
            String target,
            String quietStart,
            String quietEnd,
            String sleepStart,
            String sleepEnd
    ) {
        preferences(context).edit()
                .putBoolean(ENABLED, true)
                .putLong(AT, at)
                .putString(TITLE, title)
                .putString(BODY, body)
                .putString(SERVICE, service)
                .putString(SUGGESTION_ID, suggestionId)
                .putString(TARGET, target)
                .putString(QUIET_START, quietStart)
                .putString(QUIET_END, quietEnd)
                .putString(SLEEP_START, sleepStart)
                .putString(SLEEP_END, sleepEnd)
                .apply();
        scheduleAt(context, at);
    }

    static void scheduleAt(Context context, long at) {
        SharedPreferences prefs = preferences(context);
        if (!prefs.getBoolean(ENABLED, false)) return;
        long safeAt = Math.max(System.currentTimeMillis() + 5_000L, at);
        prefs.edit().putLong(AT, safeAt).apply();
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null) return;
        PendingIntent pending = pendingIntent(context);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            // Inexact while-idle needs no restricted exact-alarm permission.
            alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, safeAt, pending);
        } else {
            alarms.set(AlarmManager.RTC_WAKEUP, safeAt, pending);
        }
    }

    static void restore(Context context) {
        SharedPreferences prefs = preferences(context);
        if (!prefs.getBoolean(ENABLED, false)) return;
        long at = prefs.getLong(AT, 0L);
        scheduleAt(context, at > System.currentTimeMillis() ? at : System.currentTimeMillis() + 60_000L);
    }

    static void snooze(Context context, long delayMillis) {
        SharedPreferences prefs = preferences(context);
        if (!prefs.contains(SUGGESTION_ID)) return;
        prefs.edit().putBoolean(ENABLED, true).apply();
        scheduleAt(context, System.currentTimeMillis() + Math.max(30 * 60_000L, delayMillis));
    }

    static void markDelivered(Context context) {
        preferences(context).edit().putBoolean(ENABLED, false).apply();
    }

    static void cancel(Context context) {
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms != null) alarms.cancel(pendingIntent(context));
        preferences(context).edit().putBoolean(ENABLED, false).apply();
    }

    private static PendingIntent pendingIntent(Context context) {
        Intent intent = new Intent(context, SmartNotificationReceiver.class);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getBroadcast(context, REQUEST_CODE, intent, flags);
    }
}
