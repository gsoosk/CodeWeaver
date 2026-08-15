import java.util.Random;

public final class JavaRandomSource implements RandomSource {
    private final Random random;

    public JavaRandomSource(long seed) {
        this.random = new Random(seed);
    }

    @Override
    public double nextDouble() {
        return random.nextDouble();
    }

    @Override
    public int nextInt(int minInclusive, int maxInclusive) {
        if (minInclusive > maxInclusive) {
            throw new IllegalArgumentException(
                    "minInclusive must be less than or equal to maxInclusive");
        }

        int bound = maxInclusive - minInclusive + 1;
        if (bound > 0) {
            return minInclusive + random.nextInt(bound);
        }

        int value;
        do {
            value = random.nextInt();
        } while (value < minInclusive || value > maxInclusive);
        return value;
    }
}
