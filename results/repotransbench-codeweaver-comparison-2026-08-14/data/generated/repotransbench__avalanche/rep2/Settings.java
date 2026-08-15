import java.util.LinkedHashMap;
import java.util.Map;
import java.util.logging.Level;

public final class Settings {
    public static int seed = 1;
    public static int delay = 1;
    public static double p_fault = 0.5d;
    public static boolean debug = false;
    public static String[] interfaces = new String[]{"eth0"};
    public static int[] ports = new int[]{2001};
    public static Level log_level = Level.INFO;
    public static Map<Class<?>, Double> faults = defaultFaults();

    private Settings() {
    }

    private static Map<Class<?>, Double> defaultFaults() {
        Map<Class<?>, Double> configuredFaults = new LinkedHashMap<Class<?>, Double>();
        configuredFaults.put(Partition.class, 0.2d);
        configuredFaults.put(PacketLoss.class, 0.2d);
        configuredFaults.put(Latency.class, 0.3d);
        configuredFaults.put(Reorder.class, 0.3d);
        return configuredFaults;
    }
}
