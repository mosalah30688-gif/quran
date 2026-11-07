package com.quran.mushaf;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * يستقبل منبّه الوقت فيشغّل الأذان من خدمة أمامية (فيعمل والتطبيق مغلق)،
 * أو يرفع تنبيه الإقامة بعد الأذان بالمدة التي اختارها المستخدم.
 */
public class AdhanReceiver extends BroadcastReceiver {

    public static final String ACTION_ADHAN = "com.quran.mushaf.adhan.ADHAN";
    public static final String ACTION_IQAMA = "com.quran.mushaf.adhan.IQAMA";

    static final String CHANNEL_IQAMA = "adhan_iqama";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        int index = intent.getIntExtra("index", -1);
        if (index < 0) return;

        JSONObject event = eventAt(context, index);
        if (event == null) return;

        if (ACTION_ADHAN.equals(action)) {
            startAdhan(context, event);
        } else if (ACTION_IQAMA.equals(action)) {
            notifyIqama(context, event);
        }
    }

    private static JSONObject eventAt(Context context, int index) {
        JSONArray events = AdhanScheduler.events(context);
        return events.optJSONObject(index);
    }

    private static void startAdhan(Context context, JSONObject event) {
        Intent service = new Intent(context, AdhanService.class);
        service.setAction(AdhanService.ACTION_PLAY);
        service.putExtra("prayer", event.optString("prayer", ""));
        service.putExtra("label", event.optString("label", ""));
        service.putExtra("adhanId", event.optString("adhanId", ""));
        service.putExtra("url", event.optString("url", ""));
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ContextCompat.startForegroundService(context, service);
            } else {
                context.startService(service);
            }
        } catch (Exception error) {
            // إذا منع النظام بدء الخدمة من الخلفية نرفع تنبيهًا صوتيًا بدلًا منها.
            notifyFallback(context, event);
        }
    }

    private static void notifyIqama(Context context, JSONObject event) {
        String label = event.optString("label", "");
        if (label.isEmpty()) label = event.optString("prayer", "");
        post(context, CHANNEL_IQAMA, 4822,
                "إقامة صلاة " + label,
                "حان الآن وقت الإقامة، أقيمت الصلاة تقبّل الله منك.",
                event.optString("prayer", ""));
    }

    private static void notifyFallback(Context context, JSONObject event) {
        String label = event.optString("label", "");
        if (label.isEmpty()) label = event.optString("prayer", "");
        post(context, CHANNEL_IQAMA, 4823,
                "حان الآن وقت صلاة " + label,
                "افتح سراج لتشغيل الأذان.",
                event.optString("prayer", ""));
    }

    private static void post(Context context, String channelId, int id,
                             String title, String body, String prayer) {
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    channelId, "الإقامة والأذان", NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("تنبيه الإقامة بعد الأذان وتنبيه المواقيت");
            channel.enableVibration(true);
            manager.createNotificationChannel(channel);
        }
        Intent open = new Intent(context, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        open.putExtra("siraj_view", "prayer");
        open.putExtra("siraj_prayer", prayer);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        PendingIntent pending = PendingIntent.getActivity(context, id, open, flags);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, channelId)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setAutoCancel(true)
                .setDefaults(NotificationCompat.DEFAULT_SOUND | NotificationCompat.DEFAULT_VIBRATE)
                .setContentIntent(pending);
        try {
            manager.notify(id, builder.build());
        } catch (SecurityException error) {
            // تنبيهات التطبيق متوقفة من إعدادات النظام
        }
    }
}
