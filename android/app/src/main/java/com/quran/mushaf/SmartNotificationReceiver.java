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

import java.util.TimeZone;

public class SmartNotificationReceiver extends BroadcastReceiver {
    static final String CHANNEL_ID = "siraj_smart";
    static final int NOTIFICATION_ID = 14201;

    @Override
    public void onReceive(Context context, Intent intent) {
        SharedPreferences prefs = SmartNotificationScheduler.preferences(context);
        if (!prefs.getBoolean(SmartNotificationScheduler.ENABLED, false)) return;

        String quietStart = prefs.getString(SmartNotificationScheduler.QUIET_START, "22:30");
        String quietEnd = prefs.getString(SmartNotificationScheduler.QUIET_END, "06:30");
        String sleepStart = prefs.getString(SmartNotificationScheduler.SLEEP_START, "23:00");
        String sleepEnd = prefs.getString(SmartNotificationScheduler.SLEEP_END, "07:00");
        long now = System.currentTimeMillis();
        long allowedAt = SmartTimeWindow.nextAllowedAt(
                now, quietStart, quietEnd, sleepStart, sleepEnd, TimeZone.getDefault());
        if (allowedAt > now + 30_000L) {
            // Native hard gate: even if a stale web plan fires, defer beyond
            // quiet/sleep windows instead of showing the notification.
            SmartNotificationScheduler.scheduleAt(context, allowedAt);
            return;
        }

        String service = prefs.getString(SmartNotificationScheduler.SERVICE, "app");
        String suggestionId = prefs.getString(SmartNotificationScheduler.SUGGESTION_ID, "");
        String target = prefs.getString(SmartNotificationScheduler.TARGET, "");
        String title = prefs.getString(SmartNotificationScheduler.TITLE, "سراج");
        String body = prefs.getString(SmartNotificationScheduler.BODY, "لديك متابعة مناسبة الآن.");

        createChannel(context);
        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) pendingFlags |= PendingIntent.FLAG_IMMUTABLE;

        Intent open = new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP)
                .putExtra(SmartFeedbackStore.EXTRA_SMART, true)
                .putExtra(SmartFeedbackStore.EXTRA_SERVICE, service)
                .putExtra(SmartFeedbackStore.EXTRA_ID, suggestionId)
                .putExtra(SmartFeedbackStore.EXTRA_TARGET, target);
        PendingIntent content = PendingIntent.getActivity(context, 14202, open, pendingFlags);

        Intent snooze = actionIntent(context, SmartNotificationActionReceiver.ACTION_SNOOZE,
                service, suggestionId, target);
        PendingIntent snoozePending = PendingIntent.getBroadcast(context, 14203, snooze, pendingFlags);
        Intent dismiss = actionIntent(context, SmartNotificationActionReceiver.ACTION_DISMISS,
                service, suggestionId, target);
        PendingIntent dismissPending = PendingIntent.getBroadcast(context, 14204, dismiss, pendingFlags);

        NotificationCompat.Builder notification = new NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_stat_siraj)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setContentIntent(content)
                .setDeleteIntent(dismissPending)
                .addAction(R.drawable.ic_stat_siraj, "لاحقًا", snoozePending)
                .setAutoCancel(true)
                .setOnlyAlertOnce(true)
                .setPriority(NotificationCompat.PRIORITY_DEFAULT);

        try {
            NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification.build());
            SmartFeedbackStore.record(context, "shown", service, suggestionId, target);
        } catch (SecurityException ignored) {
            // Android 13 permission can be revoked after an alarm was planned.
        } finally {
            SmartNotificationScheduler.markDelivered(context);
        }
    }

    private static Intent actionIntent(
            Context context,
            String action,
            String service,
            String suggestionId,
            String target
    ) {
        return new Intent(context, SmartNotificationActionReceiver.class)
                .setAction(action)
                .putExtra(SmartFeedbackStore.EXTRA_SERVICE, service)
                .putExtra(SmartFeedbackStore.EXTRA_ID, suggestionId)
                .putExtra(SmartFeedbackStore.EXTRA_TARGET, target);
    }

    private static void createChannel(Context context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "اقتراحات سراج الذكية", NotificationManager.IMPORTANCE_DEFAULT);
        channel.setDescription("اقتراحات اختيارية محلية تراعي النوم وساعات الهدوء");
        manager.createNotificationChannel(channel);
    }
}
