package com.quran.mushaf;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.support.v4.media.MediaMetadataCompat;
import android.support.v4.media.session.MediaSessionCompat;
import android.support.v4.media.session.PlaybackStateCompat;

import androidx.core.app.NotificationCompat;

import java.io.File;

/**
 * خدمة أمامية تشغّل الأذان بنفسها: من الملف المنزَّل على الجهاز إن وُجد
 * (فيعمل دون إنترنت)، وإلا من الشبكة. تعمل والتطبيق مغلق أو الشاشة مطفأة.
 */
public class AdhanService extends Service implements MediaPlayer.OnCompletionListener, MediaPlayer.OnErrorListener {

    public static final String ACTION_PLAY = "com.quran.mushaf.adhan.PLAY";
    public static final String ACTION_STOP = "com.quran.mushaf.adhan.STOP";

    private static final String CHANNEL_ID = "adhan_playback";
    private static final int NOTIFICATION_ID = 4821;
    private static final long MAX_DURATION_MS = 12 * 60 * 1000L;

    private MediaPlayer player;
    private MediaSessionCompat session;
    private PowerManager.WakeLock wakeLock;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable timeout = new Runnable() {
        @Override
        public void run() {
            stopEverything();
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        setupSession();
        PowerManager power = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (power != null) {
            wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "siraj:adhan");
            wakeLock.setReferenceCounted(false);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            stopEverything();
            return START_NOT_STICKY;
        }
        String prayer = intent == null ? "" : intent.getStringExtra("prayer");
        String label = intent == null ? "" : intent.getStringExtra("label");
        String adhanId = intent == null ? "" : intent.getStringExtra("adhanId");
        String url = intent == null ? "" : intent.getStringExtra("url");

        startForegroundSafely(buildNotification(label.isEmpty() ? "الأذان" : "أذان " + label));
        play(label, adhanId, url);
        return START_NOT_STICKY;
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "الأذان", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("تشغيل الأذان في وقته");
        channel.setShowBadge(false);
        manager.createNotificationChannel(channel);
    }

    private void setupSession() {
        session = new MediaSessionCompat(this, "SirajAdhan");
        session.setCallback(new MediaSessionCompat.Callback() {
            @Override
            public void onStop() {
                stopEverything();
            }
        });
        session.setActive(true);
    }

    private void startForegroundSafely(Notification notification) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification,
                        android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
        } catch (Exception error) {
            // بعض الأنظمة ترفض الإشعار أثناء القيود؛ يبقى الصوت أولى.
        }
    }

    private void play(String label, String adhanId, String url) {
        stopPlayer();
        String path = AdhanScheduler.audioPath(this, adhanId);
        File file = path.isEmpty() ? null : new File(path);
        boolean local = file != null && file.exists() && file.length() > 16_384;
        player = new MediaPlayer();
        player.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .build());
        player.setOnCompletionListener(this);
        player.setOnErrorListener(this);
        try {
            if (local) {
                player.setDataSource(file.getAbsolutePath());
            } else if (url != null && !url.isEmpty()) {
                player.setDataSource(url);
            } else {
                stopEverything();
                return;
            }
            player.prepareAsync();
            player.setOnPreparedListener((mp) -> {
                if (wakeLock != null && !wakeLock.isHeld()) wakeLock.acquire(MAX_DURATION_MS + 60_000L);
                mp.start();
                handler.postDelayed(timeout, MAX_DURATION_MS);
            });
        } catch (Exception error) {
            stopEverything();
            return;
        }
        if (session != null) {
            session.setMetadata(new MediaMetadataCompat.Builder()
                    .putString(MediaMetadataCompat.METADATA_KEY_TITLE, "أذان " + label)
                    .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, "سراج")
                    .build());
            session.setPlaybackState(new PlaybackStateCompat.Builder()
                    .setActions(PlaybackStateCompat.ACTION_STOP)
                    .setState(PlaybackStateCompat.STATE_PLAYING, 0, 1f)
                    .build());
        }
    }

    private Notification buildNotification(String title) {
        Intent open = new Intent(this, MainActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        open.putExtra("siraj_view", "prayer");
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) flags |= PendingIntent.FLAG_IMMUTABLE;
        PendingIntent content = PendingIntent.getActivity(this, 4820, open, flags);

        Intent stop = new Intent(this, AdhanService.class);
        stop.setAction(ACTION_STOP);
        PendingIntent stopPending = PendingIntent.getService(this, 4824, stop, flags);

        NotificationCompat.Action stopAction = new NotificationCompat.Action.Builder(
                android.R.drawable.ic_media_pause, "إيقاف", stopPending).build();

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle(title)
                .setContentText("الأذان يعمل الآن")
                .setContentIntent(content)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setCategory(NotificationCompat.CATEGORY_SERVICE)
                .setOngoing(true)
                .setDeleteIntent(stopPending)
                .addAction(stopAction)
                .setStyle(new androidx.media.app.NotificationCompat.MediaStyle()
                        .setMediaSession(session == null ? null : session.getSessionToken())
                        .setShowActionsInCompactView(0))
                .build();
    }

    private void stopPlayer() {
        handler.removeCallbacks(timeout);
        if (player != null) {
            try {
                if (player.isPlaying()) player.stop();
            } catch (Exception error) {
                // متجاهَل: المشغّل أُفرغ بالفعل
            }
            player.release();
            player = null;
        }
    }

    private void stopEverything() {
        stopPlayer();
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        if (session != null) {
            session.setPlaybackState(new PlaybackStateCompat.Builder()
                    .setState(PlaybackStateCompat.STATE_STOPPED, 0, 1f).build());
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
        stopSelf();
    }

    @Override
    public void onCompletion(MediaPlayer mp) {
        stopEverything();
    }

    @Override
    public boolean onError(MediaPlayer mp, int what, int extra) {
        stopEverything();
        return true;
    }

    @Override
    public void onDestroy() {
        stopPlayer();
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        if (session != null) {
            session.setActive(false);
            session.release();
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
