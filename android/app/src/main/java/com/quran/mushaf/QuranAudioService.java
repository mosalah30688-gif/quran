package com.quran.mushaf;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.support.v4.media.MediaMetadataCompat;
import android.support.v4.media.session.MediaSessionCompat;
import android.support.v4.media.session.PlaybackStateCompat;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import androidx.core.app.NotificationCompat;

import java.util.ArrayList;

/**
 * خدمة أمامية (foreground service) تتولى تشغيل التلاوة بنفسها خارج طبقة الويب،
 * فيستمر الصوت بعد خروج المستخدم من التطبيق أو إغلاق واجهته، مع إشعار تحكّم
 * وأزرار (تشغيل/إيقاف/التالي/السابق) وشاشة قفل.
 */
public class QuranAudioService extends Service implements MediaPlayer.OnCompletionListener {

    public static final String ACTION_START = "com.quran.mushaf.audio.START";
    public static final String ACTION_PLAY = "com.quran.mushaf.audio.PLAY";
    public static final String ACTION_PAUSE = "com.quran.mushaf.audio.PAUSE";
    public static final String ACTION_NEXT = "com.quran.mushaf.audio.NEXT";
    public static final String ACTION_PREV = "com.quran.mushaf.audio.PREV";
    public static final String ACTION_STOP = "com.quran.mushaf.audio.STOP";

    private static final String CHANNEL_ID = "quran_audio";
    private static final int NOTIFICATION_ID = 4811;

    private static QuranAudioService instance;

    private MediaPlayer player;
    private MediaSessionCompat session;
    private PowerManager.WakeLock wakeLock;
    private final ArrayList<String> urls = new ArrayList<>();
    private final ArrayList<String> titles = new ArrayList<>();
    private int index = 0;
    private boolean prepared = false;

