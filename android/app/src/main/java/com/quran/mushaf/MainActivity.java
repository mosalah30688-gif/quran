package com.quran.mushaf;

import android.content.Intent;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(FolderPickerPlugin.class);
        registerPlugin(ApkUpdaterPlugin.class);
        registerPlugin(TafsirStorePlugin.class);
        registerPlugin(ReminderPlugin.class);
        registerPlugin(SmartDevicePlugin.class);
        registerPlugin(QuranAudioPlugin.class);
        registerPlugin(AdhanPlugin.class);
        super.onCreate(savedInstanceState);
        SmartFeedbackStore.captureOpenIntent(this, getIntent());
    }

    @Override
    public void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        SmartFeedbackStore.captureOpenIntent(this, intent);
    }
}
