public final class Partition implements Fault {
    public Partition() {
    }

    @Override
    public String action() {
        return "netem loss 100%";
    }

    @Override
    public String desc() {
        return "network partition";
    }
}
