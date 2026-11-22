package com.stehouwerpublishing.feexpressdriver;

import android.annotation.SuppressLint;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.util.Log;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public final class DriverTelemetryService extends Service implements LocationListener {
    private static final String TAG = "FEDriverService";
    public static final String ACTION_START = "com.stehouwerpublishing.feexpressdriver.START";
    public static final String ACTION_STOP = "com.stehouwerpublishing.feexpressdriver.STOP";

    private LocationManager locationManager;
    private ScheduledExecutorService scheduler;
    private double currentLat = 42.3314; // Default Detroit baseline
    private double currentLon = -83.0458;
    private float currentSpeedMph = 0f;

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationHelper.ensureChannels(this);
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        scheduler = Executors.newSingleThreadScheduledExecutor();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : ACTION_START;
        if (ACTION_STOP.equals(action)) {
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }

        startInForeground();
        startLocationUpdates();
        startTelemetrySync();

        return START_STICKY;
    }

    private void startInForeground() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                    NotificationHelper.NOTIF_ID_FOREGROUND,
                    NotificationHelper.buildForegroundNotification(this, "FE Express Unit 274 Active", "GPS Navigation & Dispatch Telemetry Live"),
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
            );
        } else {
            startForeground(
                    NotificationHelper.NOTIF_ID_FOREGROUND,
                    NotificationHelper.buildForegroundNotification(this, "FE Express Unit 274 Active", "GPS Navigation & Dispatch Telemetry Live")
            );
        }
    }

    @SuppressLint("MissingPermission")
    private void startLocationUpdates() {
        try {
            if (locationManager != null) {
                if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                    locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 5000L, 5f, this);
                } else if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                    locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 5000L, 5f, this);
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "Location permission not granted or provider unavailable: " + e.getMessage());
        }
    }

    private void startTelemetrySync() {
        scheduler.scheduleWithFixedDelay(this::syncTelemetryWithDispatch, 2L, 10L, TimeUnit.SECONDS);
    }

    private void syncTelemetryWithDispatch() {
        try {
            URL url = new URL("http://127.0.0.1:8025/v1/trips/TRIP-2026-DEVIN-01");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(3000);
            conn.setReadTimeout(3000);

            int code = conn.getResponseCode();
            if (code == 200) {
                // Trip query successful
            }
            conn.disconnect();
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onLocationChanged(Location loc) {
        if (loc != null) {
            currentLat = loc.getLatitude();
            currentLon = loc.getLongitude();
            currentSpeedMph = loc.hasSpeed() ? loc.getSpeed() * 2.23694f : 0f;
        }
    }

    @Override
    public void onStatusChanged(String provider, int status, Bundle extras) {}

    @Override
    public void onProviderEnabled(String provider) {}

    @Override
    public void onProviderDisabled(String provider) {}

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (locationManager != null) {
            locationManager.removeUpdates(this);
        }
        if (scheduler != null) {
            scheduler.shutdownNow();
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
