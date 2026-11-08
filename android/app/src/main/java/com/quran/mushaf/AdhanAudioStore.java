package com.quran.mushaf;

import android.content.Context;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * ينزّل ملف الأذان مرة واحدة إلى ذاكرة التطبيق الخاصة، فيعمل الأذان في وقته
 * دون إنترنت بعد أول تنزيل. لا يُخزَّن أي ملف داخل حزمة التطبيق.
 */
final class AdhanAudioStore {

    private AdhanAudioStore() {}

    static File folder(Context context) {
        File dir = new File(context.getFilesDir(), "adhans");
        if (!dir.exists()) dir.mkdirs();
        return dir;
    }

    static File fileFor(Context context, String id) {
        String safe = id == null ? "" : id.replaceAll("[^a-zA-Z0-9_-]", "");
        if (safe.isEmpty()) return null;
        return new File(folder(context), safe + ".mp3");
    }

    /** ينسخ الأذان المحزوم داخل التطبيق (assets/adhans) إلى ذاكرة التطبيق مرة واحدة. */
    static String copyBundled(Context context, String id) {
        File target = fileFor(context, id);
        if (target == null) return "";
        if (target.exists() && target.length() > 16_384) return target.getAbsolutePath();
        File temp = new File(target.getAbsolutePath() + ".part");
        InputStream input = null;
        FileOutputStream output = null;
        try {
            input = context.getAssets().open("adhans/" + id + ".mp3");
            output = new FileOutputStream(temp);
            byte[] buffer = new byte[64 * 1024];
            int read;
            long total = 0;
            while ((read = input.read(buffer)) > 0) {
                output.write(buffer, 0, read);
                total += read;
                if (total > 40L * 1024 * 1024) break;
            }
            output.flush();
            output.close();
            output = null;
            if (temp.length() <= 16_384) { temp.delete(); return ""; }
            if (target.exists()) target.delete();
            if (!temp.renameTo(target)) { temp.delete(); return ""; }
            AdhanScheduler.putAudioPath(context, id, target.getAbsolutePath());
            return target.getAbsolutePath();
        } catch (Exception error) {
            if (temp.exists()) temp.delete();
            return "";
        } finally {
            try { if (output != null) output.close(); } catch (Exception ignored) {}
            try { if (input != null) input.close(); } catch (Exception ignored) {}
        }
    }

    /** يعيد المسار المحلي إن كان الملف موجودًا وكاملًا، وإلا ينزّله ويعيد مساره. */
    static String ensure(Context context, String id, String url) {
        File target = fileFor(context, id);
        if (target == null) return "";
        if (target.exists() && target.length() > 16_384) {
            AdhanScheduler.putAudioPath(context, id, target.getAbsolutePath());
            return target.getAbsolutePath();
        }
        // 1) الأذان المحزوم داخل التطبيق يعمل بلا إنترنت من أول تشغيل.
        String bundled = copyBundled(context, id);
        if (!bundled.isEmpty()) return bundled;
        if (url == null || url.isEmpty()) return "";
        File temp = new File(target.getAbsolutePath() + ".part");
        HttpURLConnection connection = null;
        InputStream input = null;
        FileOutputStream output = null;
        try {
            connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setConnectTimeout(20_000);
            connection.setReadTimeout(60_000);
            connection.setInstanceFollowRedirects(true);
            connection.setRequestProperty("User-Agent", "Siraj/1.0");
            if (connection.getResponseCode() != HttpURLConnection.HTTP_OK) return "";
            input = connection.getInputStream();
            output = new FileOutputStream(temp);
            byte[] buffer = new byte[64 * 1024];
            int read;
            long total = 0;
            while ((read = input.read(buffer)) > 0) {
                output.write(buffer, 0, read);
                total += read;
                if (total > 40L * 1024 * 1024) break;
            }
            output.flush();
            output.close();
            output = null;
            if (temp.length() <= 16_384) {
                temp.delete();
                return "";
            }
            if (target.exists()) target.delete();
            if (!temp.renameTo(target)) {
                temp.delete();
                return "";
            }
            AdhanScheduler.putAudioPath(context, id, target.getAbsolutePath());
            return target.getAbsolutePath();
        } catch (Exception error) {
            if (temp.exists()) temp.delete();
            return "";
        } finally {
            try { if (output != null) output.close(); } catch (Exception ignored) {}
            try { if (input != null) input.close(); } catch (Exception ignored) {}
            if (connection != null) connection.disconnect();
        }
    }
}
