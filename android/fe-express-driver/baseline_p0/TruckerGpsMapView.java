package com.stehouwerpublishing.feexpressdriver;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.DashPathEffect;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

public class TruckerGpsMapView extends View {
    private final Paint roadPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint routePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint routeCasingPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint truckPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint truckRingPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint gridPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint poiPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    private final List<PointF> polyline = new ArrayList<>();
    private String nextManeuver = "Head west toward I-96 West";
    private String nextDist = "1.8 mi";
    private String currentRoad = "I-96 West • Michigan Truck Corridor";
    private String speedMph = "62";
    private String speedLimit = "65";
    private float bearing = 278.0f; // Degrees

    public static class PointF {
        public double lat;
        public double lon;
        public PointF(double lat, double lon) {
            this.lat = lat;
            this.lon = lon;
        }
    }

    public TruckerGpsMapView(Context context) {
        super(context);
        init();
    }

    public TruckerGpsMapView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        // Truck route styling (Trucker Path electric cyan / green)
        routeCasingPaint.setColor(Color.parseColor("#0369A1"));
        routeCasingPaint.setStyle(Paint.Style.STROKE);
        routeCasingPaint.setStrokeWidth(28f);
        routeCasingPaint.setStrokeCap(Paint.Cap.ROUND);
        routeCasingPaint.setStrokeJoin(Paint.Join.ROUND);

        routePaint.setColor(Color.parseColor("#06B6D4"));
        routePaint.setStyle(Paint.Style.STROKE);
        routePaint.setStrokeWidth(18f);
        routePaint.setStrokeCap(Paint.Cap.ROUND);
        routePaint.setStrokeJoin(Paint.Join.ROUND);

        roadPaint.setColor(Color.parseColor("#334155"));
        roadPaint.setStyle(Paint.Style.STROKE);
        roadPaint.setStrokeWidth(14f);
        roadPaint.setStrokeCap(Paint.Cap.ROUND);

        gridPaint.setColor(Color.parseColor("#141E33"));
        gridPaint.setStyle(Paint.Style.STROKE);
        gridPaint.setStrokeWidth(2f);
        gridPaint.setPathEffect(new DashPathEffect(new float[]{10, 10}, 0));

        truckPaint.setColor(Color.parseColor("#10B981"));
        truckPaint.setStyle(Paint.Style.FILL);

        truckRingPaint.setColor(Color.WHITE);
        truckRingPaint.setStyle(Paint.Style.STROKE);
        truckRingPaint.setStrokeWidth(4f);

        textPaint.setColor(Color.WHITE);
        textPaint.setTextSize(32f);
        textPaint.setAntiAlias(true);