    public static QuranAudioService get() {
        return instance;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        createChannel();
        setupSession();
        setupWakeLock();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            stopPlayback(true);
            return START_NOT_STICKY;
        }
        if (ACTION_PAUSE.equals(action)) {
            pause();
            return START_STICKY;
        }
        if (ACTION_PLAY.equals(action)) {
            resume();
            return START_STICKY;
        }
        if (ACTION_NEXT.equals(action)) {
            skip(1);
            return START_STICKY;
        }
        if (ACTION_PREV.equals(action)) {
            skip(-1);
            return START_STICKY;
        }
        if (ACTION_START.equals(action) && intent != null) {
            ArrayList<String> incomingUrls = intent.getStringArrayListExtra("urls");
            ArrayList<String> incomingTitles = intent.getStringArrayListExtra("titles");
            int startAt = intent.getIntExtra("index", 0);
            float rate = intent.getFloatExtra("rate", 1f);
            startForegroundSafely(buildNotification());
            start(incomingUrls, incomingTitles, startAt, rate);
            return START_STICKY;
        }
        startForegroundSafely(buildNotification());
        return START_STICKY;
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "التلاوة", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("تشغيل التلاوة في الخلفية");
        channel.setShowBadge(false);
        manager.createNotificationChannel(channel);
    }

    private void setupSession() {
        session = new MediaSessionCompat(this, "SirajQuran");
        session.setCallback(new MediaSessionCompat.Callback() {
            @Override
            public void onPlay() {
                resume();
            }

            @Override
            public void onPause() {
                pause();
            }

            @Override
            public void onSkipToNext() {
                skip(1);
            }

            @Override
            public void onSkipToPrevious() {
                skip(-1);
            }

            @Override
            public void onStop() {
                stopPlayback(true);
            }
        });
        session.setActive(true);
    }

    private void setupWakeLock() {
        PowerManager power = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (power == null) return;
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "siraj:quran-audio");
        wakeLock.setReferenceCounted(false);
    }

    public void start(ArrayList<String> incomingUrls, ArrayList<String> incomingTitles, int startAt, float rate) {
        urls.clear();
        titles.clear();
        if (incomingUrls != null) urls.addAll(incomingUrls);
        if (incomingTitles != null) titles.addAll(incomingTitles);
        if (urls.isEmpty()) {
            stopPlayback(true);
            return;
        }
        index = Math.max(0, Math.min(startAt, urls.size() - 1));
        playCurrent(rate);
    }

    private void playCurrent(float rate) {
        releasePlayer();
        try {
            player = new MediaPlayer();
            player.setAudioAttributes(new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build());
            player.setDataSource(urls.get(index));
            player.setOnCompletionListener(this);
            player.setOnPreparedListener(mp -> {
                prepared = true;
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                    try {
                        mp.setPlaybackParams(mp.getPlaybackParams().setSpeed(rate <= 0 ? 1f : rate));
                    } catch (Exception ignored) {
                        // بعض الأجهزة لا تدعم تغيير السرعة؛ نكمل بالسرعة الطبيعية
                    }
                }
                mp.start();
                acquireWake();
                updateNotification();
                updateSession(true);
                QuranAudioPlugin.emit("state", stateJson());
            });
            player.setOnErrorListener((mp, what, extra) -> {
                QuranAudioPlugin.emit("error", stateJson());
                skip(1);
                return true;
            });
            player.prepareAsync();
        } catch (Exception error) {
            QuranAudioPlugin.emit("error", stateJson());
        }
    }

    public void pause() {
        if (player != null && player.isPlaying()) player.pause();
        releaseWake();
        updateNotification();
        updateSession(false);
        QuranAudioPlugin.emit("state", stateJson());
    }

    public void resume() {
        if (player != null && prepared) {
            player.start();
            acquireWake();
            updateNotification();
            updateSession(true);
            QuranAudioPlugin.emit("state", stateJson());
        }
    }

    public void skip(int delta) {
        int next = index + delta;
        if (next < 0 || next >= urls.size()) {
            if (next >= urls.size()) stopPlayback(true);
            return;
        }
        index = next;
        playCurrent(currentRate());
    }

    public void stopPlayback(boolean fromUser) {
        releasePlayer();
        releaseWake();
        if (session != null) {
            session.setPlaybackState(new PlaybackStateCompat.Builder()
                    .setState(PlaybackStateCompat.STATE_STOPPED, PlaybackStateCompat.PLAYBACK_POSITION_UNKNOWN, 1f)
                    .build());
        }
        QuranAudioPlugin.emit("stopped", stateJson());
        stopForeground(true);
        stopSelf();
    }

    private float currentRate() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            try {
                if (player != null) return player.getPlaybackParams().getSpeed();
            } catch (Exception ignored) {
            }
        }
        return 1f;
    }

    @Override
    public void onCompletion(MediaPlayer mp) {
        if (index + 1 < urls.size()) {
            index += 1;
            playCurrent(currentRate());
        } else {
            stopPlayback(false);
        }
    }

    private void acquireWake() {
        try {
            if (wakeLock != null && !wakeLock.isHeld()) wakeLock.acquire(6 * 60 * 60 * 1000L);
        } catch (Exception ignored) {
        }
    }

    private void releaseWake() {
        try {
            if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        } catch (Exception ignored) {
        }
    }

    private void releasePlayer() {
        prepared = false;
        if (player == null) return;
        try {
            if (player.isPlaying()) player.stop();
        } catch (Exception ignored) {
        }
        try {
            player.release();
        } catch (Exception ignored) {
        }
        player = null;
    }

    private void startForegroundSafely(Notification notification) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
        } catch (Exception ignored) {
        }
    }

    private Notification buildNotification() {
        Intent openIntent = new Intent(this, MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        PendingIntent contentIntent = PendingIntent.getActivity(this, 0, openIntent, flags);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle(currentTitle())
                .setContentText("التلاوة شغالة في الخلفية — اضغط للرجوع إلى سراج")
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentIntent(contentIntent)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setShowWhen(false)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC);

        boolean playing = player != null && prepared && player.isPlaying();
        builder.addAction(action(playing ? ACTION_PAUSE : ACTION_PLAY,
                playing ? "إيقاف" : "تشغيل", playing ? 1 : 2));
        builder.addAction(action(ACTION_PREV, "السابق", 3));
        builder.addAction(action(ACTION_NEXT, "التالي", 4));

        androidx.media.app.NotificationCompat.MediaStyle style =
                new androidx.media.app.NotificationCompat.MediaStyle()
                        .setShowActionsInCompactView(0, 1)
                        .setMediaSession(session == null ? null : session.getSessionToken());
        builder.setStyle(style);
        return builder.build();
    }

    private NotificationCompat.Action action(String intentAction, String title, int requestCode) {
        Intent intent = new Intent(this, QuranAudioService.class).setAction(intentAction);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        PendingIntent pending = PendingIntent.getService(this, requestCode, intent, flags);
        return new NotificationCompat.Action(0, title, pending);
    }

    private void updateNotification() {
        try {
            NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) manager.notify(NOTIFICATION_ID, buildNotification());
        } catch (Exception ignored) {
        }
    }

    private void updateSession(boolean playing) {
        if (session == null) return;
        PlaybackStateCompat.Builder state = new PlaybackStateCompat.Builder()
                .setActions(PlaybackStateCompat.ACTION_PLAY | PlaybackStateCompat.ACTION_PAUSE
                        | PlaybackStateCompat.ACTION_PLAY_PAUSE | PlaybackStateCompat.ACTION_SKIP_TO_NEXT
                        | PlaybackStateCompat.ACTION_SKIP_TO_PREVIOUS | PlaybackStateCompat.ACTION_STOP)
                .setState(playing ? PlaybackStateCompat.STATE_PLAYING : PlaybackStateCompat.STATE_PAUSED,
                        player == null ? 0 : Math.max(0, player.getCurrentPosition()), 1f);
        session.setPlaybackState(state.build());
        try {
            Bitmap art = BitmapFactory.decodeResource(getResources(), R.mipmap.ic_launcher);
            MediaMetadataCompat.Builder meta = new MediaMetadataCompat.Builder()
                    .putString(MediaMetadataCompat.METADATA_KEY_TITLE, currentTitle())
                    .putString(MediaMetadataCompat.METADATA_KEY_ARTIST, "سراج — القرآن الكريم");
            if (art != null) meta.putBitmap(MediaMetadataCompat.METADATA_KEY_ALBUM_ART, art);
            session.setMetadata(meta.build());
        } catch (Exception ignored) {
        }
        session.setActive(true);
    }

    private String currentTitle() {
        if (index >= 0 && index < titles.size() && titles.get(index) != null && !titles.get(index).isEmpty()) {
            return titles.get(index);
        }
        return "القرآن الكريم";
    }

    public String stateJson() {
        boolean playing = player != null && prepared && player.isPlaying();
        int position = player == null ? 0 : Math.max(0, player.getCurrentPosition());
        StringBuilder json = new StringBuilder("{");
        json.append("\"playing\":").append(playing).append(',');
        json.append("\"index\":").append(index).append(',');
        json.append("\"position\":").append(position).append(',');
        json.append("\"title\":\"").append(currentTitle().replace("\"", "'")).append("\",");
        json.append("\"count\":").append(urls.size()).append('}');
        return json.toString();
    }

    @Override
    public void onDestroy() {
        releasePlayer();
        releaseWake();
        if (session != null) {
            session.release();
            session = null;
        }
        instance = null;
        super.onDestroy();
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        // إغلاق التطبيق من قائمة التطبيقات ينهي التلاوة أيضًا: التشغيل في الخلفية يخدم
        // مغادرة التطبيق أو إطفاء الشاشة فقط، وينتهي بانتهاء التطبيق نفسه.
        stopPlayback(false);
        super.onTaskRemoved(rootIntent);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
