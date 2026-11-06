package com.quran.mushaf;

import android.content.Intent;
import android.os.Build;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.ArrayList;

/**
 * جسر الويب للخدمة الأمامية التي تُشغّل التلاوة خارج طبقة الويب،
 * فيستمر الصوت بعد خروج المستخدم من التطبيق أو إغلاق واجهته.
 */
@CapacitorPlugin(name = "QuranAudio")
public class QuranAudioPlugin extends Plugin {

    private static QuranAudioPlugin instance;

    @Override
    public void load() {
        instance = this;
    }

    static void emit(String event, String stateJson) {
        QuranAudioPlugin plugin = instance;
        if (plugin == null) return;
        JSObject payload = new JSObject();
        payload.put("event", event);
        payload.put("state", stateJson);
        plugin.notifyListeners(event, payload, true);
    }

    @PluginMethod
    public void start(PluginCall call) {
        ArrayList<String> urls = new ArrayList<>();
        ArrayList<String> titles = new ArrayList<>();
        com.getcapacitor.JSObject data = call.getData();
        try {
            org.json.JSONArray items = data.optJSONArray("items");
            if (items != null) {
                for (int i = 0; i < items.length(); i++) {
                    org.json.JSONObject object = items.optJSONObject(i);
                    if (object == null) continue;
                    String url = object.optString("url", "");
                    if (url.isEmpty()) continue;
                    urls.add(url);
                    titles.add(object.optString("title", ""));
                }
            }
        } catch (Exception error) {
            call.reject("invalid items");
            return;
        }
        if (urls.isEmpty()) {
            call.reject("empty playlist");
            return;
        }
        int startIndex = data.optInt("index", 0);
        double rate = data.optDouble("rate", 1d);
        Intent intent = new Intent(getContext(), QuranAudioService.class);
        intent.setAction(QuranAudioService.ACTION_START);
        intent.putStringArrayListExtra("urls", urls);
        intent.putStringArrayListExtra("titles", titles);
        intent.putExtra("index", startIndex);
        intent.putExtra("rate", (float) rate);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getContext().startForegroundService(intent);
        } else {
            getContext().startService(intent);
        }
        JSObject result = new JSObject();
        result.put("started", true);
        result.put("count", urls.size());
        call.resolve(result);
    }

    @PluginMethod
    public void pause(PluginCall call) {
        control(QuranAudioService.ACTION_PAUSE);
        call.resolve();
    }

    @PluginMethod
    public void resume(PluginCall call) {
        control(QuranAudioService.ACTION_PLAY);
        call.resolve();
    }

    @PluginMethod
    public void next(PluginCall call) {
        control(QuranAudioService.ACTION_NEXT);
        call.resolve();
    }

    @PluginMethod
    public void previous(PluginCall call) {
        control(QuranAudioService.ACTION_PREV);
        call.resolve();
    }

    @PluginMethod
    public void stop(PluginCall call) {
        control(QuranAudioService.ACTION_STOP);
        call.resolve();
    }

    @PluginMethod
    public void state(PluginCall call) {
        QuranAudioService service = QuranAudioService.get();
        JSObject result = new JSObject();
        result.put("active", service != null);
        result.put("state", service == null ? "{}" : service.stateJson());
        call.resolve(result);
    }

    private void control(String action) {
        Intent intent = new Intent(getContext(), QuranAudioService.class);
        intent.setAction(action);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getContext().startForegroundService(intent);
        } else {
            getContext().startService(intent);
        }
    }
}
