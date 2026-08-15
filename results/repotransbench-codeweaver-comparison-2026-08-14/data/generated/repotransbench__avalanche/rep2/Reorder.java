public final class Reorder implements Fault {
    private static final int DEFAULT_CORRELATION = 50;
    private static final int DEFAULT_DELAY = 10;

    private final int correlation;
    private final int delay;
    private final int reorder;

    public Reorder() {
        this(new JavaRandomSource(Settings.seed));
    }

    Reorder(RandomSource randomSource) {
        this.correlation = DEFAULT_CORRELATION;
        this.delay = DEFAULT_DELAY;
        this.reorder = randomSource.nextInt(10, 75);
    }

    public int getCorrelation() {
        return correlation;
    }

    public int getDelay() {
        return delay;
    }

    public int getReorder() {
        return reorder;
    }

    @Override
    public String action() {
        return "netem delay " + delay + "ms reorder " + (100 - reorder) + "% "
                + correlation + "%";
    }

    @Override
    public String desc() {
        return "reorder after delay of " + delay + "ms with probability "
                + (100 - reorder) + " and correlation " + correlation;
    }
}
