public interface RandomSource {
    double nextDouble();

    int nextIntInclusive(int minInclusive, int maxInclusive);
}
