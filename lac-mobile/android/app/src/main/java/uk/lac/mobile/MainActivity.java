package uk.lac.mobile;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(LacWifiDirectPlugin.class);
        super.onCreate(savedInstanceState);
    }
}