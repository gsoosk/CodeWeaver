import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.RoundingMode;

public final class PythonFloatFormatter {
    private static final BigDecimal TWO = BigDecimal.valueOf(2L);
    private static final BigInteger TEN = BigInteger.TEN;
    private static final int MAX_SIGNIFICANT_DIGITS = 17;

    private PythonFloatFormatter() {
    }

    public static String format(double value) {
        if (Double.isNaN(value)) {
            return "nan";
        }
        if (value == Double.POSITIVE_INFINITY) {
            return "inf";
        }
        if (value == Double.NEGATIVE_INFINITY) {
            return "-inf";
        }

        long rawBits = Double.doubleToRawLongBits(value);
        boolean negative = (rawBits & Long.MIN_VALUE) != 0L;
        double magnitude = Math.abs(value);
        if (magnitude == 0.0d) {
            return negative ? "-0.0" : "0.0";
        }

        DecimalRepresentation representation = shortestRepresentation(magnitude);
        return (negative ? "-" : "") + representation.format();
    }

    private static DecimalRepresentation shortestRepresentation(double value) {
        BigDecimal exact = new BigDecimal(value);
        BigDecimal lower = midpoint(new BigDecimal(Math.nextDown(value)), exact);
        double next = Math.nextUp(value);
        BigDecimal upper = Double.isInfinite(next)
                ? exact.add(new BigDecimal(Math.ulp(value)).divide(TWO))
                : midpoint(exact, new BigDecimal(next));
        boolean boundariesIncluded =
                (Double.doubleToRawLongBits(value) & 1L) == 0L;
        int decimalExponent = exact.precision() - exact.scale() - 1;

        // Search the rounding interval for the closest decimal with the fewest digits.
        for (int precision = 1;
                precision <= MAX_SIGNIFICANT_DIGITS;
                precision++) {
            int decimalScale = decimalExponent - precision + 1;
            BigDecimal scaledLower = lower.scaleByPowerOfTen(-decimalScale);
            BigDecimal scaledUpper = upper.scaleByPowerOfTen(-decimalScale);

            BigInteger minimum = scaledLower
                    .setScale(0, RoundingMode.CEILING)
                    .toBigIntegerExact();
            if (!boundariesIncluded && isInteger(scaledLower)) {
                minimum = minimum.add(BigInteger.ONE);
            }

            BigInteger maximum = scaledUpper
                    .setScale(0, RoundingMode.FLOOR)
                    .toBigIntegerExact();
            if (!boundariesIncluded && isInteger(scaledUpper)) {
                maximum = maximum.subtract(BigInteger.ONE);
            }

            BigInteger minimumDigits = TEN.pow(precision - 1);
            BigInteger maximumDigits = TEN.pow(precision);
            minimum = minimum.max(minimumDigits);
            maximum = maximum.min(maximumDigits);
            if (minimum.compareTo(maximum) > 0) {
                continue;
            }

            BigInteger closest = exact
                    .scaleByPowerOfTen(-decimalScale)
                    .setScale(0, RoundingMode.HALF_EVEN)
                    .toBigIntegerExact();
            if (closest.compareTo(minimum) < 0) {
                closest = minimum;
            } else if (closest.compareTo(maximum) > 0) {
                closest = maximum;
            }
            return DecimalRepresentation.normalized(closest, decimalScale);
        }

        throw new IllegalStateException("Unable to format finite double");
    }

    private static BigDecimal midpoint(BigDecimal left, BigDecimal right) {
        return left.add(right).divide(TWO);
    }

    private static boolean isInteger(BigDecimal value) {
        return value.compareTo(new BigDecimal(value.toBigInteger())) == 0;
    }

    private static final class DecimalRepresentation {
        private final String digits;
        private final int scale;

        private DecimalRepresentation(String digits, int scale) {
            this.digits = digits;
            this.scale = scale;
        }

        static DecimalRepresentation normalized(BigInteger significand, int scale) {
            BigInteger normalized = significand;
            int normalizedScale = scale;
            while (normalized.mod(TEN).signum() == 0) {
                normalized = normalized.divide(TEN);
                normalizedScale++;
            }
            return new DecimalRepresentation(normalized.toString(), normalizedScale);
        }

        String format() {
            int exponent = scale + digits.length() - 1;
            if (exponent < -4 || exponent >= 16) {
                return scientific(exponent);
            }
            return fixed();
        }

        private String scientific(int exponent) {
            StringBuilder result = new StringBuilder();
            result.append(digits.charAt(0));
            if (digits.length() > 1) {
                result.append('.').append(digits.substring(1));
            }
            result.append('e').append(exponent < 0 ? '-' : '+');

            String exponentDigits = Integer.toString(Math.abs(exponent));
            if (exponentDigits.length() < 2) {
                result.append('0');
            }
            return result.append(exponentDigits).toString();
        }

        private String fixed() {
            int decimalPoint = digits.length() + scale;
            StringBuilder result = new StringBuilder();
            if (decimalPoint <= 0) {
                result.append("0.");
                appendZeros(result, -decimalPoint);
                return result.append(digits).toString();
            }
            if (decimalPoint >= digits.length()) {
                result.append(digits);
                appendZeros(result, decimalPoint - digits.length());
                return result.append(".0").toString();
            }
            return result.append(digits, 0, decimalPoint)
                    .append('.')
                    .append(digits, decimalPoint, digits.length())
                    .toString();
        }

        private static void appendZeros(StringBuilder result, int count) {
            for (int index = 0; index < count; index++) {
                result.append('0');
            }
        }
    }
}
