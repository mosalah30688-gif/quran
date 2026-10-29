package com.quran.mushaf;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

public class ReminderReceiver extends BroadcastReceiver {
    private static final String CHANNEL_ID = "siraj_wird";
    private static final int NOTIFICATION_ID = 14001;

    @Override
    public void onReceive(Context context, Intent intent) {
        SharedPreferences prefs = ReminderScheduler.preferences(context);
        if (!prefs.getBoolean(ReminderScheduler.ENABLED, false)) return;
        createChannel(context);
        Intent open = new Intent(context, MainActivity.class);
        open.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        PendingIntent content = PendingIntent.getActivity(context, 14002, open, pendingFlags);
        String title = prefs.getString(ReminderScheduler.TITLE, "سراج — ورد القرآن");
        String body = prefs.getString(ReminderScheduler.BODY, "موعد وردك اليوم. اقرأ ما تيسر دون إلزام.");
        NotificationCompat.Builder notification = new NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_stat_siraj)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setContentIntent(content)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT);
        try {
            NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification.build());
        } catch (SecurityException ignored) {
            // The user may revoke Android 13 notification permission after scheduling.
        }
        ReminderScheduler.schedule(context);
    }

    private void createChannel(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "ورد القرآن", NotificationManager.IMPORTANCE_DEFAULT);
        channel.setDescription("تذكير يومي اختياري بورد القرآن");
        manager.createNotificationChannel(channel);
    }
}
