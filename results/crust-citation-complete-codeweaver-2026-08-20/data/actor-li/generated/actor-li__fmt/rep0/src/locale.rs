use std::borrow::Cow;
use std::ffi::OsStr;

#[cfg(unix)]
use std::os::unix::ffi::OsStrExt;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum LocaleMode {
    C,
    Utf8,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DecodedUnit {
    pub(crate) scalar: Option<char>,
    pub(crate) byte_len: usize,
    pub(crate) display_width: usize,
}

pub(crate) fn locale_mode_from_environment(
    lc_all: Option<&OsStr>,
    lc_ctype: Option<&OsStr>,
    lang: Option<&OsStr>,
) -> LocaleMode {
    let selected = [lc_all, lc_ctype, lang]
        .into_iter()
        .flatten()
        .map(os_str_bytes)
        .find(|value| !value.is_empty());
    let Some(selected) = selected else {
        return LocaleMode::C;
    };

    let upper: Vec<u8> = selected.iter().map(u8::to_ascii_uppercase).collect();
    if upper == b"C" || upper == b"POSIX" {
        LocaleMode::C
    } else if upper.windows(5).any(|window| window == b"UTF-8")
        || upper.windows(4).any(|window| window == b"UTF8")
    {
        LocaleMode::Utf8
    } else {
        LocaleMode::C
    }
}

fn os_str_bytes(value: &OsStr) -> Cow<'_, [u8]> {
    #[cfg(unix)]
    {
        Cow::Borrowed(value.as_bytes())
    }
    #[cfg(not(unix))]
    {
        Cow::Owned(value.to_string_lossy().into_owned().into_bytes())
    }
}

pub(crate) fn decode_next(input: &[u8], mode: LocaleMode) -> Option<DecodedUnit> {
    let first = *input.first()?;
    if mode == LocaleMode::C || first < 0x80 {
        let scalar = (first < 0x80).then(|| char::from(first));
        return Some(DecodedUnit {
            scalar,
            byte_len: 1,
            display_width: scalar.map_or(1, scalar_width),
        });
    }

    let expected_len = match first {
        0xc2..=0xdf => 2,
        0xe0..=0xef => 3,
        0xf0..=0xf4 => 4,
        _ => 1,
    };
    if expected_len > 1 && input.len() >= expected_len {
        if let Ok(text) = std::str::from_utf8(&input[..expected_len]) {
            if let Some(scalar) = text.chars().next() {
                return Some(DecodedUnit {
                    scalar: Some(scalar),
                    byte_len: expected_len,
                    display_width: scalar_width(scalar),
                });
            }
        }
    }

    Some(DecodedUnit {
        scalar: None,
        byte_len: 1,
        display_width: 1,
    })
}

pub(crate) fn is_wide_blank(unit: DecodedUnit) -> bool {
    let Some(scalar) = unit.scalar else {
        return false;
    };
    matches!(
        scalar,
        '\t'
            | ' '
            | '\u{1680}'
            | '\u{2000}'..='\u{2006}'
            | '\u{2008}'..='\u{200a}'
            | '\u{205f}'
            | '\u{3000}'
    )
}

pub(crate) fn is_wide_space(unit: DecodedUnit) -> bool {
    unit.scalar.is_some_and(|scalar| {
        matches!(
            scalar,
            '\t'
                | '\n'
                | '\u{000b}'
                | '\u{000c}'
                | '\r'
                | ' '
                | '\u{1680}'
                | '\u{2000}'..='\u{2006}'
                | '\u{2008}'..='\u{200a}'
                | '\u{2028}'
                | '\u{2029}'
                | '\u{205f}'
                | '\u{3000}'
        )
    })
}

