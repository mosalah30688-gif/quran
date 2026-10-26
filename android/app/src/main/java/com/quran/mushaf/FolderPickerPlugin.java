package com.quran.mushaf;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.util.Base64;

import androidx.activity.result.ActivityResult;
import androidx.documentfile.provider.DocumentFile;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * يتيح اختيار مجلد على الجهاز (Storage Access Framework) والكتابة فيه وقراءته.
 * كل عمليات الملفات تعمل في خيط خلفية حتى لا تتجمد الواجهة.
 */
@CapacitorPlugin(name = "FolderPicker")
public class FolderPickerPlugin extends Plugin {

    private final ExecutorService io = Executors.newFixedThreadPool(3);

    @PluginMethod
    public void pickFolder(PluginCall call) {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION
                | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        startActivityForResult(call, intent, "pickResult");
    }

    @ActivityCallback
    private void pickResult(PluginCall call, ActivityResult result) {
        if (call == null) return;
        Intent data = result.getData();
        if (result.getResultCode() != Activity.RESULT_OK || data == null || data.getData() == null) {
            call.reject("cancelled");
            return;
        }
        Uri uri = data.getData();
        try {
            getContext().getContentResolver().takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        } catch (SecurityException e) {
            call.reject("permission");
            return;
        }
        JSObject ret = new JSObject();
        ret.put("uri", uri.toString());
        call.resolve(ret);
    }

    @PluginMethod
    public void exists(PluginCall call) {
        final String uri = call.getString("uri");
        final String path = call.getString("path");
        io.execute(() -> {
            try {
                DocumentFile f = findPath(uri, path);
                JSObject ret = new JSObject();
                ret.put("exists", f != null && f.exists());
                call.resolve(ret);
            } catch (Exception e) {
                call.reject("exists failed: " + e.getMessage());
            }
        });
    }

    @PluginMethod
    public void readFile(PluginCall call) {
        final String uri = call.getString("uri");
        final String path = call.getString("path");
        io.execute(() -> {
            try {
                DocumentFile f = findPath(uri, path);
                if (f == null || !f.exists()) throw new Exception("missing");
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                try (InputStream is = getContext().getContentResolver().openInputStream(f.getUri())) {
                    if (is == null) throw new Exception("cannot open");
                    byte[] buf = new byte[16384];
                    int n;
                    while ((n = is.read(buf)) > 0) bos.write(buf, 0, n);
                }
                JSObject ret = new JSObject();
                ret.put("data", Base64.encodeToString(bos.toByteArray(), Base64.NO_WRAP));
                call.resolve(ret);
            } catch (Exception e) {
                call.reject("read failed: " + e.getMessage());
            }
        });
    }

    @PluginMethod
    public void writeFile(PluginCall call) {
        final String uri = call.getString("uri");
        final String path = call.getString("path");
        final String data = call.getString("data");
        io.execute(() -> {
            try {
                String[] parts = path.split("/");
                DocumentFile dir = DocumentFile.fromTreeUri(getContext(), Uri.parse(uri));
                if (dir == null) throw new Exception("no folder");
                for (int i = 0; i < parts.length - 1; i++) {
                    DocumentFile next = dir.findFile(parts[i]);
                    if (next == null) next = dir.createDirectory(parts[i]);
                    if (next == null) throw new Exception("cannot create folder");
                    dir = next;
                }
                String name = parts[parts.length - 1];
                DocumentFile old = dir.findFile(name);
                if (old != null) old.delete();
                DocumentFile file = dir.createFile("audio/mpeg", name);
                if (file == null) throw new Exception("cannot create file");
                byte[] bytes = Base64.decode(data, Base64.DEFAULT);
                try (OutputStream os = getContext().getContentResolver().openOutputStream(file.getUri())) {
                    if (os == null) throw new Exception("cannot open");
                    os.write(bytes);
                }
                call.resolve();
            } catch (Exception e) {
                call.reject("write failed: " + e.getMessage());
            }
        });
    }

    private DocumentFile findPath(String uri, String path) {
        DocumentFile dir = DocumentFile.fromTreeUri(getContext(), Uri.parse(uri));
        if (dir == null) return null;
        String[] parts = path.split("/");
        for (int i = 0; i < parts.length - 1; i++) {
            dir = dir.findFile(parts[i]);
            if (dir == null) return null;
        }
        return dir.findFile(parts[parts.length - 1]);
    }
}
