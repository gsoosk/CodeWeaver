package distinct_n;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Objects;

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
            T rightPadSymbol) {
        Objects.requireNonNull(sequence, "sequence");
        final int paddingSize = n > 1 ? n - 1 : 0;

        return () -> new Iterator<T>() {
            private final Iterator<T> source = sequence.iterator();
            private int leftRemaining = padLeft ? paddingSize : 0;
            private int rightRemaining = padRight ? paddingSize : 0;
            private boolean sourceExhausted;

            @Override
            public boolean hasNext() {
                if (leftRemaining > 0) {
                    return true;
                }
                if (!sourceExhausted && source.hasNext()) {
                    return true;
                }
                sourceExhausted = true;
                return rightRemaining > 0;
            }

            @Override
            public T next() {
                if (leftRemaining > 0) {
                    leftRemaining--;
                    return leftPadSymbol;
                }
                if (!sourceExhausted && source.hasNext()) {
                    return source.next();
                }
                sourceExhausted = true;
                if (rightRemaining > 0) {
                    rightRemaining--;
                    return rightPadSymbol;
                }
                throw new NoSuchElementException();
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
        final int order = n > 1 ? n : 1;

        return () -> new Iterator<List<T>>() {
            private final Iterator<T> source = paddedSequence.iterator();
            private final List<T> history = new ArrayList<>();
            private List<T> nextWindow;
            private boolean finished;

            @Override
            public boolean hasNext() {
                prepareNext();
                return !finished;
            }

            @Override
            public List<T> next() {
                prepareNext();
                if (finished) {
                    throw new NoSuchElementException();
                }
                List<T> result = nextWindow;
                nextWindow = null;
                return result;
            }

            private void prepareNext() {
                if (nextWindow != null || finished) {
                    return;
                }
                while (history.size() < order - 1) {
                    if (!source.hasNext()) {
                        finished = true;
                        return;
                    }
                    history.add(source.next());
                }
                if (!source.hasNext()) {
                    finished = true;
                    return;
                }
                history.add(source.next());
                nextWindow = Collections.unmodifiableList(new ArrayList<>(history));
                history.remove(0);
            }
        };
    }
}
