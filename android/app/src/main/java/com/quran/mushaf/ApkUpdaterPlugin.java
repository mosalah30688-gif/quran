package com.quran.mushaf;

import android.content.Intent;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import androidx.core.content.FileProvider;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * تحديث التطبيق كاملاً: ينزّل ملف APK من الرابط، يتحقق من بصمته، ثم يفتح نافذة التثبيت لدى المستخدم.
 */
@CapacitorPlugin(name = "ApkUpdater")
public class ApkUpdaterPlugin extends Plugin {

    private final ExecutorService io = Executors.newSingleThreadExecutor();

    @PluginMethod
    public void getVersion(PluginCall call) {
        try {
            PackageInfo pi = getContext().getPackageManager().getPackageInfo(getContext().getPackageName(), 0);
            JSObject ret = new JSObject();
            ret.put("version", pi.versionName);
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("version: " + e.getMessage());
        }
    }

    @PluginMethod
    public void canInstall(PluginCall call) {
        boolean allowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.O
                || getContext().getPackageManager().canRequestPackageInstalls();
        JSObject ret = new JSObject();
        ret.put("allowed", allowed);
        call.resolve(ret);
    }

    @PluginMethod
    public void openInstallPermission(PluginCall call) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + getContext().getPackageName()));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(intent);
        }
        call.resolve();
    }

    @PluginMethod
    public void downloadAndInstall(PluginCall call) {
        final String url = call.getString("url");
        final String sha256 = call.getString("sha256", "");
        if (url == null || !url.startsWith("https://")) {
            call.reject("update URL must use HTTPS");
            return;
        }
        if (sha256 == null || !sha256.matches("(?i)[0-9a-f]{64}")) {
            call.reject("a SHA-256 checksum is required");
            return;
        }
        io.execute(() -> {
            try {
                File dir = new File(getContext().getCacheDir(), "apk");
                dir.mkdirs();
                File out = new File(dir, "update.apk");
                HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
                conn.setInstanceFollowRedirects(true);
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(30000);
                conn.setRequestProperty("User-Agent", "Siraj-Android/1.4.2");
                if (conn.getResponseCode() != 200) throw new Exception("HTTP " + conn.getResponseCode());
                if (!"https".equalsIgnoreCase(conn.getURL().getProtocol())) throw new Exception("insecure redirect");

                MessageDigest md = MessageDigest.getInstance("SHA-256");
                try (InputStream is = conn.getInputStream(); FileOutputStream os = new FileOutputStream(out)) {
                    byte[] buf = new byte[65536];
                    int n;
                    while ((n = is.read(buf)) > 0) {
                        os.write(buf, 0, n);
                        md.update(buf, 0, n);
                    }
                }
                StringBuilder hex = new StringBuilder();
                for (byte b : md.digest()) hex.append(String.format("%02x", b));
                if (!hex.toString().equalsIgnoreCase(sha256)) {
                    out.delete();
                    throw new Exception("checksum mismatch");
                }

                Uri uri = FileProvider.getUriForFile(getContext(), getContext().getPackageName() + ".fileprovider", out);
                Intent install = new Intent(Intent.ACTION_VIEW);
                install.setDataAndType(uri, "application/vnd.android.package-archive");
                install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(install);
                call.resolve();
            } catch (Exception e) {
                call.reject("update failed: " + e.getMessage());
            }
        });
    }
}
