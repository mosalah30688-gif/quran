package com.quran.mushaf;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Build;
import android.os.storage.StorageManager;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.InflaterInputStream;

/**
 * تنزيل وقراءة حزمة التفاسير الاختيارية دون تحميل القاعدة الكبيرة في الذاكرة.
 * الملف لا يُعتمد إلا بعد مطابقة الحجم وSHA-256 وفحص بنية SQLite.
 */
@CapacitorPlugin(name = "TafsirStore")
public class TafsirStorePlugin extends Plugin {
    private static final String DOWNLOAD_URL =
            "https://github.com/mosalah30688-gif/quran/releases/download/" +
            "siraj-tafsir-data-v2026.10.28/Siraj-Tafsir-Offline-2026.10.28.sqlite3";
    private static final long EXPECTED_BYTES = 728866816L;
    private static final String EXPECTED_SHA256 =
            "66ce7736d44679a2b6fc536635a556881d8c7f98bad47fa5622a155700c1900c";
    private static final int EXPECTED_EDITIONS = 78;
    private static final int EXPECTED_SCHEMA = 1;
    private static final int CHUNK_SIZE = 16;

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final AtomicBoolean cancelling = new AtomicBoolean(false);
    private volatile boolean downloading = false;
    private volatile HttpURLConnection activeConnection;

    private File dataDirectory() {
        File directory = new File(getContext().getFilesDir(), "tafsir");
        if (!directory.exists()) directory.mkdirs();
        return directory;
    }

    private File databaseFile() {
        return new File(dataDirectory(), "tafsir-offline.sqlite3");
    }

    private File partialFile() {
        return new File(dataDirectory(), "tafsir-offline.sqlite3.part");
    }

