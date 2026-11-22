package com.stehouwerpublishing.feexpressdriver;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

public final class NotificationHelper {
    public static final String CHANNEL_TELEMETRY = "fe_driver_telemetry";
    public static final String CHANNEL_DISPATCH_ALERTS = "fe_dispatch_alerts";
    public static final int NOTIF_ID_FOREGROUND = 101;
    public static final int NOTIF_ID_ALERT = 102;

    public static void ensureChannels(Context ctx) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = ctx.getSystemService(NotificationManager.class);
            if (nm == null) return;

            NotificationChannel c1 = new NotificationChannel(
                    CHANNEL_TELEMETRY,
                    "FE Driver Telemetry Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            c1.setDescription("Active navigation telemetry and dispatch sync");
            nm.createNotificationChannel(c1);

            NotificationChannel c2 = new NotificationChannel(
                    CHANNEL_DISPATCH_ALERTS,
                    "Dispatch Alerts & Gate Clearance",
                    NotificationManager.IMPORTANCE_HIGH
            );
            c2.setDescription("Heads-up delivery, clearance, and dispatch calls");
            c2.enableVibration(true);
            nm.createNotificationChannel(c2);
        }
    }

    public static Notification buildForegroundNotification(Context ctx, String title, String body) {
        Intent intent = new Intent(ctx, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pi = PendingIntent.getActivity(
                ctx, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(ctx, CHANNEL_TELEMETRY)
                : new Notification.Builder(ctx);

        builder.setContentTitle(title)
                .setContentText(body)
                .setSmallIcon(R.drawable.ic_driver_truck)
                .setContentIntent(pi)
                .setOngoing(true);

        return builder.build();
    }

    public static void postAlert(Context ctx, String title, String body) {
        Intent intent = new Intent(ctx, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                ctx, 1, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0)
        );

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(ctx, CHANNEL_DISPATCH_ALERTS)
                : new Notification.Builder(ctx);

        builder.setContentTitle(title)
                .setContentText(body)
                .setSmallIcon(R.drawable.ic_driver_truck)
                .setContentIntent(pi)
                .setAutoCancel(true);

        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIF_ID_ALERT, builder.build());
        }
    }
}
