import distinct_n.Metrics;

import java.util.List;

public final class DistinctN {

    private DistinctN() {
    }

    public static double distinctNSentenceLevel(List<String> sentence, int n) {
        return Metrics.distinctNSentenceLevel(sentence, n);
    }

    public static double distinctNCorpusLevel(List<List<String>> sentences, int n) {
        return Metrics.distinctNCorpusLevel(sentences, n);
    }
}