    private long availableBytes() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            StorageManager storage = getContext().getSystemService(StorageManager.class);
            if (storage != null) {
                try {
                    return storage.getAllocatableBytes(storage.getUuidForPath(dataDirectory()));
                } catch (IOException ignored) {
                    // Fall through for unusual storage providers.
                }
            }
        }
        return dataDirectory().getUsableSpace();
    }

    @PluginMethod
    public void status(PluginCall call) {
        io.execute(() -> {
            File db = databaseFile();
            boolean ready = db.isFile() && db.length() == EXPECTED_BYTES && validDatabase(db, false);
            JSObject result = new JSObject();
            result.put("ready", ready);
            result.put("downloading", downloading);
            result.put("bytes", ready ? db.length() : (partialFile().isFile() ? partialFile().length() : 0));
            result.put("total", EXPECTED_BYTES);
            result.put("freeBytes", availableBytes());
            result.put("version", "2026.10.28");
            call.resolve(result);
        });
    }

    @PluginMethod
    public void download(PluginCall call) {
        synchronized (this) {
            if (downloading) {
                call.reject("download already running");
                return;
            }
            downloading = true;
            cancelling.set(false);
        }
        io.execute(() -> {
            try {
                File db = databaseFile();
                if (db.isFile() && db.length() == EXPECTED_BYTES && validDatabase(db, false)) {
                    call.resolve(statusObject(true, db.length()));
                    return;
                }
                File part = partialFile();
                long existing = part.isFile() ? part.length() : 0L;
                if (existing > EXPECTED_BYTES) {
                    part.delete();
                    existing = 0L;
                }
                long required = Math.max(0L, EXPECTED_BYTES - existing) + 64L * 1024L * 1024L;
                if (availableBytes() < required) {
                    throw new IOException("insufficient storage");
                }
                if (existing < EXPECTED_BYTES) streamDownload(part, existing);
                ensureNotCancelled();
                if (part.length() != EXPECTED_BYTES) throw new IOException("size mismatch");
                String digest = sha256(part);
                if (!EXPECTED_SHA256.equalsIgnoreCase(digest)) {
                    part.delete();
                    throw new IOException("checksum mismatch");
                }
                ensureNotCancelled();
                if (!validDatabase(part, true)) {
                    part.delete();
                    throw new IOException("invalid database");
                }
                if (db.exists() && !db.delete()) throw new IOException("cannot replace database");
                if (!part.renameTo(db)) throw new IOException("cannot install database");
                call.resolve(statusObject(true, db.length()));
            } catch (InterruptedIOException cancelled) {
                call.reject("cancelled");
            } catch (Exception error) {
                if (cancelling.get()) call.reject("cancelled");
                else call.reject("tafsir download failed: " + error.getMessage());
            } finally {
                HttpURLConnection connection = activeConnection;
                if (connection != null) connection.disconnect();
                activeConnection = null;
                downloading = false;
                cancelling.set(false);
            }
        });
    }

    private void streamDownload(File target, long offset) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(DOWNLOAD_URL).openConnection();
        activeConnection = connection;
        connection.setInstanceFollowRedirects(true);
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(45000);
        connection.setRequestProperty("User-Agent", "Siraj-Android/1.4.3");
        connection.setRequestProperty("Accept", "application/octet-stream");
        if (offset > 0) connection.setRequestProperty("Range", "bytes=" + offset + "-");
        int response = connection.getResponseCode();
        if (!"https".equalsIgnoreCase(connection.getURL().getProtocol())) {
            throw new IOException("insecure redirect");
        }
        boolean append = offset > 0 && response == HttpURLConnection.HTTP_PARTIAL;
        if (response != HttpURLConnection.HTTP_OK && response != HttpURLConnection.HTTP_PARTIAL) {
            throw new IOException("HTTP " + response);
        }
        if (!append) offset = 0L;
        long written = offset;
        long lastNotice = 0L;
        try (InputStream input = connection.getInputStream();
             FileOutputStream output = new FileOutputStream(target, append)) {
            byte[] buffer = new byte[128 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) {
                ensureNotCancelled();
                output.write(buffer, 0, count);
                written += count;
                long now = System.currentTimeMillis();
                if (now - lastNotice >= 350L || written == EXPECTED_BYTES) {
                    notifyProgress(written, "download");
                    lastNotice = now;
                }
                if (written > EXPECTED_BYTES) throw new IOException("download too large");
            }
            output.getFD().sync();
        } finally {
            connection.disconnect();
            activeConnection = null;
        }
    }

    private String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        long read = 0L;
        long lastNotice = 0L;
        try (InputStream input = new FileInputStream(file)) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) {
                ensureNotCancelled();
                digest.update(buffer, 0, count);
                read += count;
                long now = System.currentTimeMillis();
                if (now - lastNotice >= 500L) {
                    notifyProgress(read, "verify");
                    lastNotice = now;
                }
            }
        }
        StringBuilder hex = new StringBuilder(64);
        for (byte value : digest.digest()) hex.append(String.format(Locale.US, "%02x", value));
        return hex.toString();
    }

    private void notifyProgress(long bytes, String phase) {
        JSObject progress = new JSObject();
        progress.put("bytes", bytes);
        progress.put("total", EXPECTED_BYTES);
        progress.put("phase", phase);
        notifyListeners("downloadProgress", progress);
    }

    private void ensureNotCancelled() throws InterruptedIOException {
        if (cancelling.get()) throw new InterruptedIOException("cancelled");
    }

    private JSObject statusObject(boolean ready, long bytes) {
        JSObject result = new JSObject();
        result.put("ready", ready);
        result.put("downloading", downloading);
        result.put("bytes", bytes);
        result.put("total", EXPECTED_BYTES);
        result.put("freeBytes", availableBytes());
        return result;
    }

    @PluginMethod
    public void cancel(PluginCall call) {
        cancelling.set(true);
        HttpURLConnection connection = activeConnection;
        if (connection != null) connection.disconnect();
        call.resolve();
    }

    @PluginMethod
    public void delete(PluginCall call) {
        io.execute(() -> {
            if (downloading) {
                call.reject("download running");
                return;
            }
            boolean ok = (!databaseFile().exists() || databaseFile().delete())
                    && (!partialFile().exists() || partialFile().delete());
            if (ok) call.resolve(statusObject(false, 0));
            else call.reject("delete failed");
        });
    }

    @PluginMethod
    public void lookupBatch(PluginCall call) {
        final String edition = call.getString("edition", "");
        final JSONArray references = call.getArray("ayahs");
        io.execute(() -> {
            File file = databaseFile();
            if (!file.isFile() || file.length() != EXPECTED_BYTES || references == null || references.length() > 40) {
                JSObject result = new JSObject();
                result.put("handled", false);
                call.resolve(result);
                return;
            }
            SQLiteDatabase database = null;
            Cursor editionCursor = null;
            try {
                database = SQLiteDatabase.openDatabase(file.getAbsolutePath(), null, SQLiteDatabase.OPEN_READONLY);
                editionCursor = database.rawQuery("SELECT 1 FROM editions WHERE edition=?", new String[]{edition});
                if (!editionCursor.moveToFirst()) {
                    JSObject result = new JSObject();
                    result.put("handled", false);
                    call.resolve(result);
                    return;
                }
                editionCursor.close();
                editionCursor = null;
                JSONArray texts = new JSONArray();
                for (int i = 0; i < references.length(); i++) {
                    JSONObject reference = references.optJSONObject(i);
                    if (reference == null) {
                        texts.put(JSONObject.NULL);
                        continue;
                    }
                    int surah = reference.optInt("surah", 0);
                    int ayah = reference.optInt("ayah", 0);
                    String text = lookup(database, edition, surah, ayah);
                    texts.put(text == null ? JSONObject.NULL : text);
                }
                JSObject result = new JSObject();
                result.put("handled", true);
                result.put("texts", texts);
                call.resolve(result);
            } catch (Exception error) {
                call.reject("tafsir lookup failed: " + error.getMessage());
            } finally {
                if (editionCursor != null) editionCursor.close();
                if (database != null) database.close();
            }
        });
    }

    @PluginMethod
    public void query(PluginCall call) {
        final String edition = call.getString("edition", "");
        final int surah = call.getInt("surah", 0);
        final int ayah = call.getInt("ayah", 0);
        io.execute(() -> {
            File file = databaseFile();
            if (!file.isFile() || file.length() != EXPECTED_BYTES) {
                call.reject("tafsir pack missing");
                return;
            }
            if (surah < 1 || surah > 114 || ayah < 1 || !edition.matches("[a-z]+(?:\\.[a-z]+|:\\d+)")) {
                call.reject("invalid query");
                return;
            }
            SQLiteDatabase database = null;
            Cursor cursor = null;
            try {
                database = SQLiteDatabase.openDatabase(file.getAbsolutePath(), null, SQLiteDatabase.OPEN_READONLY);
                int chunk = (ayah - 1) / CHUNK_SIZE;
                int slot = (ayah - 1) % CHUNK_SIZE;
                cursor = database.rawQuery(
                        "SELECT payload FROM tafsir_chunks WHERE edition=? AND surah=? AND chunk=?",
                        new String[]{edition, String.valueOf(surah), String.valueOf(chunk)});
                JSObject result = new JSObject();
                result.put("covered", true);
                if (!cursor.moveToFirst()) {
                    result.put("text", null);
                    call.resolve(result);
                    return;
                }
                byte[] packed = cursor.getBlob(0);
                String json = inflate(packed);
                JSONArray values = new JSONArray(json);
                if (values.length() != CHUNK_SIZE) throw new IOException("bad chunk");
                if (values.isNull(slot)) result.put("text", null);
                else {
                    String text = values.optString(slot, "").trim();
                    result.put("text", text.isEmpty() ? null : text);
                }
                call.resolve(result);
            } catch (Exception error) {
                call.reject("tafsir query failed: " + error.getMessage());
            } finally {
                if (cursor != null) cursor.close();
                if (database != null) database.close();
            }
        });
    }

    private String lookup(SQLiteDatabase database, String edition, int surah, int ayah) throws Exception {
        if (surah < 1 || surah > 114 || ayah < 1) return null;
        int chunk = (ayah - 1) / CHUNK_SIZE;
        int slot = (ayah - 1) % CHUNK_SIZE;
        try (Cursor cursor = database.rawQuery(
                "SELECT payload FROM tafsir_chunks WHERE edition=? AND surah=? AND chunk=?",
                new String[]{edition, String.valueOf(surah), String.valueOf(chunk)})) {
            if (!cursor.moveToFirst()) return null;
            JSONArray values = new JSONArray(inflate(cursor.getBlob(0)));
            if (values.length() != CHUNK_SIZE) throw new IOException("bad chunk");
            if (values.isNull(slot)) return null;
            String text = values.optString(slot, "").trim();
            return text.isEmpty() ? null : text;
        }
    }

    private String inflate(byte[] packed) throws IOException {
        try (InflaterInputStream input = new InflaterInputStream(new java.io.ByteArrayInputStream(packed));
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[32 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            return output.toString(StandardCharsets.UTF_8.name());
        }
    }

    private boolean validDatabase(File file, boolean fullCheck) {
        SQLiteDatabase database = null;
        Cursor cursor = null;
        try {
            database = SQLiteDatabase.openDatabase(file.getAbsolutePath(), null, SQLiteDatabase.OPEN_READONLY);
            cursor = database.rawQuery("PRAGMA user_version", null);
            if (!cursor.moveToFirst() || cursor.getInt(0) != EXPECTED_SCHEMA) return false;
            cursor.close();
            cursor = database.rawQuery("SELECT value FROM metadata WHERE key='codec'", null);
            if (!cursor.moveToFirst() || !"zlib-json-list-v1".equals(cursor.getString(0))) return false;
            cursor.close();
            cursor = database.rawQuery("SELECT value FROM metadata WHERE key='edition_count'", null);
            if (!cursor.moveToFirst() || cursor.getInt(0) != EXPECTED_EDITIONS) return false;
            cursor.close();
            cursor = database.rawQuery("SELECT COUNT(*) FROM editions", null);
            if (!cursor.moveToFirst() || cursor.getInt(0) != EXPECTED_EDITIONS) return false;
            if (fullCheck) {
                cursor.close();
                cursor = database.rawQuery("PRAGMA quick_check", null);
                if (!cursor.moveToFirst() || !"ok".equalsIgnoreCase(cursor.getString(0))) return false;
            }
            return true;
        } catch (Exception ignored) {
            return false;
        } finally {
            if (cursor != null) cursor.close();
            if (database != null) database.close();
        }
    }

    @Override
    protected void handleOnDestroy() {
        cancelling.set(true);
        HttpURLConnection connection = activeConnection;
        if (connection != null) connection.disconnect();
        io.shutdownNow();
        super.handleOnDestroy();
    }
}
