package com.quran.mushaf;

import android.Manifest;
import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

/**
 * الحساسات التي تحتاجها الواجهة: تحديد الموقع الجغرافي بوصلةً حقيقيةً من حساسات الجهاز.
 * كانت الواجهة تعتمد على واجهات المتصفح داخل WebView، وهي لا تطلب إذن الموقع
 * ولا تُسلّم اتجاه البوصلة، فكان الزر «لا يعمل» والعقرب «ثابتًا». هنا نطلب الإذن
 * من النظام ونقرأ الحساسات مباشرة.
 */
@CapacitorPlugin(
        name = "SirajSensors",
        permissions = {
                @Permission(
                        alias = "location",
                        strings = {
                                Manifest.permission.ACCESS_COARSE_LOCATION,
                                Manifest.permission.ACCESS_FINE_LOCATION,
                        })
        })
public class SirajSensorsPlugin extends Plugin implements SensorEventListener {

    private SensorManager sensorManager;
    private Sensor rotationSensor;
    private long lastHeadingAt = 0L;

    @Override
    public void load() {
        sensorManager = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
            if (rotationSensor == null) rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR);
        }
    }

    /** هل الجهاز يملك حساس اتجاه أصلًا؟ (حتى تعرف الواجهة أن تعتمد عليه) */
    @PluginMethod
    public void capabilities(PluginCall call) {
        JSObject result = new JSObject();
        result.put("compass", rotationSensor != null);
        result.put("location", getContext().getPackageManager()
                .hasSystemFeature(android.content.pm.PackageManager.FEATURE_LOCATION));
        result.put("locationPermission", getPermissionState("location").toString());
        call.resolve(result);
    }

    // ---------- الموقع ----------

    @PluginMethod
    public void getLocation(final PluginCall call) {
        if (getPermissionState("location") != PermissionState.GRANTED) {
            requestPermissionForAlias("location", call, "locationPermissionCallback");
            return;
        }
        fetchLocation(call);
    }

    @PermissionCallback
    private void locationPermissionCallback(PluginCall call) {
        if (getPermissionState("location") == PermissionState.GRANTED) {
            fetchLocation(call);
            return;
        }
        JSObject denied = new JSObject();
        denied.put("denied", true);
        call.resolve(denied);
    }

    @PluginMethod
    public void requestLocationPermission(PluginCall call) {
        if (getPermissionState("location") == PermissionState.GRANTED) {
            JSObject granted = new JSObject();
            granted.put("granted", true);
            call.resolve(granted);
            return;
        }
        requestPermissionForAlias("location", call, "locationPermissionCallback");
    }

    private void fetchLocation(final PluginCall call) {
        final LocationManager manager = (LocationManager) getContext().getSystemService(Context.LOCATION_SERVICE);
        if (manager == null) {
            call.reject("لا يوجد مزوّد موقع في هذا الجهاز");
            return;
        }
        Location best = null;
        try {
            for (String provider : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER, LocationManager.PASSIVE_PROVIDER}) {
                if (!manager.isProviderEnabled(provider)) continue;
                Location last = manager.getLastKnownLocation(provider);
                if (last == null) continue;
                if (best == null || last.getTime() > best.getTime()) best = last;
            }
        } catch (SecurityException ignored) {
            // الإذن يُطلب قبل الاستدعاء
        }
        if (best != null && System.currentTimeMillis() - best.getTime() < 10 * 60 * 1000L) {
            resolveLocation(call, best, false);
            return;
        }

        // لا يوجد موقع حديث: نطلب تحديثًا واحدًا ونعيد أول قراءة تصل.
        final Handler handler = new Handler(Looper.getMainLooper());
        final boolean[] done = new boolean[]{false};
        final LocationManager locationManager = manager;
        final android.location.LocationListener listener = new android.location.LocationListener() {
            @Override
            public void onLocationChanged(Location location) {
                if (done[0]) return;
                done[0] = true;
                try {
                    locationManager.removeUpdates(this);
                } catch (Exception ignored) {
                    // تم الإلغاء
                }
                resolveLocation(call, location, false);
            }

            @Override
            public void onStatusChanged(String provider, int status, android.os.Bundle extras) {}

            @Override
            public void onProviderEnabled(String provider) {}

            @Override
            public void onProviderDisabled(String provider) {}
        };
        try {
            String provider = manager.isProviderEnabled(LocationManager.GPS_PROVIDER)
                    ? LocationManager.GPS_PROVIDER : LocationManager.NETWORK_PROVIDER;
            if (!manager.isProviderEnabled(provider)) {
                call.reject("خدمة الموقع مغلقة في الهاتف، فشّلها من إعدادات النظام");
                return;
            }
            manager.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper());
        } catch (SecurityException error) {
            call.reject("إذن الموقع مرفوض");
            return;
        } catch (Exception error) {
            call.reject("تعذّر بدء تحديد الموقع");
            return;
        }
        handler.postDelayed(() -> {
            if (done[0]) return;
            done[0] = true;
            try {
                locationManager.removeUpdates(listener);
            } catch (Exception ignored) {
                // تم الإلغاء
            }
            LayoutFallback(call);
        }, 15000L);
    }

    /** إن انتهت المدة بلا قراءة نعيد آخر موقع معروف ولو قديمًا. */
    private void LayoutFallback(PluginCall call) {
        LocationManager manager = (LocationManager) getContext().getSystemService(Context.LOCATION_SERVICE);
        try {
            if (manager != null) {
                for (String provider : new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER, LocationManager.PASSIVE_PROVIDER}) {
                    Location last = manager.getLastKnownLocation(provider);
                    if (last != null) {
                        resolveLocation(call, last, true);
                        return;
                    }
                }
            }
        } catch (Exception ignored) {
            // لا شيء
        }
        call.reject("لم يصل تحديد الموقع؛ جرّب في مكان مكشوف أو أدخل الإحداثيات يدويًا");
    }

    private void resolveLocation(PluginCall call, Location location, boolean stale) {
        JSObject result = new JSObject();
        result.put("lat", location.getLatitude());
        result.put("lng", location.getLongitude());
        result.put("accuracy", location.hasAccuracy() ? location.getAccuracy() : -1);
        result.put("stale", stale);
        call.resolve(result);
    }

    // ---------- البوصلة ----------

    @PluginMethod
    public void startCompass(PluginCall call) {
        if (sensorManager == null || rotationSensor == null) {
            call.reject("هذا الجهاز لا يحوي حساس اتجاه (بوصلة)");
            return;
        }
        lastHeadingAt = 0L;
        sensorManager.registerListener(this, rotationSensor, SensorManager.SENSOR_DELAY_UI);
        JSObject result = new JSObject();
        result.put("started", true);
        call.resolve(result);
    }

    @PluginMethod
    public void stopCompass(PluginCall call) {
        if (sensorManager != null) sensorManager.unregisterListener(this);
        call.resolve();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        long now = System.currentTimeMillis();
        if (now - lastHeadingAt < 60L) return; // ~١٦ تحديثًا في الثانية كافية للعقرب
        lastHeadingAt = now;
        float[] rotation = new float[9];
        float[] orientation = new float[3];
        SensorManager.getRotationMatrixFromVector(rotation, event.values);
        SensorManager.getOrientation(rotation, orientation);
        float azimuth = (float) Math.toDegrees(orientation[0]);
        if (azimuth < 0) azimuth += 360f;
        JSObject payload = new JSObject();
        payload.put("heading", azimuth);
        payload.put("accuracy", event.accuracy);
        notifyListeners("heading", payload, true);
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // لا حاجة لإبلاغ الواجهة؛ تُرسل الدقة مع كل قراءة
    }

    @Override
    protected void handleOnPause() {
        super.handleOnPause();
        if (sensorManager != null) sensorManager.unregisterListener(this);
    }
}
