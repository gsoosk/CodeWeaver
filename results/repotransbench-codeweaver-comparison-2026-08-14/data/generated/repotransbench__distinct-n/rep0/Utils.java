import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;

public final class Utils {

    private Utils() {
    }

    public static <T> Iterable<T> padSequence(Iterable<T> sequence, int n) {
        return padSequence(sequence, n, false, false, null, null);
    }

    public static <T> Iterable<T> padSequence(
        Iterable<T> sequence,
        int n,
        boolean padLeft,
        boolean padRight,
        T leftPadSymbol,
        T rightPadSymbol
    ) {
        final Iterator<T> items = sequence.iterator();
        final int paddingSize = n > 1 ? n - 1 : 0;

        Iterator<T> paddedItems = new Iterator<T>() {
            private int leftRemaining = padLeft ? paddingSize : 0;
            private int rightRemaining = padRight ? paddingSize : 0;
            private boolean itemsExhausted;

            @Override
            public boolean hasNext() {
                if (leftRemaining > 0) {
                    return true;
                }
                if (!itemsExhausted && items.hasNext()) {
                    return true;
                }
                itemsExhausted = true;
                return rightRemaining > 0;
            }

            @Override
            public T next() {
                if (leftRemaining > 0) {
                    leftRemaining--;
                    return leftPadSymbol;
                }
                if (!itemsExhausted && items.hasNext()) {
                    return items.next();
                }
                itemsExhausted = true;
                if (rightRemaining > 0) {
                    rightRemaining--;
                    return rightPadSymbol;
                }
                throw new NoSuchElementException();
            }

            @Override
            public void remove() {
                throw new UnsupportedOperationException();
            }
        };

        return oneShotIterable(paddedItems);
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
        T rightPadSymbol
    ) {
        final int warmupSize = n > 1 ? n - 1 : 0;

        Iterator<List<T>> windows = new Iterator<List<T>>() {
            private final List<T> history = new ArrayList<T>();
            private Iterator<T> items;
            private boolean initialized;
            private IllegalStateException initializationFailure;

            private void initialize() {
                if (initializationFailure != null) {
                    throw initializationFailure;
                }
                if (initialized) {
                    return;
                }

                try {
                    items = padSequence(
                        sequence,
                        n,
                        padLeft,
                        padRight,
                        leftPadSymbol,
                        rightPadSymbol
                    ).iterator();
                    for (int i = 0; i < warmupSize; i++) {
                        history.add(items.next());
                    }
                    initialized = true;
                } catch (NoSuchElementException exception) {
                    initializationFailure = new IllegalStateException(
                        "Sequence exhausted while preparing n-gram history",
                        exception
                    );
                    throw initializationFailure;
                }
            }

            @Override
            public boolean hasNext() {
                initialize();
                return items.hasNext();
            }

            @Override
            public List<T> next() {
                initialize();
                if (!items.hasNext()) {
                    throw new NoSuchElementException();
                }

                history.add(items.next());
                List<T> window = Collections.unmodifiableList(
                    new ArrayList<T>(history)
                );
                history.remove(0);
                return window;
            }

            @Override
            public void remove() {
                throw new UnsupportedOperationException();
            }
        };

        return oneShotIterable(windows);
    }

    private static <T> Iterable<T> oneShotIterable(final Iterator<T> iterator) {
        return new Iterable<T>() {
            @Override
            public Iterator<T> iterator() {
                return iterator;
            }
        };
    }
}
