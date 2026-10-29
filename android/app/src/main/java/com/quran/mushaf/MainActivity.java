package com.quran.mushaf;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(FolderPickerPlugin.class);
        registerPlugin(ApkUpdaterPlugin.class);
        registerPlugin(TafsirStorePlugin.class);
        registerPlugin(ReminderPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
