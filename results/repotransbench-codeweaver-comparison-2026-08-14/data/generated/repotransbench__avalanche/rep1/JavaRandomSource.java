import java.util.Random;

public final class JavaRandomSource implements RandomSource {
    private final Random random;

    public JavaRandomSource(long seed) {
        random = new Random(seed);
    }

    @Override
    public double nextDouble() {
        return random.nextDouble();
    }

    @Override
    public int nextIntInclusive(int minimum, int maximum) {
        if (minimum > maximum) {
            throw new IllegalArgumentException(
                    "minimum must not exceed maximum");
        }
        return minimum + random.nextInt(maximum - minimum + 1);
    }
}
