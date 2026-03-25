package uk.lac.mobile;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.NetworkInfo;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pManager;
import android.net.wifi.p2p.WifiP2pManager.ActionListener;
import android.net.wifi.p2p.WifiP2pManager.Channel;
import android.os.Looper;
import android.util.Log;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * LacWifiDirect v4
 *
 * Architecture: Star topology at WiFi layer, mesh at app layer.
 *
 *   [A — GO]  ←TCP— [B — STA]
 *   [A — GO]  ←TCP— [C — STA]
 *
 * GO relays packets between all connected STAs.
 * MeshRouter.js handles TTL + dedup for multi-hop.
 *
 * No autonomous groups — avoids 192.168.49.1 IP conflict.
 */
public class LacWifiDirect {

    private static final String TAG       = "LacWifiDirect";
    public  static final int    MESH_PORT = 47731;

    public interface Listener {
        void onPeerFound(String peerId, String peerName);
        void onPeerLost(String peerId);
        void onTcpConnected(String peerId);
        void onTcpDisconnected(String peerId);
        void onPacketReceived(String rawJson, String fromId);
        void onConnected(String groupOwnerIp, boolean isGroupOwner);
        void onDisconnected();
        void onLog(String message);
    }

    private final Context         context;
    private final Listener        listener;
    private final WifiP2pManager  manager;
    private final Channel         channel;
    private final ExecutorService executor;

    // TCP connections keyed by peerId
    private final Map<String, PeerConnection> connections     = new HashMap<>();
    private final List<String>                connectingPeers = new ArrayList<>();

    private ServerSocket serverSocket;
    private boolean      running   = false;
    private boolean      isGroupOwner = false;

    public LacWifiDirect(Context context, Listener listener) {
        this.context  = context;
        this.listener = listener;
        this.executor = Executors.newCachedThreadPool();
        this.manager  = (WifiP2pManager) context.getSystemService(Context.WIFI_P2P_SERVICE);
        this.channel  = manager.initialize(context, Looper.getMainLooper(), null);
    }

    // ── Public API ────────────────────────────────────────────────────────────

    public void start() {
        running = true;
        registerReceiver();
        startTcpServer();
        // Remove any old group first, then discover
        manager.removeGroup(channel, new ActionListener() {
            @Override public void onSuccess() { discoverPeers(); }
            @Override public void onFailure(int r) { discoverPeers(); }
        });
        log("LacWifiDirect v4 started");
    }

    public void stop() {
        running = false;
        try { context.unregisterReceiver(receiver); } catch (Exception ignored) {}
        closeAllConnections();
        if (serverSocket != null) try { serverSocket.close(); } catch (IOException ignored) {}
        manager.stopPeerDiscovery(channel, null);
        manager.removeGroup(channel, null);
        log("stopped");
    }

    public int getConnectedCount() {
        synchronized (connections) { return connections.size(); }
    }

    /**
     * Send to all connected TCP peers.
     * If we are GO — also relay to all other clients (mesh forwarding).
     */
    public void broadcast(String rawJson) {
        broadcast(rawJson, null);
    }

    /**
     * Broadcast excluding one peer (to avoid echo when relaying).
     */
    public void broadcast(String rawJson, String excludePeerId) {
        synchronized (connections) {
            if (connections.isEmpty()) { log("broadcast: no peers"); return; }
            for (String key : new ArrayList<>(connections.keySet())) {
                if (key.equals(excludePeerId)) continue;
                sendTo(key, rawJson);
            }
        }
    }

    public void sendTo(String peerId, String rawJson) {
        PeerConnection conn;
        synchronized (connections) { conn = connections.get(peerId); }
        if (conn == null) return;
        final PeerConnection c = conn;
        executor.submit(() -> {
            try { c.writer.println(rawJson); c.writer.flush(); }
            catch (Exception e) { log("sendTo failed: " + e.getMessage()); removePeer(peerId); }
        });
    }

    public void connectToPeer(String addr) {
        synchronized (connections) { if (connections.containsKey(addr)) return; }
        if (!connectingPeers.contains(addr)) initiateP2pConnect(addr);
    }

    // ── Discovery ─────────────────────────────────────────────────────────────

    private void discoverPeers() {
        if (!running) return;
        manager.discoverPeers(channel, new ActionListener() {
            @Override public void onSuccess() { log("discovery started"); }
            @Override public void onFailure(int r) {
                log("discovery failed r=" + r);
                if (running) new android.os.Handler(Looper.getMainLooper())
                    .postDelayed(() -> discoverPeers(), 5000);
            }
        });
    }

    private void requestPeerList() {
        manager.requestPeers(channel, peers -> {
            for (WifiP2pDevice d : peers.getDeviceList()) {
                listener.onPeerFound(d.deviceAddress, d.deviceName);
                log("found: " + d.deviceName);
                boolean connected;
                synchronized (connections) { connected = connections.containsKey(d.deviceAddress); }
                if (!connected && !connectingPeers.contains(d.deviceAddress)) {
                    initiateP2pConnect(d.deviceAddress);
                }
            }
        });
    }

    private void initiateP2pConnect(String addr) {
        connectingPeers.add(addr);
        WifiP2pConfig cfg = new WifiP2pConfig();
        cfg.deviceAddress    = addr;
        cfg.groupOwnerIntent = 7; // neutral — let Android negotiate
        manager.connect(channel, cfg, new ActionListener() {
            @Override public void onSuccess() { log("P2P connect → " + addr); }
            @Override public void onFailure(int r) {
                log("P2P fail r=" + r);
                connectingPeers.remove(addr);
                // Retry after delay
                if (running) new android.os.Handler(Looper.getMainLooper())
                    .postDelayed(() -> initiateP2pConnect(addr), 5000);
            }
        });
    }

