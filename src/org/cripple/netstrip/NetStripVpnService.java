package org.cripple.netstrip;

import android.net.VpnService;
import android.content.Intent;
import android.os.ParcelFileDescriptor;
import android.util.Log;

public class NetStripVpnService extends VpnService {
    private static final String TAG = "NetStripVpn";
    private static NetStripVpnService instance;
    private ParcelFileDescriptor vpnInterface = null;

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

    private void startVpn() {
        if (vpnInterface != null) return;

        try {
            Builder builder = new Builder();
            builder.setSession("NetStrip Shield")
                   .addAddress("10.0.0.2", 24)
                   .addRoute("10.0.0.1", 32)
                   .addDnsServer("10.0.0.1");

            vpnInterface = builder.establish();
            Log.d(TAG, "VPN Interface established. FD: " + (vpnInterface != null ? vpnInterface.getFd() : "null"));
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
