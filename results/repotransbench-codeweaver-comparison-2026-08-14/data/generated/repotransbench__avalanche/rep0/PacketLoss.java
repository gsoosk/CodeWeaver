public final class PacketLoss implements Fault {
    public int loss;

    public PacketLoss() {
        this(new JavaRandomSource(Settings.seed));
    }

    PacketLoss(RandomSource randomSource) {
        this.loss = randomSource.nextIntInclusive(5, 10);
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
