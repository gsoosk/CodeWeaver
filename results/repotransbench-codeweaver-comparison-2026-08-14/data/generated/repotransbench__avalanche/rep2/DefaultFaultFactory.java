import java.util.Objects;

public final class DefaultFaultFactory implements FaultFactory {
    private final RandomSource randomSource;

    public DefaultFaultFactory(RandomSource randomSource) {
        this.randomSource = Objects.requireNonNull(randomSource, "randomSource");
    }

    @Override
    public Fault create(Class<?> faultClass) {
        if (faultClass == null) {
            throw invalidFaultClass(
                    "null",
                    new IllegalArgumentException("fault class must not be null"));
        }
        if (!Fault.class.isAssignableFrom(faultClass)) {
            throw invalidFaultClass(
                    faultClass.getName(),
                    new ClassCastException(
                            faultClass.getName() + " does not implement Fault"));
        }

        try {
            if (faultClass == Partition.class) {
                return new Partition();
            }
            if (faultClass == PacketLoss.class) {
                return new PacketLoss(randomSource);
            }
            if (faultClass == Latency.class) {
                return new Latency(randomSource);
            }
            if (faultClass == Reorder.class) {
                return new Reorder(randomSource);
            }
        } catch (RuntimeException cause) {
            throw new AvalancheException(
                    "can't construct fault " + faultClass.getName(),
                    1,
                    cause);
        }

        throw invalidFaultClass(
                faultClass.getName(),
                new IllegalArgumentException(
                        "unsupported fault class " + faultClass.getName()));
    }

    private static AvalancheException invalidFaultClass(
            String className,
            RuntimeException cause) {
        return new AvalancheException("invalid fault class " + className, 1, cause);
    }
}
