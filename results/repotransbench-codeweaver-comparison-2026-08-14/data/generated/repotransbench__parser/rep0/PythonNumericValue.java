import java.math.BigInteger;

public interface PythonNumericValue {
    boolean isInteger();

    BigInteger asBigInteger();

    double asDouble();
}
