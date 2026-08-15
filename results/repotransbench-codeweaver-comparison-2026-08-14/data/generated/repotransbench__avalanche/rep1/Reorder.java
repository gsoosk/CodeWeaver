public class Reorder implements Fault {
    private int correlation;
    private int delay;
    private int reorder;

    public Reorder() {
        this(new JavaRandomSource(Settings.seed));
    }

    public Reorder(RandomSource randomSource) {
        correlation = 50;
        delay = 10;
        reorder = randomSource.nextIntInclusive(10, 75);
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
        return "netem delay " + delay + "ms reorder "
                + (100 - reorder) + "% " + correlation + "%";
    }

    @Override
    public String desc() {
        return "reorder after delay of " + delay
                + "ms with probability " + (100 - reorder)
                + " and correlation " + correlation;
    }
}
