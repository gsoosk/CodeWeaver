import java.util.LinkedHashMap;
import java.util.Map;
import java.util.logging.Level;

public final class Settings {
    public static int seed = 1;
    public static int delay = 1;
    public static double p_fault = 0.5;
    public static boolean debug = false;
    public static String[] interfaces = new String[] {"eth0"};
    public static int[] ports = new int[] {2001};
    public static Level log_level = Level.INFO;
    public static Object faults;

    static {
        Map<Class<? extends Fault>, Double> defaultFaults =
                new LinkedHashMap<Class<? extends Fault>, Double>();
        defaultFaults.put(Partition.class, 0.2);
        defaultFaults.put(PacketLoss.class, 0.2);
        defaultFaults.put(Latency.class, 0.3);
        defaultFaults.put(Reorder.class, 0.3);
        faults = defaultFaults;
    }

    private Settings() {
    }
}
