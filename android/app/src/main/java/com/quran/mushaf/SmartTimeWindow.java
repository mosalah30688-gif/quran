package com.quran.mushaf;

import java.util.Calendar;
import java.util.TimeZone;

/** Pure time-window helpers shared by the smart notification receiver and tests. */
final class SmartTimeWindow {
    private static final int MINUTES_PER_DAY = 24 * 60;

    private SmartTimeWindow() {}

    static int parseMinute(String value, int fallback) {
        if (value == null || !value.matches("^[0-9]{2}:[0-9]{2}$")) return fallback;
        int hour;
        int minute;
        try {
            hour = Integer.parseInt(value.substring(0, 2));
            minute = Integer.parseInt(value.substring(3, 5));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
        if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return fallback;
        return hour * 60 + minute;
    }

    static boolean contains(int minute, int start, int end) {
        int value = normalize(minute);
        int from = normalize(start);
        int to = normalize(end);
        if (from == to) return false;
        if (from < to) return value >= from && value < to;
        return value >= from || value < to;
    }

    static boolean blocked(int minute, int quietStart, int quietEnd, int sleepStart, int sleepEnd) {
        return contains(minute, quietStart, quietEnd)
                || contains(minute, sleepStart, sleepEnd);
    }

    static long nextAllowedAt(
            long fromMillis,
            String quietStart,
            String quietEnd,
            String sleepStart,
            String sleepEnd,
            TimeZone zone
    ) {
        int qStart = parseMinute(quietStart, 22 * 60 + 30);
        int qEnd = parseMinute(quietEnd, 6 * 60 + 30);
        int sStart = parseMinute(sleepStart, 23 * 60);
        int sEnd = parseMinute(sleepEnd, 7 * 60);
        Calendar cursor = Calendar.getInstance(zone == null ? TimeZone.getDefault() : zone);
        cursor.setTimeInMillis(fromMillis);
        int currentMinute = cursor.get(Calendar.HOUR_OF_DAY) * 60 + cursor.get(Calendar.MINUTE);
        if (!blocked(currentMinute, qStart, qEnd, sStart, sEnd)) return fromMillis;
        cursor.set(Calendar.SECOND, 0);
        cursor.set(Calendar.MILLISECOND, 0);
        if (cursor.getTimeInMillis() < fromMillis) cursor.add(Calendar.MINUTE, 1);
        for (int checked = 0; checked <= MINUTES_PER_DAY * 2; checked++) {
            int minute = cursor.get(Calendar.HOUR_OF_DAY) * 60 + cursor.get(Calendar.MINUTE);
            if (!blocked(minute, qStart, qEnd, sStart, sEnd)) return cursor.getTimeInMillis();
            cursor.add(Calendar.MINUTE, 1);
        }
        // Fail closed: if malformed timezone rules somehow prevent a safe minute,
        // postpone for a day instead of notifying inside a blocked window.
        return fromMillis + 24L * 60L * 60L * 1000L;
    }

    private static int normalize(int minute) {
        int value = minute % MINUTES_PER_DAY;
        return value < 0 ? value + MINUTES_PER_DAY : value;
    }
}
