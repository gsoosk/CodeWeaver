import java.util.LinkedHashMap;
import java.util.Map;
import java.util.logging.Level;

public final class Settings {
    public static int seed = 1;
    public static int delay = 1;
    public static double p_fault = 0.5;
    public static boolean debug = false;
    public static String[] interfaces = {"eth0"};
    public static int[] ports = {2001};
    public static Level log_level = Level.INFO;
    public static Map<Class<?>, Double> faults = createFaults();

    private static Map<Class<?>, Double> createFaults() {
        Map<Class<?>, Double> configuredFaults = new LinkedHashMap<Class<?>, Double>();
        configuredFaults.put(Partition.class, 0.2);
        configuredFaults.put(PacketLoss.class, 0.2);
        configuredFaults.put(Latency.class, 0.3);
        configuredFaults.put(Reorder.class, 0.3);
        return configuredFaults;
    }

    private Settings() {
    }
}
