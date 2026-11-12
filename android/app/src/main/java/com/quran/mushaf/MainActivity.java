package com.quran.mushaf;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    /** طلب فتح شاشة الأذان القادم من المنبّه في الخلفية. */
    private static volatile AdhanOpenRequest pendingAdhan = null;

    public static class AdhanOpenRequest {
        public final String prayer;
        public final String label;
        public final String adhanId;
        AdhanOpenRequest(String prayer, String label, String adhanId) {
            this.prayer = prayer;
            this.label = label;
            this.adhanId = adhanId;
        }
    }

    static void setPendingAdhan(String prayer, String label, String adhanId) {
        pendingAdhan = new AdhanOpenRequest(prayer, label, adhanId);
    }

    /** الواجهة تسحب الطلب مرة واحدة عند عودتها إلى المقدمة. */
    public static AdhanOpenRequest takePendingAdhan() {
        AdhanOpenRequest request = pendingAdhan;
        pendingAdhan = null;
        return request;
    }
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(FolderPickerPlugin.class);
        registerPlugin(ApkUpdaterPlugin.class);
        registerPlugin(TafsirStorePlugin.class);
        registerPlugin(ReminderPlugin.class);
        registerPlugin(SmartDevicePlugin.class);
        registerPlugin(QuranAudioPlugin.class);
        registerPlugin(AdhanPlugin.class);
        registerPlugin(SirajSensorsPlugin.class);
        super.onCreate(savedInstanceState);
        SmartFeedbackStore.captureOpenIntent(this, getIntent());
        applyAdhanWindowFlags(getIntent());
    }

    /** عند وصول منبّه الأذان: أظهر النشاط فوق قفل الشاشة وأيقظها. */
    private void applyAdhanWindowFlags(Intent intent) {
        if (intent == null) return;
        boolean isAdhan = intent.getBooleanExtra("siraj_open_adhan", false)
                || "adhan".equals(intent.getStringExtra("siraj_view"));
        if (!isAdhan) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | android.view.WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                    | android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                android.app.KeyguardManager keyguard =
                        (android.app.KeyguardManager) getSystemService(android.content.Context.KEYGUARD_SERVICE);
                if (keyguard != null) keyguard.requestDismissKeyguard(this, null);
            } catch (Exception ignored) {
                // بعض الأجهزة لا تسمح بالإخفاء التلقائي، ويبقى النشاط ظاهرًا فوق القفل
            }
        }
        setPendingAdhan(intent.getStringExtra("siraj_prayer"),
                intent.getStringExtra("siraj_prayer_label"),
                intent.getStringExtra("siraj_adhan_id"));
    }

    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        SmartFeedbackStore.captureOpenIntent(this, intent);
        applyAdhanWindowFlags(intent);
    }
}
