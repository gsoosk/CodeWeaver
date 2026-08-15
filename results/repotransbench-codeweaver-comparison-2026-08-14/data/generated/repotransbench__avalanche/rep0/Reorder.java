public final class Reorder implements Fault {
    public int correlation;
    public int delay;
    public int reorder;

    public Reorder() {
        this(new JavaRandomSource(Settings.seed));
    }

    Reorder(RandomSource randomSource) {
        this.correlation = 50;
        this.delay = 10;
        this.reorder = randomSource.nextIntInclusive(10, 75);
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
        return "netem delay " + delay + "ms reorder " + (100 - reorder)
                + "% " + correlation + "%";
    }

    @Override
    public String desc() {
        return "reorder after delay of " + delay + "ms with probability "
                + (100 - reorder) + " and correlation " + correlation;
    }
}
