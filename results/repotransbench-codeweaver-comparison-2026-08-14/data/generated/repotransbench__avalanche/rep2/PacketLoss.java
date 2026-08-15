public final class PacketLoss implements Fault {
    private final int loss;

    public PacketLoss() {
        this(new JavaRandomSource(Settings.seed));
    }

    PacketLoss(RandomSource randomSource) {
        this.loss = randomSource.nextInt(5, 10);
    }

    public int getLoss() {
        return loss;
    }

    @Override
    public String action() {
        return "netem loss " + loss + "%";
    }

    @Override
    public String desc() {
        return "drop packets with probability " + loss + "%";
    }
}
