public class Latency implements Fault {
    private int latency;

    public Latency() {
        this(new JavaRandomSource(Settings.seed));
    }

    public Latency(RandomSource randomSource) {
        latency = randomSource.nextIntInclusive(100, 1000);
    }

    public int getLatency() {
        return latency;
    }

    @Override
    public String action() {
        return "netem delay " + latency + "ms";
    }

    @Override
    public String desc() {
        return "delay of " + latency + "ms";
    }
}
