package com.quran.mushaf;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * جدولة أذان المواقيت على مستوى النظام: تُحفظ المواعيد القادمة (أربعة عشر يومًا)
 * في التخزين المحلي، ويُضبط لكل موعد منبّه دقيق يوقظ الجهاز ولو كان التطبيق مغلقًا.
 * هذا ما يجعل الأذان يُسمع في وقته حتى بعد إغلاق التطبيق أو إعادة تشغيل الهاتف.
 */
final class AdhanScheduler {

    static final String PREFS = "siraj_adhan_background";
    static final String KEY_SCHEDULE = "schedule";
    static final String KEY_SETTINGS = "settings";
    static final String KEY_AUDIO = "audio";
    static final String KEY_COUNT = "count";

    private static final int REQUEST_ADHAN = 21000;
    private static final int REQUEST_IQAMA = 31000;

    private AdhanScheduler() {}

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static AlarmManager alarms(Context context) {
        return (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
    }

    private static int flags() {
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        return flags;
    }

    /** هل يستطيع النظام ضبط منبّهات دقيقة الآن؟ (أندرويد ١٢+ يحتاج إذنًا من المستخدم) */
    static boolean canScheduleExact(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return true;
        AlarmManager manager = alarms(context);
        return manager != null && manager.canScheduleExactAlarms();
    }

    static JSONArray events(Context context) {
        try {
            return new JSONArray(prefs(context).getString(KEY_SCHEDULE, "[]"));
        } catch (Exception error) {
            return new JSONArray();
        }
    }

    static JSONObject settings(Context context) {
        try {
            return new JSONObject(prefs(context).getString(KEY_SETTINGS, "{}"));
        } catch (Exception error) {
            return new JSONObject();
        }
    }

    static void storeSettings(Context context, JSONObject settings) {
        prefs(context).edit().putString(KEY_SETTINGS, settings.toString()).apply();
    }

    /** مسار ملف الأذان المنزَّل على الجهاز (إن وُجد) حتى يعمل الأذان دون إنترنت. */
    static String audioPath(Context context, String id) {
        if (id == null || id.isEmpty()) return "";
        try {
            JSONObject map = new JSONObject(prefs(context).getString(KEY_AUDIO, "{}"));
            return map.optString(id, "");
        } catch (Exception error) {
            return "";
        }
    }

    static void putAudioPath(Context context, String id, String path) {
        if (id == null || id.isEmpty() || path == null || path.isEmpty()) return;
        try {
            JSONObject map = new JSONObject(prefs(context).getString(KEY_AUDIO, "{}"));
            map.put(id, path);
            prefs(context).edit().putString(KEY_AUDIO, map.toString()).apply();
        } catch (Exception error) {
            // تجاهل: يُعاد التنزيل في المرة القادمة
        }
    }

    static void cancelAll(Context context) {
        AlarmManager manager = alarms(context);
        int count = prefs(context).getInt(KEY_COUNT, 0);
        if (manager != null) {
            for (int i = 0; i < count; i++) {
                manager.cancel(adhanIntent(context, i));
                manager.cancel(iqamaIntent(context, i));
            }
        }
        prefs(context).edit().putInt(KEY_COUNT, 0).apply();
    }

    /**
     * يستبدل الجدول كاملًا بجدول جديد. يعيد عدد المواعيد التي ضُبطت فعلًا.
     */
    static int schedule(Context context, JSONArray events, JSONObject settings) {
        AlarmManager manager = alarms(context);
        if (manager == null) return 0;
        cancelAll(context);
        storeSettings(context, settings);

        boolean exact = canScheduleExact(context);
        boolean adhanEnabled = settings.optBoolean("adhanEnabled", true);
        boolean iqamaEnabled = settings.optBoolean("iqamaEnabled", true);
        long now = System.currentTimeMillis();
        int scheduled = 0;

        for (int i = 0; i < events.length(); i++) {
            JSONObject event = events.optJSONObject(i);
            if (event == null) continue;
            long at = event.optLong("at", 0L);
            if (at <= now + 3_000L) continue;
            if (adhanEnabled) {
                setAlarm(manager, exact, at, adhanIntent(context, i));
                scheduled++;
            }
            if (iqamaEnabled) {
                int minutes = event.optInt("iqamaMinutes", 0);
                if (minutes > 0) {
                    long iqamaAt = at + minutes * 60_000L;
                    if (iqamaAt > now + 3_000L) setAlarm(manager, exact, iqamaAt, iqamaIntent(context, i));
                }
            }
        }

        prefs(context).edit().putInt(KEY_COUNT, events.length()).apply();
        prefs(context).edit().putString(KEY_SCHEDULE, events.toString()).apply();
        return scheduled;
    }

    /** يعيد ضبط المنبّهات من الجدول المحفوظ (بعد إعادة تشغيل الهاتف أو تغيير الساعة). */
    static int reschedule(Context context) {
        JSONArray events = events(context);
        if (events.length() == 0) return 0;
        return schedule(context, events, settings(context));
    }

    private static void setAlarm(AlarmManager manager, boolean exact, long at, PendingIntent pending) {
        long safeAt = Math.max(System.currentTimeMillis() + 3_000L, at);
        try {
            if (exact) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    manager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, safeAt, pending);
                } else {
                    manager.setExact(AlarmManager.RTC_WAKEUP, safeAt, pending);
                }
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                // بلا إذن المنبّهات الدقيقة: نستعمل أقرب نافذة يقظة يسمح بها النظام.
                manager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, safeAt, pending);
            } else {
                manager.set(AlarmManager.RTC_WAKEUP, safeAt, pending);
            }
        } catch (SecurityException error) {
            // أندرويد ٦+ يسمح بالتنبيه أثناء نوم الجهاز بدون إذن خاص
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                manager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, safeAt, pending);
            } else {
                manager.set(AlarmManager.RTC_WAKEUP, safeAt, pending);
            }
        }
    }

    private static PendingIntent adhanIntent(Context context, int index) {
        Intent intent = new Intent(context, AdhanReceiver.class);
        intent.setAction(AdhanReceiver.ACTION_ADHAN);
        intent.putExtra("index", index);
        return PendingIntent.getBroadcast(context, REQUEST_ADHAN + index, intent, flags());
    }

    private static PendingIntent iqamaIntent(Context context, int index) {
        Intent intent = new Intent(context, AdhanReceiver.class);
        intent.setAction(AdhanReceiver.ACTION_IQAMA);
        intent.putExtra("index", index);
        return PendingIntent.getBroadcast(context, REQUEST_IQAMA + index, intent, flags());
    }
}
