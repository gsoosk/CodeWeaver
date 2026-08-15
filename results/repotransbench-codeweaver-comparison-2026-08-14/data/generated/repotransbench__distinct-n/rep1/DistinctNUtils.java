import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Objects;

public final class DistinctNUtils {
    private DistinctNUtils() {
    }

    public static <T> Iterable<T> padSequence(
            Iterable<T> sequence,
            int n,
            boolean padLeft,
            boolean padRight,
            T leftPadSymbol,
            T rightPadSymbol) {
        Objects.requireNonNull(sequence, "sequence");
        final int paddingCount = n > 1 ? n - 1 : 0;

        return new Iterable<T>() {
            @Override
            public Iterator<T> iterator() {
                final Iterator<T> source = sequence.iterator();

                return new Iterator<T>() {
                    private int leftRemaining = padLeft ? paddingCount : 0;
                    private int rightRemaining = padRight ? paddingCount : 0;
                    private boolean sourceExhausted;

                    private boolean sourceHasNext() {
                        if (!sourceExhausted && !source.hasNext()) {
                            sourceExhausted = true;
                        }
                        return !sourceExhausted;
                    }

                    @Override
                    public boolean hasNext() {
                        return leftRemaining > 0 || sourceHasNext() || rightRemaining > 0;
                    }

                    @Override
                    public T next() {
                        if (leftRemaining > 0) {
                            leftRemaining--;
                            return leftPadSymbol;
                        }
                        if (sourceHasNext()) {
                            return source.next();
                        }
                        if (rightRemaining > 0) {
                            rightRemaining--;
                            return rightPadSymbol;
                        }
                        throw new NoSuchElementException();
                    }
                };
            }
        };
    }

    public static <T> Iterable<List<T>> ngrams(Iterable<T> sequence, int n) {
        return ngrams(sequence, n, false, false, null, null);
    }

    public static <T> Iterable<List<T>> ngrams(
            Iterable<T> sequence,
            int n,
            boolean padLeft,
            boolean padRight,
            T leftPadSymbol,
            T rightPadSymbol) {
        final Iterable<T> paddedSequence = padSequence(
                sequence, n, padLeft, padRight, leftPadSymbol, rightPadSymbol);

        return new Iterable<List<T>>() {
            @Override
            public Iterator<List<T>> iterator() {
                final Iterator<T> source = paddedSequence.iterator();

                return new Iterator<List<T>>() {
                    private final List<T> history = new ArrayList<>();
                    private boolean initialized;

                    private void initialize() {
                        if (initialized) {
                            return;
                        }
                        for (int i = 1; i < n; i++) {
                            if (!source.hasNext()) {
                                throw new NoSuchElementException(
                                        "Not enough elements to preload an n-gram");
                            }
                            history.add(source.next());
                        }
                        initialized = true;
                    }

                    @Override
                    public boolean hasNext() {
                        initialize();
                        return source.hasNext();
                    }

                    @Override
                    public List<T> next() {
                        initialize();
                        if (!source.hasNext()) {
                            throw new NoSuchElementException();
                        }

                        history.add(source.next());
                        List<T> window = new ArrayList<>(history);
                        history.remove(0);
                        return window;
                    }
                };
            }
        };
    }
}
