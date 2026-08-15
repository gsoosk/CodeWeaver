public final class JavaRandomSource implements RandomSource {
    private static final int STATE_SIZE = 624;
    private static final int PERIOD_OFFSET = 397;
    private static final int MATRIX_A = 0x9908b0df;
    private static final int UPPER_MASK = 0x80000000;
    private static final int LOWER_MASK = 0x7fffffff;

    private final int[] state = new int[STATE_SIZE];
    private int index;

    public JavaRandomSource(long seed) {
        initializeByArray(seedKey(seed));
    }

    @Override
    public double nextDouble() {
        long upper = nextInt32() >>> 5;
        long lower = nextInt32() >>> 6;
        return (upper * 67108864.0 + lower) * (1.0 / 9007199254740992.0);
    }

    @Override
    public int nextIntInclusive(int minInclusive, int maxInclusive) {
        if (minInclusive > maxInclusive) {
            throw new IllegalArgumentException("minimum must not exceed maximum");
        }

        long range = (long) maxInclusive - minInclusive + 1L;
        long offset = (long) (nextDouble() * range);
        return (int) (minInclusive + offset);
    }

    private static int[] seedKey(long seed) {
        long magnitude = seed == Long.MIN_VALUE ? Long.MIN_VALUE : Math.abs(seed);
        int upper = (int) (magnitude >>> 32);
        if (upper == 0) {
            return new int[] {(int) magnitude};
        }
        return new int[] {(int) magnitude, upper};
    }

    private void initialize(int seed) {
        state[0] = seed;
        for (int position = 1; position < STATE_SIZE; position++) {
            long previous = Integer.toUnsignedLong(state[position - 1]);
            state[position] =
                    (int) (1812433253L * (previous ^ (previous >>> 30)) + position);
        }
        index = STATE_SIZE;
    }

    private void initializeByArray(int[] key) {
        initialize(19650218);
        int stateIndex = 1;
        int keyIndex = 0;

        for (int remaining = Math.max(STATE_SIZE, key.length);
                remaining > 0;
                remaining--) {
            long previous = Integer.toUnsignedLong(state[stateIndex - 1]);
            long current = Integer.toUnsignedLong(state[stateIndex]);
            long keyPart = Integer.toUnsignedLong(key[keyIndex]);
            state[stateIndex] =
                    (int) ((current
                                    ^ ((previous ^ (previous >>> 30)) * 1664525L))
                            + keyPart
                            + keyIndex);

            stateIndex++;
            keyIndex++;
            if (stateIndex >= STATE_SIZE) {
                state[0] = state[STATE_SIZE - 1];
                stateIndex = 1;
            }
            if (keyIndex >= key.length) {
                keyIndex = 0;
            }
        }

        for (int remaining = STATE_SIZE - 1; remaining > 0; remaining--) {
            long previous = Integer.toUnsignedLong(state[stateIndex - 1]);
            long current = Integer.toUnsignedLong(state[stateIndex]);
            state[stateIndex] =
                    (int) ((current
                                    ^ ((previous ^ (previous >>> 30)) * 1566083941L))
                            - stateIndex);

            stateIndex++;
            if (stateIndex >= STATE_SIZE) {
                state[0] = state[STATE_SIZE - 1];
                stateIndex = 1;
            }
        }

        state[0] = UPPER_MASK;
        index = STATE_SIZE;
    }

    private int nextInt32() {
        if (index >= STATE_SIZE) {
            twist();
        }

        int value = state[index++];
        value ^= value >>> 11;
        value ^= (value << 7) & 0x9d2c5680;
        value ^= (value << 15) & 0xefc60000;
        value ^= value >>> 18;
        return value;
    }

    private void twist() {
        int position = 0;
        for (; position < STATE_SIZE - PERIOD_OFFSET; position++) {
            state[position] =
                    state[position + PERIOD_OFFSET] ^ shiftedState(position);
        }
        for (; position < STATE_SIZE - 1; position++) {
            state[position] =
                    state[position + PERIOD_OFFSET - STATE_SIZE] ^ shiftedState(position);
        }
        state[STATE_SIZE - 1] =
                state[PERIOD_OFFSET - 1] ^ shiftedState(STATE_SIZE - 1);
        index = 0;
    }

    private int shiftedState(int position) {
        int nextPosition = position == STATE_SIZE - 1 ? 0 : position + 1;
        int combined =
                (state[position] & UPPER_MASK) | (state[nextPosition] & LOWER_MASK);
        return (combined >>> 1) ^ ((combined & 1) == 0 ? 0 : MATRIX_A);
    }
}
