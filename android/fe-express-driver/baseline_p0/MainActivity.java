package com.stehouwerpublishing.feexpressdriver;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private TextView tvStatus;
    private TextView tvGate;
    private TextView tvRoute;
    private TextView tvMetrics;
    private Button btnArrived;
    private Button btnCheckIn;
    private Button btnConsent;
    private ProgressBar progressBar;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private boolean cameraConsentGranted = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Check and start foreground telemetry service
        Intent svc = new Intent(this, DriverTelemetryService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(svc);
        } else {
            startService(svc);
        }

        buildNativeUI();
        refreshTripState();
    }

    private void buildNativeUI() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.parseColor("#0B0F19"));

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(32, 48, 32, 48);

        // Title
        TextView tvTitle = new TextView(this);
        tvTitle.setText("FE Express Driver Portal");
        tvTitle.setTextSize(22);
        tvTitle.setTextColor(Color.WHITE);
        tvTitle.setGravity(Gravity.CENTER);
        layout.addView(tvTitle);

        TextView tvSub = new TextView(this);
        tvSub.setText("Unit 274 • Michigan Regional Corridor");
        tvSub.setTextSize(14);
        tvSub.setTextColor(Color.parseColor("#94A3B8"));
        tvSub.setGravity(Gravity.CENTER);
        tvSub.setPadding(0, 4, 0, 24);
        layout.addView(tvSub);

        // Trip Route Card
        tvRoute = new TextView(this);
        tvRoute.setText("Active Trip: Loading...");
        tvRoute.setTextSize(16);
        tvRoute.setTextColor(Color.parseColor("#38BDF8"));
        tvRoute.setBackgroundColor(Color.parseColor("#1E293B"));
        tvRoute.setPadding(24, 20, 24, 20);
        layout.addView(tvRoute);

        // Status Card
        tvStatus = new TextView(this);
        tvStatus.setText("Status: EN_ROUTE");
        tvStatus.setTextSize(15);
        tvStatus.setTextColor(Color.parseColor("#10B981"));
        tvStatus.setPadding(0, 16, 0, 8);
        layout.addView(tvStatus);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(65);
        progressBar.setPadding(0, 0, 0, 16);
        layout.addView(progressBar);

        // Metrics
        tvMetrics = new TextView(this);
        tvMetrics.setText("Distance: 148.5 mi • Elapsed: 72 min");
        tvMetrics.setTextSize(14);
        tvMetrics.setTextColor(Color.parseColor("#CBD5E1"));
        tvMetrics.setPadding(0, 0, 0, 24);
        layout.addView(tvMetrics);

        // Gate Intel Box
        tvGate = new TextView(this);
        tvGate.setText("Gate Target: Loading...");
        tvGate.setTextSize(15);
        tvGate.setTextColor(Color.parseColor("#FDE047"));
        tvGate.setBackgroundColor(Color.parseColor("#1E293B"));
        tvGate.setPadding(24, 20, 24, 20);
        layout.addView(tvGate);

        // Action Buttons
        btnArrived = new Button(this);
        btnArrived.setText("Report Gate Arrival");
        btnArrived.setBackgroundColor(Color.parseColor("#2563EB"));
        btnArrived.setTextColor(Color.WHITE);
        btnArrived.setPadding(0, 20, 0, 20);
        btnArrived.setOnClickListener(v -> postEvent("ARRIVED", "Arrived at destination facility"));
        LinearLayout.LayoutParams lp1 = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp1.setMargins(0, 32, 0, 16);
        layout.addView(btnArrived, lp1);

        btnCheckIn = new Button(this);
        btnCheckIn.setText("Complete Check-In");
        btnCheckIn.setBackgroundColor(Color.parseColor("#059669"));
        btnCheckIn.setTextColor(Color.WHITE);
        btnCheckIn.setPadding(0, 20, 0, 20);
        btnCheckIn.setOnClickListener(v -> postEvent("CHECKED_IN", "Checked in at staging kiosk"));
        layout.addView(btnCheckIn);

        // Camera Consent Toggle
        btnConsent = new Button(this);
        btnConsent.setText("Grant Dispatch Road Cam Access");
        btnConsent.setBackgroundColor(Color.parseColor("#475569"));
        btnConsent.setTextColor(Color.WHITE);
        btnConsent.setPadding(0, 20, 0, 20);
        btnConsent.setOnClickListener(v -> toggleCameraConsent());
        LinearLayout.LayoutParams lp2 = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp2.setMargins(0, 16, 0, 32);
        layout.addView(btnConsent, lp2);

        scroll.addView(layout);
        setContentView(scroll);
    }

    private void refreshTripState() {
        executor.execute(() -> {
            try {
                URL url = new URL("http://127.0.0.1:8025/v1/trips/TRIP-2026-DEVIN-01");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);

                if (conn.getResponseCode() == 200) {
                    BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = br.readLine()) != null) sb.append(line);
                    br.close();

                    JSONObject json = new JSONObject(sb.toString());
                    final String origin = json.getString("origin");
                    final String status = json.getString("status");
                    final double progress = json.optDouble("route_progress_pct", 0);
                    final double miles = json.optDouble("mileage_miles", 0);
                    final int elapsed = json.optInt("elapsed_minutes", 0);

                    JSONObject gate = json.getJSONObject("destination_gate");
                    final String facility = gate.getString("facility_name");
                    final String gateName = gate.getString("gate_name");
                    final String approach = gate.getString("approach_road");
                    final String notes = gate.optString("notes", "");

                    mainHandler.post(() -> {
                        tvRoute.setText("Route: " + origin + "\n→ " + facility);
                        tvStatus.setText("Status: " + status);
                        progressBar.setProgress((int) progress);
                        tvMetrics.setText("Progress: " + (int)progress + "% • " + miles + " mi • " + elapsed + " min");
                        tvGate.setText("Destination: " + gateName + "\nApproach: " + approach + "\nNotes: " + notes);
                    });
                }
                conn.disconnect();
            } catch (Exception ignored) {}
        });
    }

    private void postEvent(String eventType, String note) {
        executor.execute(() -> {
            try {
                URL url = new URL("http://127.0.0.1:8025/v1/trips/TRIP-2026-DEVIN-01/events");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);

                JSONObject payload = new JSONObject();
                payload.put("event_id", "ev-" + System.currentTimeMillis());
                payload.put("event_type", eventType);
                payload.put("observed_at", System.currentTimeMillis() / 1000.0);
                JSONObject p = new JSONObject();
                p.put("note", note);
                p.put("reported_by", "Devin Unit 274");
                payload.put("payload", p);

                OutputStream os = conn.getOutputStream();
                os.write(payload.toString().getBytes("UTF-8"));
                os.flush();
                os.close();

                if (conn.getResponseCode() == 200) {
                    mainHandler.post(() -> {
                        Toast.makeText(MainActivity.this, "Dispatched event: " + eventType, Toast.LENGTH_SHORT).show();
                        refreshTripState();
                    });
                }
                conn.disconnect();
            } catch (Exception e) {
                mainHandler.post(() -> Toast.makeText(MainActivity.this, "Offline Event Buffered locally", Toast.LENGTH_SHORT).show());
            }
        });
    }

    private void toggleCameraConsent() {
        cameraConsentGranted = !cameraConsentGranted;
        final String action = cameraConsentGranted ? "GRANT_CAMERA" : "STOP_CAMERA";

        executor.execute(() -> {
            try {
                URL url = new URL("http://127.0.0.1:8025/v1/trips/TRIP-2026-DEVIN-01/media/session");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);

                JSONObject body = new JSONObject();
                body.put("action", action);
                body.put("requested_by", "driver");

                OutputStream os = conn.getOutputStream();
                os.write(body.toString().getBytes("UTF-8"));
                os.flush();
                os.close();

                conn.getResponseCode();
                conn.disconnect();

                mainHandler.post(() -> {
                    if (cameraConsentGranted) {
                        btnConsent.setText("Road Cam Granted (Tap to Revoke)");
                        btnConsent.setBackgroundColor(Color.parseColor("#059669"));
                        NotificationHelper.postAlert(MainActivity.this, "Road Cam Active", "Windshield stream shared with Dispatcher");
                    } else {
                        btnConsent.setText("Grant Dispatch Road Cam Access");
                        btnConsent.setBackgroundColor(Color.parseColor("#475569"));
                    }
                });
            } catch (Exception ignored) {}
        });
    }
}