        poiPaint.setColor(Color.parseColor("#F59E0B"));
        poiPaint.setStyle(Paint.Style.FILL);
    }

    public void updateNavigation(JSONObject guidance) {
        if (guidance == null) return;
        try {
            JSONArray pts = guidance.optJSONArray("polyline_points");
            if (pts != null) {
                polyline.clear();
                for (int i = 0; i < pts.length(); i++) {
                    JSONObject p = pts.getJSONObject(i);
                    polyline.add(new PointF(p.getDouble("lat"), p.getDouble("lon")));
                }
            }
            int activeIdx = guidance.optInt("active_maneuver_index", 0);
            JSONArray maneuvers = guidance.optJSONArray("maneuvers");
            if (maneuvers != null && activeIdx < maneuvers.length()) {
                JSONObject m = maneuvers.getJSONObject(activeIdx);
                nextManeuver = m.optString("instruction", nextManeuver);
                double d = guidance.optDouble("distance_to_next_maneuver_miles", m.optDouble("distance_miles", 1.0));
                nextDist = String.format("%.1f mi", d);
                currentRoad = m.optString("street_name", currentRoad);
            }
            postInvalidate();
        } catch (Exception ignored) {}
    }

    public void updateTelemetry(float speed, float heading) {
        if (speed >= 0) speedMph = String.valueOf((int) speed);
        if (heading >= 0) bearing = heading;
        postInvalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth();
        int h = getHeight();
        if (w == 0 || h == 0) return;

        // Dark cockpit navigation canvas background (#0A0F1D)
        canvas.drawColor(Color.parseColor("#0A0F1D"));

        // Background terrain radar grid lines
        for (int y = 0; y < h; y += 120) {
            canvas.drawLine(0, y, w, y, gridPaint);
        }
        for (int x = 0; x < w; x += 120) {
            canvas.drawLine(x, 0, x, h, gridPaint);
        }

        // Draw cross streets / background road network
        canvas.drawLine(-50, h * 0.35f, w + 50, h * 0.30f, roadPaint);
        canvas.drawLine(-50, h * 0.70f, w + 50, h * 0.75f, roadPaint);
        canvas.drawLine(w * 0.25f, -50, w * 0.20f, h + 50, roadPaint);
        canvas.drawLine(w * 0.80f, -50, w * 0.85f, h + 50, roadPaint);

        // Center perspective on Truck Position (65% down from top)
        float truckX = w * 0.50f;
        float truckY = h * 0.65f;

        // Draw dynamic curved corridor polyline
        Path routePath = new Path();
        routePath.moveTo(truckX, truckY);
        // Ahead along bearing
        routePath.cubicTo(
                truckX, truckY - (h * 0.25f),
                truckX - (w * 0.15f), truckY - (h * 0.45f),
                truckX - (w * 0.10f), 40f
        );
        // Trail behind truck
        routePath.lineTo(truckX + 15, h + 80);

        canvas.drawPath(routePath, routeCasingPaint);
        canvas.drawPath(routePath, routePaint);

        // Draw Truck Waypoint Markers (e.g. Weigh Station / Rest Area POIs)
        drawPoiMarker(canvas, truckX - (w * 0.14f), truckY - (h * 0.35f), "WEIGH STATION OPEN");
        drawPoiMarker(canvas, truckX + (w * 0.25f), truckY - (h * 0.20f), "DIESEL • CAT SCALE");

        // Draw Vehicle Arrow / Chevron (Unit 274)
        canvas.save();
        canvas.translate(truckX, truckY);
        canvas.rotate(0); // View is oriented in driver track-up mode

        // Outer pulse circle
        Paint pulsePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        pulsePaint.setColor(Color.parseColor("#3310B981"));
        canvas.drawCircle(0, 0, 48f, pulsePaint);

        // Truck Chevron Arrow (Pointing Up)
        Path chevron = new Path();
        chevron.moveTo(0, -32f);    // Tip
        chevron.lineTo(24f, 24f);   // Right wing
        chevron.lineTo(0, 10f);     // Notch
        chevron.lineTo(-24f, 24f);  // Left wing
        chevron.close();

        canvas.drawPath(chevron, truckPaint);
        canvas.drawPath(chevron, truckRingPaint);
        canvas.restore();

        // Compass Heading Badge (top right)
        drawCompass(canvas, w - 80f, 80f, bearing);

        // Speed Limit Sign (top left)
        drawSpeedSign(canvas, 36f, 40f, speedMph, speedLimit);
    }

    private void drawPoiMarker(Canvas canvas, float x, float y, String label) {
        canvas.drawCircle(x, y, 14f, poiPaint);
        Paint pRing = new Paint(Paint.ANTI_ALIAS_FLAG);
        pRing.setColor(Color.WHITE);
        pRing.setStyle(Paint.Style.STROKE);
        pRing.setStrokeWidth(3f);
        canvas.drawCircle(x, y, 14f, pRing);

        Paint pText = new Paint(Paint.ANTI_ALIAS_FLAG);
        pText.setColor(Color.parseColor("#CBD5E1"));
        pText.setTextSize(20f);
        pText.setFakeBoldText(true);
        canvas.drawText(label, x + 22f, y + 7f, pText);
    }

    private void drawCompass(Canvas canvas, float cx, float cy, float heading) {
        Paint bg = new Paint(Paint.ANTI_ALIAS_FLAG);
        bg.setColor(Color.parseColor("#1E293B"));
        canvas.drawCircle(cx, cy, 40f, bg);

        Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
        ring.setColor(Color.parseColor("#475569"));
        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeWidth(3f);
        canvas.drawCircle(cx, cy, 40f, ring);

        // North needle
        canvas.save();
        canvas.translate(cx, cy);
        canvas.rotate(-heading);
        Paint needleN = new Paint(Paint.ANTI_ALIAS_FLAG);
        needleN.setColor(Color.parseColor("#EF4444")); // Red north
        Path nPath = new Path();
        nPath.moveTo(0, -30f);
        nPath.lineTo(8f, 0);
        nPath.lineTo(-8f, 0);
        nPath.close();
        canvas.drawPath(nPath, needleN);

        Paint needleS = new Paint(Paint.ANTI_ALIAS_FLAG);
        needleS.setColor(Color.parseColor("#94A3B8"));
        Path sPath = new Path();
        sPath.moveTo(0, 30f);
        sPath.lineTo(8f, 0);
        sPath.lineTo(-8f, 0);
        sPath.close();
        canvas.drawPath(sPath, needleS);
        canvas.restore();
    }

    private void drawSpeedSign(Canvas canvas, float x, float y, String currentMph, String limitMph) {
        // Speed Limit Box
        RectF r = new RectF(x, y, x + 110f, y + 140f);
        Paint pBg = new Paint(Paint.ANTI_ALIAS_FLAG);
        pBg.setColor(Color.WHITE);
        canvas.drawRoundRect(r, 14f, 14f, pBg);

        Paint pBorder = new Paint(Paint.ANTI_ALIAS_FLAG);
        pBorder.setColor(Color.BLACK);
        pBorder.setStyle(Paint.Style.STROKE);
        pBorder.setStrokeWidth(4f);
        RectF rIn = new RectF(x + 6f, y + 6f, x + 104f, y + 134f);
        canvas.drawRoundRect(rIn, 10f, 10f, pBorder);

        Paint pText = new Paint(Paint.ANTI_ALIAS_FLAG);
        pText.setColor(Color.BLACK);
        pText.setFakeBoldText(true);
        pText.setTextSize(16f);
        pText.setTextAlign(Paint.Align.CENTER);
        canvas.drawText("SPEED", x + 55f, y + 32f, pText);
        canvas.drawText("LIMIT", x + 55f, y + 54f, pText);

        pText.setTextSize(46f);
        canvas.drawText(limitMph, x + 55f, y + 110f, pText);

        // Current Speed Meter (below sign)
        RectF rSpeed = new RectF(x, y + 155f, x + 110f, y + 230f);
        Paint pSpdBg = new Paint(Paint.ANTI_ALIAS_FLAG);
        pSpdBg.setColor(Color.parseColor("#0F172A"));
        canvas.drawRoundRect(rSpeed, 12f, 12f, pSpdBg);

        Paint pSpdTxt = new Paint(Paint.ANTI_ALIAS_FLAG);
        pSpdTxt.setColor(Color.parseColor("#10B981"));
        pSpdTxt.setFakeBoldText(true);
        pSpdTxt.setTextSize(40f);
        pSpdTxt.setTextAlign(Paint.Align.CENTER);
        canvas.drawText(currentMph, x + 55f, y + 200f, pSpdTxt);

        Paint pMph = new Paint(Paint.ANTI_ALIAS_FLAG);
        pMph.setColor(Color.parseColor("#94A3B8"));
        pMph.setTextSize(14f);
        pMph.setTextAlign(Paint.Align.CENTER);
        canvas.drawText("MPH", x + 55f, y + 220f, pMph);
    }
}
