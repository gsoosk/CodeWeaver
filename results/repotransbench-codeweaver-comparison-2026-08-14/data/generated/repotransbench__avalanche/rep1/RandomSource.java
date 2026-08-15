public interface RandomSource {
    double nextDouble();

    int nextIntInclusive(int minimum, int maximum);
}