    private void requestConnectionInfo() {
        manager.requestConnectionInfo(channel, info -> {
            if (info != null && info.groupFormed) {
                String  ip    = info.groupOwnerAddress.getHostAddress();
                boolean owner = info.isGroupOwner;
                isGroupOwner  = owner;
                log("group formed ip=" + ip + " owner=" + owner);
                listener.onConnected(ip, owner);
                if (!owner) {
                    // STA: connect TCP to GO
                    connectTcpTo(ip, "go_" + ip);
                }
                // GO: wait for STA to connect to our TCP server
            }
        });
    }

    // ── TCP Server ────────────────────────────────────────────────────────────

    private void startTcpServer() {
        executor.submit(() -> {
            try {
                serverSocket = new ServerSocket(MESH_PORT);
                log("TCP server :" + MESH_PORT);
                while (running) {
                    try {
                        Socket s  = serverSocket.accept();
                        String ip = s.getInetAddress().getHostAddress();
                        log("incoming TCP from " + ip);
                        handleIncomingSocket(s, "cli_" + ip);
                    } catch (IOException e) { if (running) log("accept: " + e.getMessage()); }
                }
            } catch (IOException e) { log("server fail: " + e.getMessage()); }
        });
    }

    private void handleIncomingSocket(Socket socket, String peerId) {
        executor.submit(() -> {
            try {
                PrintWriter w = new PrintWriter(socket.getOutputStream(), true);
                synchronized (connections) { connections.put(peerId, new PeerConnection(socket, w, peerId)); }
                listener.onTcpConnected(peerId);
                log("TCP ready(in) " + peerId + " total=" + getConnectedCount());

                BufferedReader r = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                String line;
                while (running && (line = r.readLine()) != null) {
                    if (!line.isEmpty()) {
                        listener.onPacketReceived(line, peerId);
                        // GO relays to all other connected peers
                        if (isGroupOwner) {
                            broadcast(line, peerId);
                            log("GO relay from " + peerId);
                        }
                    }
                }
            } catch (IOException e) { log("socket in error: " + e.getMessage()); }
            finally { removePeer(peerId); }
        });
    }

    // ── TCP Client ────────────────────────────────────────────────────────────

    private void connectTcpTo(String ip, String peerId) {
        synchronized (connections) { if (connections.containsKey(peerId)) return; }
        executor.submit(() -> {
            for (int i = 0; i < 10 && running; i++) {
                try {
                    log("TCP→" + ip + " try " + (i + 1));
                    Socket s = new Socket();
                    s.connect(new InetSocketAddress(ip, MESH_PORT), 5000);
                    PrintWriter w = new PrintWriter(s.getOutputStream(), true);
                    synchronized (connections) { connections.put(peerId, new PeerConnection(s, w, peerId)); }
                    listener.onTcpConnected(peerId);
                    log("TCP ready(out) " + ip + " total=" + getConnectedCount());

                    BufferedReader r = new BufferedReader(new InputStreamReader(s.getInputStream()));
                    String line;
                    while (running && (line = r.readLine()) != null)
                        if (!line.isEmpty()) listener.onPacketReceived(line, peerId);
                    break;
                } catch (IOException e) {
                    log("TCP fail " + (i + 1) + ": " + e.getMessage());
                    try { Thread.sleep(2000); } catch (InterruptedException ignored) {}
                }
            }
            connectingPeers.remove(peerId);
        });
    }

    // ── BroadcastReceiver ─────────────────────────────────────────────────────

    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context ctx, Intent intent) {
            String a = intent.getAction();
            if (a == null) return;
            switch (a) {
                case WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION:
                    requestPeerList();
                    break;
                case WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION:
                    NetworkInfo net = intent.getParcelableExtra(WifiP2pManager.EXTRA_NETWORK_INFO);
                    if (net != null && net.isConnected()) {
                        requestConnectionInfo();
                    } else {
                        isGroupOwner = false;
                        listener.onDisconnected();
                        log("P2P disconnected");
                        if (running) new android.os.Handler(Looper.getMainLooper())
                            .postDelayed(() -> discoverPeers(), 3000);
                    }
                    break;
                case WifiP2pManager.WIFI_P2P_DISCOVERY_CHANGED_ACTION:
                    int st = intent.getIntExtra(WifiP2pManager.EXTRA_DISCOVERY_STATE, -1);
                    if (st == WifiP2pManager.WIFI_P2P_DISCOVERY_STOPPED && running)
                        new android.os.Handler(Looper.getMainLooper())
                            .postDelayed(() -> discoverPeers(), 3000);
                    break;
            }
        }
    };

    private void registerReceiver() {
        IntentFilter f = new IntentFilter();
        f.addAction(WifiP2pManager.WIFI_P2P_PEERS_CHANGED_ACTION);
        f.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);
        f.addAction(WifiP2pManager.WIFI_P2P_DISCOVERY_CHANGED_ACTION);
        context.registerReceiver(receiver, f);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private void removePeer(String id) {
        PeerConnection c;
        synchronized (connections) { c = connections.remove(id); }
        if (c != null) {
            try { c.socket.close(); } catch (IOException ignored) {}
            listener.onTcpDisconnected(id);
            log("peer left: " + id + " total=" + getConnectedCount());
        }
    }

    private void closeAllConnections() {
        synchronized (connections) {
            for (PeerConnection c : connections.values())
                try { c.socket.close(); } catch (IOException ignored) {}
            connections.clear();
        }
    }

    private void log(String m) { Log.d(TAG, m); listener.onLog(m); }

    private static class PeerConnection {
        final Socket socket; final PrintWriter writer; final String id;
        PeerConnection(Socket s, PrintWriter w, String id) { socket=s; writer=w; this.id=id; }
    }
}
