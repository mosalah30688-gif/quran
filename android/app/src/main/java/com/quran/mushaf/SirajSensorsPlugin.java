package com.quran.mushaf;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.Context;
import android.content.pm.PackageManager;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import androidx.core.content.ContextCompat;

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
    private Sensor accelerometerSensor;
    private Sensor magnetometerSensor;
    private Sensor gyroscopeSensor;
    /** نظام بديل: دمج التسارع + المغناطيسية، أو الجيروسكوب عند غياب المغناطيسية. */
    private final float[] gravityValues = new float[3];
    private final float[] magneticValues = new float[3];
    private boolean hasGravity;
    private boolean hasMagnetic;
    private long lastGyroAt;
    private float gyroHeading = Float.NaN;
    private long lastHeadingAt = 0L;

    @Override
    public void load() {
        sensorManager = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
        if (sensorManager != null) {
            rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
            if (rotationSensor == null) rotationSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR);
            // حساسات احتياطية: أكثر الهواتف تملك التسارع والمغناطيسية حتى لو غاب حساس التدوير.
            accelerometerSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            magnetometerSensor = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);
            gyroscopeSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE);
        }
    }

    /** هل الجهاز يملك حساس اتجاه أصلًا؟ (حتى تعرف الواجهة أن تعتمد عليه) */
    @PluginMethod
    public void capabilities(PluginCall call) {
        JSObject result = new JSObject();
        result.put("compass", rotationSensor != null
                || (accelerometerSensor != null && magnetometerSensor != null)
                || gyroscopeSensor != null);
        result.put("rotationVector", rotationSensor != null);
        result.put("magneticField", magnetometerSensor != null);
        result.put("gyroscope", gyroscopeSensor != null);
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
        if (!hasLocationPermission()) {
            call.reject("إذن الموقع مرفوض");
            return;
        }
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
    @SuppressLint("MissingPermission")
    private void LayoutFallback(PluginCall call) {
        // لا نقرأ أي موقع قبل التحقق الصريح من الإذن (متطلب فحص Lint وسياسة Google Play).
        if (!hasLocationPermission()) {
            call.reject("إذن الموقع مرفوض");
            return;
        }
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

    private boolean hasLocationPermission() {
        Context context = getContext();
        return ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
            || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
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
        if (sensorManager == null) {
            call.reject("خدمة الحساسات غير متاحة على هذا الجهاز");
            return;
        }
        lastHeadingAt = 0L;
        hasGravity = false;
        hasMagnetic = false;
        gyroHeading = Float.NaN;
        // السلسلة: حساس التدوير أولًا، ثم التسارع + المغناطيسية، ثم الجيروسكوب كحل أخير.
        if (rotationSensor != null) {
            sensorManager.registerListener(this, rotationSensor, SensorManager.SENSOR_DELAY_UI);
        } else if (accelerometerSensor != null && magnetometerSensor != null) {
            sensorManager.registerListener(this, accelerometerSensor, SensorManager.SENSOR_DELAY_UI);
            sensorManager.registerListener(this, magnetometerSensor, SensorManager.SENSOR_DELAY_UI);
        } else if (gyroscopeSensor != null) {
            sensorManager.registerListener(this, gyroscopeSensor, SensorManager.SENSOR_DELAY_UI);
        } else {
            call.reject("هذا الجهاز لا يحوي حسّاس اتجاه؛ استخدم تحديد الشمال بالشمس أو يدويًا");
            return;
        }
        JSObject result = new JSObject();
        result.put("started", true);
        result.put("mode", rotationSensor != null ? "rotation"
                : (magnetometerSensor != null ? "accelMag" : "gyro"));
        call.resolve(result);
    }

    @PluginMethod
    public void stopCompass(PluginCall call) {
        if (sensorManager != null) sensorManager.unregisterListener(this);
        call.resolve();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        int type = event.sensor.getType();
        if (type == Sensor.TYPE_ACCELEROMETER) {
            System.arraycopy(event.values, 0, gravityValues, 0, 3);
            hasGravity = true;
            emitCompositeHeading(event.accuracy);
            return;
        }
        if (type == Sensor.TYPE_MAGNETIC_FIELD) {
            System.arraycopy(event.values, 0, magneticValues, 0, 3);
            hasMagnetic = true;
            emitCompositeHeading(event.accuracy);
            return;
        }
        if (type == Sensor.TYPE_GYROSCOPE) {
            emitGyroHeading(event);
            return;
        }
        // حساس التدوير (الأدق)
        long now = System.currentTimeMillis();
        if (now - lastHeadingAt < 60L) return; // ~١٦ تحديثًا في الثانية كافية للعقرب
        lastHeadingAt = now;
        float[] rotation = new float[9];
        float[] orientation = new float[3];
        SensorManager.getRotationMatrixFromVector(rotation, event.values);
        SensorManager.getOrientation(rotation, orientation);
        emitHeading((float) Math.toDegrees(orientation[0]), event.accuracy, "rotation");
    }

    /** اتجاه من دمج التسارع والمغناطيسية — يعمل على الهواتف بلا حساس تدوير. */
    private void emitCompositeHeading(int accuracy) {
        if (!hasGravity || !hasMagnetic) return;
        long now = System.currentTimeMillis();
        if (now - lastHeadingAt < 60L) return;
        lastHeadingAt = now;
        float[] rotation = new float[9];
        float[] orientation = new float[3];
        if (!SensorManager.getRotationMatrix(rotation, null, gravityValues, magneticValues)) return;
        SensorManager.getOrientation(rotation, orientation);
        emitHeading((float) Math.toDegrees(orientation[0]), accuracy, "accelMag");
    }

    /** حل أخير: دمج معدل الدوران حول المحور الرأسي بعد معايرة، مع تصحيح انزلاق بسيط. */
    private void emitGyroHeading(SensorEvent event) {
        long now = System.currentTimeMillis();
        if (lastGyroAt == 0L) { lastGyroAt = now; return; }
        long dt = Math.max(1L, now - lastGyroAt);
        lastGyroAt = now;
        if (Float.isNaN(gyroHeading)) gyroHeading = 0f;
        gyroHeading -= (float) Math.toDegrees(event.values[2] * (dt / 1000.0));
        while (gyroHeading < 0f) gyroHeading += 360f;
        while (gyroHeading >= 360f) gyroHeading -= 360f;
        if (now - lastHeadingAt < 60L) return;
        lastHeadingAt = now;
        emitHeading(gyroHeading, event.accuracy, "gyro");
    }

    private void emitHeading(float azimuth, int accuracy, String mode) {
        while (azimuth < 0f) azimuth += 360f;
        while (azimuth >= 360f) azimuth -= 360f;
        JSObject payload = new JSObject();
        payload.put("heading", azimuth);
        payload.put("accuracy", accuracy);
        payload.put("mode", mode);
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
