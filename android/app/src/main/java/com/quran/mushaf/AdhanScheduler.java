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
    /** أكواد المنبّهات المضبوطة حاليًا حتى نلغيها بدقة عند إعادة الجدولة. */
    static final String KEY_CODES = "codes";

    /** نوعا المنبّه: 0 أذان · 1 إقامة · 2 تنبيه ما قبل الأذان. */
    private static final int KIND_ADHAN = 0;
    private static final int KIND_IQAMA = 1;
    private static final int KIND_PRE = 2;
    private static final int REQUEST_BASE = 1000;

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

    /**
     * يلغي كل منبّه مضبوط بدقة (بقائمة الأكواد المحفوظة)، فلا يبقى منبّه يتيم
     * ينطلق بعد إعادة الجدولة ويشغّل أذان صلاة أخرى في غير وقتها.
     */
    static void cancelAll(Context context) {
        AlarmManager manager = alarms(context);
        JSONArray codes = codes(context);
        if (manager != null) {
            for (int i = 0; i < codes.length(); i++) {
                int code = codes.optInt(i, 0);
                if (code != 0) manager.cancel(alarmIntent(context, code));
            }
        }
        prefs(context).edit().putInt(KEY_COUNT, 0).putString(KEY_CODES, "[]").apply();
    }

    private static JSONArray codes(Context context) {
        try {
            return new JSONArray(prefs(context).getString(KEY_CODES, "[]"));
        } catch (Exception error) {
            return new JSONArray();
        }
    }

    /**
     * كود ثابت لكل منبّه مشتق من دقيقته المطلقة ونوعه: لا يتكرر ولا يتغيّر
     * بتغيّر ترتيب الجدول، فلا يصل منبّه إلى موعد صلاة أخرى.
     */
    private static int codeFor(long at, int kind) {
        long minute = Math.max(0L, at / 60_000L);
        return REQUEST_BASE + (int) ((minute & 0x3FFFFFF) * 4 + kind);
    }

    private static int kindOf(int code) {
        return Math.abs(code - REQUEST_BASE) % 4;
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
        int preMinutes = settings.optInt("preMinutes", 0);
        long now = System.currentTimeMillis();
        int scheduled = 0;
        JSONArray codes = new JSONArray();

        for (int i = 0; i < events.length(); i++) {
            JSONObject event = events.optJSONObject(i);
            if (event == null) continue;
            long at = event.optLong("at", 0L);
            if (at <= now + 3_000L) continue;
            if (adhanEnabled) {
                int code = codeFor(at, KIND_ADHAN);
                setAlarm(manager, exact, at, alarmIntent(context, code,
                        AdhanReceiver.ACTION_ADHAN, event, at, at));
                codes.put(code);
                scheduled++;
            }
            // تنبيه ما قبل الأذان: إشعار صوتي «أذان الظهر بعد ١٠ دقائق»
            if (preMinutes > 0) {
                long preAt = at - preMinutes * 60_000L;
                if (preAt > now + 3_000L) {
                    int code = codeFor(preAt, KIND_PRE);
                    setAlarm(manager, exact, preAt, alarmIntent(context, code,
                            AdhanReceiver.ACTION_PRE_ADHAN, event, preAt, at));
                    codes.put(code);
                }
            }
            if (iqamaEnabled) {
                int minutes = event.optInt("iqamaMinutes", 0);
                if (minutes > 0) {
                    long iqamaAt = at + minutes * 60_000L;
                    if (iqamaAt > now + 3_000L) {
                        int code = codeFor(iqamaAt, KIND_IQAMA);
                        setAlarm(manager, exact, iqamaAt, alarmIntent(context, code,
                                AdhanReceiver.ACTION_IQAMA, event, iqamaAt, at));
                        codes.put(code);
                    }
                }
            }
        }

        prefs(context).edit()
                .putInt(KEY_COUNT, events.length())
                .putString(KEY_CODES, codes.toString())
                .putString(KEY_SCHEDULE, events.toString())
                .apply();
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

    /** منبّه يحمل بياناته كاملة (الصلاة والوقت والصوت) فلا يقرأ الجدول وقت الانطلاق. */
    private static PendingIntent alarmIntent(Context context, int code, String action,
                                             JSONObject event, long fireAt, long prayerAt) {
        Intent intent = new Intent(context, AdhanReceiver.class);
        intent.setAction(action);
        intent.putExtra("fireAt", fireAt);
        intent.putExtra("at", prayerAt);
        intent.putExtra("prayer", event.optString("prayer", ""));
        intent.putExtra("label", event.optString("label", ""));
        intent.putExtra("adhanId", event.optString("adhanId", ""));
        intent.putExtra("url", event.optString("url", ""));
        intent.putExtra("iqamaMinutes", event.optInt("iqamaMinutes", 0));
        intent.putExtra("preMinutes", event.optInt("preMinutes", 0));
        return PendingIntent.getBroadcast(context, code, intent, flags());
    }

    /** نفس الـ PendingIntent بالكود وحده — يكفي للإلغاء (المحتوى لا يدخل في المطابقة). */
    private static PendingIntent alarmIntent(Context context, int code) {
        int kind = kindOf(code);
        String action = kind == KIND_IQAMA ? AdhanReceiver.ACTION_IQAMA
                : kind == KIND_PRE ? AdhanReceiver.ACTION_PRE_ADHAN
                : AdhanReceiver.ACTION_ADHAN;
        Intent intent = new Intent(context, AdhanReceiver.class);
        intent.setAction(action);
        return PendingIntent.getBroadcast(context, code, intent, flags());
    }
}