pub(crate) fn scalar_width(scalar: char) -> usize {
    <char as unicode_width::UnicodeWidthChar>::width(scalar).unwrap_or(1)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsStr;

    #[test]
    fn locale_precedence_is_lc_all_then_lc_ctype_then_lang() {
        assert_eq!(
            locale_mode_from_environment(
                Some(OsStr::new("C")),
                Some(OsStr::new("C.UTF-8")),
                Some(OsStr::new("C.UTF-8")),
            ),
            LocaleMode::C
        );
        assert_eq!(
            locale_mode_from_environment(
                Some(OsStr::new("")),
                Some(OsStr::new("C.UTF-8")),
                Some(OsStr::new("C")),
            ),
            LocaleMode::Utf8
        );
        assert_eq!(
            locale_mode_from_environment(
                Some(OsStr::new("")),
                Some(OsStr::new("")),
                Some(OsStr::new("C.utf8")),
            ),
            LocaleMode::Utf8
        );
        assert_eq!(
            locale_mode_from_environment(
                Some(OsStr::new("not-a-locale")),
                Some(OsStr::new("C.UTF-8")),
                Some(OsStr::new("C.UTF-8")),
            ),
            LocaleMode::C
        );
    }

    #[test]
    fn c_and_posix_select_c_locale() {
        for locale in ["C", "POSIX", "c", "posix"] {
            assert_eq!(
                locale_mode_from_environment(Some(OsStr::new(locale)), None, None),
                LocaleMode::C
            );
        }
        assert_eq!(
            locale_mode_from_environment(None, None, None),
            LocaleMode::C
        );
    }

    #[test]
    fn common_utf8_spellings_select_utf8() {
        for locale in ["C.UTF-8", "C.utf8", "en_US.UTF-8", "en_US.utf8"] {
            assert_eq!(
                locale_mode_from_environment(Some(OsStr::new(locale)), None, None),
                LocaleMode::Utf8
            );
        }
    }

    #[test]
    fn unknown_locale_falls_back_to_c() {
        for locale in ["", "not-a-locale", "en_US.ISO-8859-1"] {
            assert_eq!(
                locale_mode_from_environment(Some(OsStr::new(locale)), None, None),
                LocaleMode::C
            );
        }
    }

    fn decoded_scalar(scalar: char) -> DecodedUnit {
        DecodedUnit {
            scalar: Some(scalar),
            byte_len: scalar.len_utf8(),
            display_width: scalar_width(scalar),
        }
    }

    #[test]
    fn c_locale_decodes_ascii_one_byte_at_a_time() {
        let input = b"A\0~";
        for (index, expected) in ['A', '\0', '~'].into_iter().enumerate() {
            let unit = decode_next(&input[index..], LocaleMode::C).unwrap();
            assert_eq!(unit.scalar, Some(expected));
            assert_eq!(unit.byte_len, 1);
            assert_eq!(unit.display_width, scalar_width(expected));
        }
        assert_eq!(decode_next(&[], LocaleMode::C), None);
    }

    #[test]
    fn c_locale_rejects_high_bytes_one_at_a_time() {
        let input = b"\xc3\xa9\xff";
        for index in 0..input.len() {
            assert_eq!(
                decode_next(&input[index..], LocaleMode::C),
                Some(DecodedUnit {
                    scalar: None,
                    byte_len: 1,
                    display_width: 1,
                })
            );
        }
    }

    #[test]
    fn utf8_decodes_valid_scalar_prefixes() {
        let input = b"A\xc3\xa9\xe7\x95\x8c\xcc\x81";
        let expected = [
            ('A', 1, 1),
            ('\u{00e9}', 2, 1),
            ('\u{754c}', 3, 2),
            ('\u{0301}', 2, 0),
        ];
        let mut offset = 0;

        for (scalar, byte_len, display_width) in expected {
            let unit = decode_next(&input[offset..], LocaleMode::Utf8).unwrap();
            assert_eq!(
                unit,
                DecodedUnit {
                    scalar: Some(scalar),
                    byte_len,
                    display_width,
                }
            );
            offset += unit.byte_len;
        }
        assert_eq!(offset, input.len());
    }

    #[test]
    fn utf8_rejects_malformed_bytes_one_at_a_time() {
        let input = b"\xe2(\xa1\xc0\xaf\xf5";
        let expected = [None, Some('('), None, None, None, None];

        for (index, scalar) in expected.into_iter().enumerate() {
            assert_eq!(
                decode_next(&input[index..], LocaleMode::Utf8),
                Some(DecodedUnit {
                    scalar,
                    byte_len: 1,
                    display_width: 1,
                })
            );
        }
    }

    #[test]
    fn utf8_rejects_truncated_sequences_one_at_a_time() {
        for input in [&b"\xc2"[..], &b"\xe2\x82"[..], &b"\xf0\x9f\x92"[..]] {
            for index in 0..input.len() {
                assert_eq!(
                    decode_next(&input[index..], LocaleMode::Utf8),
                    Some(DecodedUnit {
                        scalar: None,
                        byte_len: 1,
                        display_width: 1,
                    })
                );
            }
        }
    }

    #[test]
    fn wide_blank_excludes_vertical_separators() {
        for scalar in ['\t', ' ', '\u{1680}', '\u{2000}', '\u{3000}'] {
            assert!(is_wide_blank(decoded_scalar(scalar)), "{scalar:?}");
        }
        for scalar in ['\n', '\u{000b}', '\u{000c}', '\r', '\u{2028}', '\u{2029}'] {
            assert!(!is_wide_blank(decoded_scalar(scalar)), "{scalar:?}");
        }
    }

    #[test]
    fn wide_blank_explicitly_excludes_nbsp() {
        for scalar in ['\u{00a0}', '\u{2007}', '\u{202f}'] {
            assert!(!is_wide_blank(decoded_scalar(scalar)), "{scalar:?}");
        }
        assert!(!is_wide_blank(DecodedUnit {
            scalar: None,
            byte_len: 1,
            display_width: 1,
        }));
    }

    #[test]
    fn wide_space_accepts_centering_whitespace() {
        for scalar in [
            '\t', '\n', '\u{000b}', '\u{000c}', '\r', ' ', '\u{1680}', '\u{2000}', '\u{2028}',
            '\u{2029}', '\u{3000}',
        ] {
            assert!(is_wide_space(decoded_scalar(scalar)), "{scalar:?}");
        }
        for scalar in ['\u{00a0}', '\u{2007}', '\u{202f}', 'A'] {
            assert!(!is_wide_space(decoded_scalar(scalar)), "{scalar:?}");
        }
    }

    #[test]
    fn scalar_width_uses_non_cjk_width() {
        assert_eq!(scalar_width('A'), 1);
        assert_eq!(scalar_width('\u{03b1}'), 1);
        assert_eq!(scalar_width('\u{754c}'), 2);
    }

    #[test]
    fn scalar_width_maps_missing_width_to_one() {
        assert_eq!(
            <char as unicode_width::UnicodeWidthChar>::width('\u{0007}'),
            None
        );
        assert_eq!(scalar_width('\u{0007}'), 1);
    }

    #[test]
    fn combining_scalar_width_is_zero() {
        assert_eq!(scalar_width('\u{0301}'), 0);
        assert_eq!(
            decode_next(b"\xcc\x81", LocaleMode::Utf8),
            Some(DecodedUnit {
                scalar: Some('\u{0301}'),
                byte_len: 2,
                display_width: 0,
            })
        );
    }
}
