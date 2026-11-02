package com.quran.mushaf;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

final class SmartFeedbackStore {
    static final String EXTRA_SMART = "siraj_smart_notification";
    static final String EXTRA_SERVICE = "siraj_smart_service";
    static final String EXTRA_ID = "siraj_smart_id";
    static final String EXTRA_TARGET = "siraj_smart_target";

    private static final String PREFS = "siraj_smart_feedback";
    private static final String QUEUE = "queue";
    private static final int MAX_EVENTS = 32;

    private SmartFeedbackStore() {}

    static synchronized void record(
            Context context,
            String type,
            String service,
            String suggestionId,
            String target
    ) {
        String safeType = token(type, "dismiss");
        String safeService = token(service, "app");
        String safeId = identifier(suggestionId);
        String safeTarget = identifier(target);
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        JSONArray queue = parse(prefs.getString(QUEUE, "[]"));
        JSONObject last = queue.length() > 0 ? queue.optJSONObject(queue.length() - 1) : null;
        if (last != null && safeType.equals(last.optString("type"))
                && safeId.equals(last.optString("id"))) return;
        JSONObject item = new JSONObject();
        try {
            item.put("type", safeType);
            item.put("service", safeService);
            item.put("id", safeId);
            item.put("target", safeTarget);
            item.put("at", System.currentTimeMillis());
            queue.put(item);
        } catch (JSONException ignored) {
            return;
        }
        JSONArray bounded = new JSONArray();
        int start = Math.max(0, queue.length() - MAX_EVENTS);
        for (int index = start; index < queue.length(); index++) bounded.put(queue.opt(index));
        prefs.edit().putString(QUEUE, bounded.toString()).apply();
    }

    static synchronized JSONArray consume(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        JSONArray queue = parse(prefs.getString(QUEUE, "[]"));
        prefs.edit().remove(QUEUE).apply();
        return queue;
    }

    static void captureOpenIntent(Context context, Intent intent) {
        if (intent == null || !intent.getBooleanExtra(EXTRA_SMART, false)) return;
        record(context, "open", intent.getStringExtra(EXTRA_SERVICE),
                intent.getStringExtra(EXTRA_ID), intent.getStringExtra(EXTRA_TARGET));
        intent.removeExtra(EXTRA_SMART);
    }

    private static JSONArray parse(String raw) {
        try {
            return new JSONArray(raw == null ? "[]" : raw);
        } catch (JSONException ignored) {
            return new JSONArray();
        }
    }

    private static String token(String value, String fallback) {
        String text = value == null ? "" : value.trim().toLowerCase();
        return text.matches("^[a-z][a-z0-9_-]{0,47}$") ? text : fallback;
    }

    private static String identifier(String value) {
        String text = value == null ? "" : value.trim();
        return text.matches("^[A-Za-z0-9_.:-]{0,64}$") ? text : "";
    }
}
