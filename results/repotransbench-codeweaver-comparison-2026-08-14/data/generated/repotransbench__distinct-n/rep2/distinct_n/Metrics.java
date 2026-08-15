package distinct_n;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

public final class Metrics {

    private Metrics() {
    }

    public static double distinctNSentenceLevel(List<String> sentence, int n) {
        Objects.requireNonNull(sentence, "sentence");
        if (sentence.isEmpty()) {
            return 0.0;
        }

        Set<List<String>> distinctNgrams = new HashSet<>();
        for (List<String> ngram : Utils.ngrams(sentence, n)) {
            distinctNgrams.add(ngram);
        }
        return (double) distinctNgrams.size() / sentence.size();
    }

    public static double distinctNCorpusLevel(List<List<String>> sentences, int n) {
        Objects.requireNonNull(sentences, "sentences");
        if (sentences.isEmpty()) {
            throw new ArithmeticException("Cannot average an empty corpus");
        }

        double total = 0.0;
        for (List<String> sentence : sentences) {
            total += distinctNSentenceLevel(sentence, n);
        }
        return total / sentences.size();
    }
}
