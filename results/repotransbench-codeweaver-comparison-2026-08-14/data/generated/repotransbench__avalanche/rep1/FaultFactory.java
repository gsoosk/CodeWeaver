import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;

public class FaultFactory {
    public Fault create(Class<?> faultClass, RandomSource randomSource) {
        if (faultClass == null) {
            throw new IllegalArgumentException("fault class must not be null");
        }
        if (randomSource == null) {
            throw new IllegalArgumentException(
                    "random source must not be null");
        }

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

        final Class<? extends Fault> concreteFaultClass;
        try {
            concreteFaultClass = faultClass.asSubclass(Fault.class);
        } catch (ClassCastException failure) {
            throw new IllegalArgumentException(
                    "unsupported fault class: " + faultClass.getName(),
                    failure);
        }

        try {
            Constructor<? extends Fault> constructor =
                    concreteFaultClass.getDeclaredConstructor();
            return constructor.newInstance();
        } catch (NoSuchMethodException failure) {
            throw cannotInstantiate(faultClass, failure);
        } catch (InstantiationException failure) {
            throw cannotInstantiate(faultClass, failure);
        } catch (IllegalAccessException failure) {
            throw cannotInstantiate(faultClass, failure);
        } catch (InvocationTargetException failure) {
            Throwable cause = failure.getCause() == null
                    ? failure : failure.getCause();
            throw cannotInstantiate(faultClass, cause);
        }
    }

    private static IllegalArgumentException cannotInstantiate(
            Class<?> faultClass,
            Throwable cause) {
        return new IllegalArgumentException(
                "cannot instantiate fault class: " + faultClass.getName(),
                cause);
    }
}
