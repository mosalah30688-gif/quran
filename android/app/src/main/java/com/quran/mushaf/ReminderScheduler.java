package com.quran.mushaf;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import java.util.Calendar;

final class ReminderScheduler {
    static final String PREFS = "siraj_wird_reminder";
    static final String ENABLED = "enabled";
    static final String HOUR = "hour";
    static final String MINUTE = "minute";
    static final String TITLE = "title";
    static final String BODY = "body";
    private static final int REQUEST_CODE = 14001;

    private ReminderScheduler() {}

    static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static long nextTrigger(int hour, int minute) {
        Calendar now = Calendar.getInstance();
        Calendar next = Calendar.getInstance();
        next.set(Calendar.HOUR_OF_DAY, hour);
        next.set(Calendar.MINUTE, minute);
        next.set(Calendar.SECOND, 0);
        next.set(Calendar.MILLISECOND, 0);
        if (next.getTimeInMillis() <= now.getTimeInMillis()) next.add(Calendar.DAY_OF_YEAR, 1);
        return next.getTimeInMillis();
    }

    static void schedule(Context context) {
        SharedPreferences prefs = preferences(context);
        if (!prefs.getBoolean(ENABLED, false)) return;
        int hour = prefs.getInt(HOUR, 20);
        int minute = prefs.getInt(MINUTE, 0);
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null) return;
        PendingIntent pending = reminderIntent(context);
        long at = nextTrigger(hour, minute);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            // Inexact while-idle avoids the restricted exact-alarm permission and is sufficient for a daily reminder.
            alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pending);
        } else {
            alarms.set(AlarmManager.RTC_WAKEUP, at, pending);
        }
    }

    static void cancel(Context context) {
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms != null) alarms.cancel(reminderIntent(context));
        preferences(context).edit().putBoolean(ENABLED, false).apply();
    }

    private static PendingIntent reminderIntent(Context context) {
        Intent intent = new Intent(context, ReminderReceiver.class);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getBroadcast(context, REQUEST_CODE, intent, flags);
    }
}
