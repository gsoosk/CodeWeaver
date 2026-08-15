public final class Latency implements Fault {
    public int latency;

    public Latency() {
        this(new JavaRandomSource(Settings.seed));
    }

    Latency(RandomSource randomSource) {
        this.latency = randomSource.nextIntInclusive(100, 1000);
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
