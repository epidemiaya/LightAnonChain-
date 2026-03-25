package uk.lac.mobile;

import android.Manifest;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

@CapacitorPlugin(
    name = "LacWifiDirect",
    permissions = {
        @Permission(strings = { Manifest.permission.ACCESS_FINE_LOCATION },  alias = "location"),
        @Permission(strings = { Manifest.permission.NEARBY_WIFI_DEVICES },   alias = "nearbyWifi"),
        @Permission(strings = { Manifest.permission.ACCESS_WIFI_STATE },     alias = "wifiState"),
        @Permission(strings = { Manifest.permission.CHANGE_WIFI_STATE },     alias = "changeWifi"),
        @Permission(strings = { Manifest.permission.INTERNET },              alias = "internet"),
    }
)
public class LacWifiDirectPlugin extends Plugin {

    private LacWifiDirect wifiDirect;

    @PluginMethod
    public void start(PluginCall call) {
        requestAllPermissions(call, "permissionsCallback");
    }

    @PermissionCallback
    private void permissionsCallback(PluginCall call) {
        wifiDirect = new LacWifiDirect(getContext(), new LacWifiDirect.Listener() {

            @Override public void onPeerFound(String peerId, String peerName) {
                JSObject d = new JSObject();
                d.put("address", peerId); d.put("name", peerName);
                notifyListeners("peerFound", d);
            }

            @Override public void onPeerLost(String peerId) {
                JSObject d = new JSObject(); d.put("address", peerId);
                notifyListeners("peerLost", d);
            }

            @Override public void onTcpConnected(String peerId) {
                JSObject d = new JSObject(); d.put("peerId", peerId);
                notifyListeners("tcpConnected", d);
            }

            @Override public void onTcpDisconnected(String peerId) {
                JSObject d = new JSObject(); d.put("peerId", peerId);
                notifyListeners("tcpDisconnected", d);
            }

            @Override public void onPacketReceived(String rawJson, String fromId) {
                JSObject d = new JSObject(); d.put("data", rawJson); d.put("from", fromId);
                notifyListeners("packet", d);
            }

            @Override public void onConnected(String groupOwnerIp, boolean isGroupOwner) {
                JSObject d = new JSObject();
                d.put("groupOwnerIp", groupOwnerIp); d.put("isGroupOwner", isGroupOwner);
                notifyListeners("connected", d);
            }

            @Override public void onDisconnected() {
                notifyListeners("disconnected", new JSObject());
            }

            @Override public void onLog(String message) {
                JSObject d = new JSObject(); d.put("message", message);
                notifyListeners("log", d);
            }
        });

        wifiDirect.start();
        call.resolve();
    }

    @PluginMethod public void stop(PluginCall call) {
        if (wifiDirect != null) { wifiDirect.stop(); wifiDirect = null; }
        call.resolve();
    }

    @PluginMethod public void broadcast(PluginCall call) {
        String data = call.getString("data");
        if (data == null) { call.reject("data required"); return; }
        if (wifiDirect == null) { call.reject("not started"); return; }
        wifiDirect.broadcast(data);
        call.resolve();
    }

    @PluginMethod public void connectToPeer(PluginCall call) {
        String address = call.getString("address");
        if (address == null) { call.reject("address required"); return; }
        if (wifiDirect == null) { call.reject("not started"); return; }
        wifiDirect.connectToPeer(address);
        call.resolve();
    }

    @PluginMethod public void getStatus(PluginCall call) {
        JSObject r = new JSObject();
        r.put("running", wifiDirect != null);
        r.put("peers", wifiDirect != null ? wifiDirect.getConnectedCount() : 0);
        call.resolve(r);
    }
}
