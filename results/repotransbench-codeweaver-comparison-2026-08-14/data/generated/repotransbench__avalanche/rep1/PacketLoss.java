public class PacketLoss implements Fault {
    private int loss;

    public PacketLoss() {
        this(new JavaRandomSource(Settings.seed));
    }

    public PacketLoss(RandomSource randomSource) {
        loss = randomSource.nextIntInclusive(5, 10);
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
