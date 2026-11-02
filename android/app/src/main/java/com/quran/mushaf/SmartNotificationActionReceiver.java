package com.quran.mushaf;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import androidx.core.app.NotificationManagerCompat;

public class SmartNotificationActionReceiver extends BroadcastReceiver {
    static final String ACTION_SNOOZE = "com.quran.mushaf.SMART_SNOOZE";
    static final String ACTION_DISMISS = "com.quran.mushaf.SMART_DISMISS";
    private static final long SNOOZE_MILLIS = 2L * 60L * 60L * 1000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        String service = intent.getStringExtra(SmartFeedbackStore.EXTRA_SERVICE);
        String suggestionId = intent.getStringExtra(SmartFeedbackStore.EXTRA_ID);
        String target = intent.getStringExtra(SmartFeedbackStore.EXTRA_TARGET);
        if (ACTION_SNOOZE.equals(action)) {
            SmartFeedbackStore.record(context, "snooze", service, suggestionId, target);
            SmartNotificationScheduler.snooze(context, SNOOZE_MILLIS);
        } else if (ACTION_DISMISS.equals(action)) {
            SmartFeedbackStore.record(context, "dismiss", service, suggestionId, target);
        } else {
            return;
        }
        NotificationManagerCompat.from(context).cancel(SmartNotificationReceiver.NOTIFICATION_ID);
    }
}
