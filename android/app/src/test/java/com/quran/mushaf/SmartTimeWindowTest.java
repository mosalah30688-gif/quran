package com.quran.mushaf;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Calendar;
import java.util.TimeZone;

public class SmartTimeWindowTest {
    private static final TimeZone UTC = TimeZone.getTimeZone("UTC");

    @Test
    public void parsesOnlyRealClockTimes() {
        assertEquals(22 * 60 + 30, SmartTimeWindow.parseMinute("22:30", -1));
        assertEquals(-1, SmartTimeWindow.parseMinute("24:00", -1));
        assertEquals(-1, SmartTimeWindow.parseMinute("12:90", -1));
        assertEquals(-1, SmartTimeWindow.parseMinute("2:30", -1));
    }

    @Test
    public void wrappedWindowsCoverBothSidesOfMidnight() {
        assertTrue(SmartTimeWindow.contains(23 * 60, 22 * 60, 6 * 60));
        assertTrue(SmartTimeWindow.contains(5 * 60, 22 * 60, 6 * 60));
        assertFalse(SmartTimeWindow.contains(12 * 60, 22 * 60, 6 * 60));
        assertFalse(SmartTimeWindow.contains(12 * 60, 0, 0));
    }

    @Test
    public void eitherQuietOrSleepWindowBlocksDelivery() {
        assertTrue(SmartTimeWindow.blocked(22 * 60 + 45,
                22 * 60 + 30, 6 * 60 + 30, 23 * 60, 7 * 60));
        assertTrue(SmartTimeWindow.blocked(6 * 60 + 45,
                22 * 60 + 30, 6 * 60 + 30, 23 * 60, 7 * 60));
        assertFalse(SmartTimeWindow.blocked(8 * 60,
                22 * 60 + 30, 6 * 60 + 30, 23 * 60, 7 * 60));
    }

    @Test
    public void nextAllowedTimeWaitsForTheLaterSafetyWindowEnd() {
        long from = utcMillis(2026, Calendar.OCTOBER, 20, 23, 45);
        long allowed = SmartTimeWindow.nextAllowedAt(
                from, "22:30", "06:30", "23:00", "07:00", UTC);
        assertEquals(utcMillis(2026, Calendar.OCTOBER, 21, 7, 0), allowed);
    }

    @Test
    public void alreadySafeTimeIsReturnedWithoutDelay() {
        long from = utcMillis(2026, Calendar.OCTOBER, 20, 14, 15);
        long allowed = SmartTimeWindow.nextAllowedAt(
                from, "22:30", "06:30", "23:00", "07:00", UTC);
        assertEquals(from, allowed);
    }

    private static long utcMillis(int year, int month, int day, int hour, int minute) {
        Calendar calendar = Calendar.getInstance(UTC);
        calendar.clear();
        calendar.set(year, month, day, hour, minute, 0);
        return calendar.getTimeInMillis();
    }
}
