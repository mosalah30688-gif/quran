package com.quran.mushaf;

import android.content.Intent;
import android.os.Build;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * جسر الواجهة إلى جدولة الأذان على مستوى النظام:
 * الواجهة تحسب المواقيت القادمة (أربعة عشر يومًا) وتمرّرها مرة واحدة،
 * فيتولى أندرويد إيقاظ التطبيق وتشغيل الأذان في وقته ولو كان مغلقًا.
 */
@CapacitorPlugin(name = "AdhanBackground")
public class AdhanPlugin extends Plugin {

    @PluginMethod
    public void configure(PluginCall call) {
        try {
            JSObject data = call.getData();
            JSONArray events = data.optJSONArray("events");
            JSONObject settings = data.optJSONObject("settings");
            if (events == null) events = new JSONArray();
            if (settings == null) settings = new JSONObject();

            int scheduled = AdhanScheduler.schedule(getContext(), events, settings);
            JSObject result = new JSObject();
            result.put("scheduled", scheduled);
            result.put("events", events.length());
            result.put("exact", AdhanScheduler.canScheduleExact(getContext()));
            call.resolve(result);

            prefetchAudio(events);
        } catch (Exception error) {
            call.reject("تعذر جدولة الأذان: " + error.getMessage());
        }
    }

    /** ينزّل في الخلفية ملفات الأذان المستخدمة فقط، فلا يتكرر التشغيل من الشبكة. */
    private void prefetchAudio(JSONArray events) {
        JSONArray unique = new JSONArray();
        for (int i = 0; i < events.length(); i++) {
            JSONObject event = events.optJSONObject(i);
            if (event == null) continue;
            String id = event.optString("adhanId", "");
            String url = event.optString("url", "");
            if (id.isEmpty() || url.isEmpty()) continue;
            if (AdhanScheduler.audioPath(getContext(), id) != null
                    && !AdhanScheduler.audioPath(getContext(), id).isEmpty()) continue;
            boolean seen = false;
            for (int j = 0; j < unique.length(); j++) {
                if (id.equals(unique.optString(j, ""))) { seen = true; break; }
            }
            if (seen) continue;
            unique.put(id);
            final String audioId = id;
            final String audioUrl = url;
            new Thread(() -> AdhanAudioStore.ensure(getContext(), audioId, audioUrl)).start();
        }
    }

    @PluginMethod
    public void status(PluginCall call) {
        JSONObject settings = AdhanScheduler.settings(getContext());
        JSObject result = new JSObject();
        result.put("events", AdhanScheduler.events(getContext()).length());
        result.put("exact", AdhanScheduler.canScheduleExact(getContext()));
        result.put("adhanEnabled", settings.optBoolean("adhanEnabled", true));
        result.put("iqamaEnabled", settings.optBoolean("iqamaEnabled", true));
        call.resolve(result);
    }

    /** تشغيل تجريبي فوري للأذان المختار — نفس مسار المنبّه تمامًا. */
    @PluginMethod
    public void play(PluginCall call) {
        String prayer = call.getString("prayer", "fajr");
        String label = call.getString("label", "الفجر");
        String adhanId = call.getString("adhanId", "");
        String url = call.getString("url", "");
        Intent service = new Intent(getContext(), AdhanService.class);
        service.setAction(AdhanService.ACTION_PLAY);
        service.putExtra("prayer", prayer);
        service.putExtra("label", label);
        service.putExtra("adhanId", adhanId);
        service.putExtra("url", url);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                getContext().startForegroundService(service);
            } else {
                getContext().startService(service);
            }
            call.resolve();
        } catch (Exception error) {
            call.reject("تعذر تشغيل الأذان: " + error.getMessage());
        }
    }

    @PluginMethod
    public void stop(PluginCall call) {
        Intent service = new Intent(getContext(), AdhanService.class);
        service.setAction(AdhanService.ACTION_STOP);
        try {
            getContext().startService(service);
        } catch (Exception error) {
            // الخدمة غير قائمة أصلًا
        }
        call.resolve();
    }


    /** تسحب الواجهة طلب فتح شاشة الأذان بعد وصول المنبّه في الخلفية. */
    @PluginMethod
    public void takePendingOpen(PluginCall call) {
        MainActivity.AdhanOpenRequest request = MainActivity.takePendingAdhan();
        JSObject result = new JSObject();
        if (request == null) {
            result.put("pending", false);
        } else {
            result.put("pending", true);
            result.put("prayer", request.prayer == null ? "" : request.prayer);
            result.put("label", request.label == null ? "" : request.label);
            result.put("adhanId", request.adhanId == null ? "" : request.adhanId);
        }
        call.resolve(result);
    }

    /** يحذف الجدول بالكامل عند إلغاء المستخدم للأذان. */
    @PluginMethod
    public void clear(PluginCall call) {
        AdhanScheduler.cancelAll(getContext());
        call.resolve();
    }
}
