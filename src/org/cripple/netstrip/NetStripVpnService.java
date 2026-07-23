package org.cripple.netstrip;

import android.net.VpnService;
import android.content.Intent;
import android.os.ParcelFileDescriptor;
import android.util.Log;

/**
 * NetStrip VPN Service — Provides native Android VPN slot integration.
 *
 * Supports two modes:
 *   1. FULL mode (default) — Routes ALL traffic through NetStrip's TUN interface
 *      for complete packet interception. Occupies Android's VPN slot natively.
 *   2. DNS_ONLY mode — Routes only DNS (port 53) queries through the TUN interface.
 *      Allows coexistence with another VPN app that handles the actual tunnel.
 *
 * The mode is set via the Intent action: "START_FULL" or "START_DNS_ONLY".
 */
public class NetStripVpnService extends VpnService {
    private static final String TAG = "NetStripVpn";
    private static NetStripVpnService instance;
    private ParcelFileDescriptor vpnInterface = null;
    private boolean isFullMode = true;

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && "STOP".equals(intent.getAction())) {
            stopVpn();
            return START_NOT_STICKY;
        }

        // Determine mode from intent
        if (intent != null && "START_DNS_ONLY".equals(intent.getAction())) {
            isFullMode = false;
        } else {
            isFullMode = true;
        }

        startVpn();
        return START_STICKY;
    }

    public static NetStripVpnService getInstance() {
        return instance;
    }

    public int getVpnFd() {
        if (vpnInterface != null) {
            return vpnInterface.getFd();
        }
        return -1;
    }

    public boolean isFullMode() {
        return isFullMode;
    }

    private void startVpn() {
        if (vpnInterface != null) return;

        try {
            Builder builder = new Builder();
            builder.setSession("NetStrip Shield")
                   .addAddress("10.0.0.2", 24)
                   .addDnsServer("10.0.0.1")
                   .setMtu(1500)
                   .setBlocking(false);

            if (isFullMode) {
                // FULL mode: Route ALL traffic through our TUN interface
                // This makes NetStrip the system VPN — all packets flow through us
                builder.addRoute("0.0.0.0", 0);    // All IPv4 traffic
                builder.addRoute("::", 0);           // All IPv6 traffic

                // Exclude our own app to prevent routing loops
                try {
                    builder.addDisallowedApplication(getPackageName());
                } catch (Exception e) {
                    Log.w(TAG, "Failed to exclude self from VPN: " + e.getMessage());
                }

                Log.d(TAG, "VPN starting in FULL mode (all traffic routed)");
            } else {
                // DNS_ONLY mode: Only route DNS queries to our dummy gateway
                // Allows another VPN app to handle the actual tunnel
                builder.addRoute("10.0.0.1", 32);   // Only the dummy DNS server IP

                Log.d(TAG, "VPN starting in DNS_ONLY mode (DNS queries only)");
            }

            vpnInterface = builder.establish();
            Log.d(TAG, "VPN Interface established. FD: " + (vpnInterface != null ? vpnInterface.getFd() : "null")
                       + ", Mode: " + (isFullMode ? "FULL" : "DNS_ONLY"));
        } catch (Exception e) {
            Log.e(TAG, "Failed to start VPN", e);
        }
    }

    public void stopVpn() {
        try {
            if (vpnInterface != null) {
                vpnInterface.close();
                vpnInterface = null;
                Log.d(TAG, "VPN Interface closed.");
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to stop VPN", e);
        }
        stopSelf();
    }

    @Override
    public void onDestroy() {
        stopVpn();
        instance = null;
        super.onDestroy();
    }
}
