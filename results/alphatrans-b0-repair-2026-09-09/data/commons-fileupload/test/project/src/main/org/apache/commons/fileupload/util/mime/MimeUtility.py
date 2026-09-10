from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.fileupload.util.mime.QuotedPrintableDecoder import *
from src.main.org.apache.commons.fileupload.util.mime.ParseException import *
from src.main.org.apache.commons.fileupload.util.mime.Base64Decoder import *
import typing
from typing import *
import io

# Imports End


class UnsupportedEncodingException(Exception):
    """Raised when an encoding is not supported."""
    pass


class MimeUtility:

    # Class Fields Begin
    __US_ASCII_CHARSET: str = "US-ASCII"
    __BASE64_ENCODING_MARKER: str = "B"
    __QUOTEDPRINTABLE_ENCODING_MARKER: str = "Q"
    __ENCODED_TOKEN_MARKER: str = "=?"
    __ENCODED_TOKEN_FINISHER: str = "?="
    __LINEAR_WHITESPACE: str = " \t\r\n"
    __MIME2JAVA: typing.Dict[str, str] = {
        "iso-2022-cn": "ISO2022CN",
        "iso-2022-kr": "ISO2022KR",
        "utf-8": "UTF8",
        "utf8": "UTF8",
        "ja_jp.iso2022-7": "ISO2022JP",
        "ja_jp.eucjp": "EUCJIS",
        "euc-kr": "KSC5601",
        "euckr": "KSC5601",
        "us-ascii": "ISO-8859-1",
        "x-us-ascii": "ISO-8859-1",
    }
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def decodeText(text: str) -> str:
        if text.find(MimeUtility.__ENCODED_TOKEN_MARKER) < 0:
            return text

        offset = 0
        end_offset = len(text)

        start_white_space = -1
        end_white_space = -1

        decoded_text = io.StringIO()

        previous_token_encoded = False

        while offset < end_offset:
            ch = text[offset]

            if ch in MimeUtility.__LINEAR_WHITESPACE:
                start_white_space = offset
                while offset < end_offset:
                    ch = text[offset]
                    if ch in MimeUtility.__LINEAR_WHITESPACE:
                        offset += 1
                    else:
                        end_white_space = offset
                        break
            else:
                word_start = offset

                while offset < end_offset:
                    ch = text[offset]
                    if ch not in MimeUtility.__LINEAR_WHITESPACE:
                        offset += 1
                    else:
                        break
                word = text[word_start:offset]
                if word.startswith(MimeUtility.__ENCODED_TOKEN_MARKER):
                    try:
                        decoded_word = MimeUtility.__decodeWord(word)

                        if not previous_token_encoded and start_white_space != -1:
                            decoded_text.write(text[start_white_space:end_white_space])
                            start_white_space = -1
                        previous_token_encoded = True
                        decoded_text.write(decoded_word)
                        continue
                    except ParseException:
                        pass
                if start_white_space != -1:
                    decoded_text.write(text[start_white_space:end_white_space])
                    start_white_space = -1
                previous_token_encoded = False
                decoded_text.write(word)

        return decoded_text.getvalue()

    @staticmethod
    def __javaCharset(charset: str) -> str:
        if charset is None:
            return None

        mapped_charset = MimeUtility.__MIME2JAVA.get(charset.lower())
        if mapped_charset is None:
            return charset
        return mapped_charset

    @staticmethod
    def __decodeWord(word: str) -> str:
        if not word.startswith(MimeUtility.__ENCODED_TOKEN_MARKER):
            raise ParseException("Invalid RFC 2047 encoded-word: " + word)

        charset_pos = word.find('?', 2)
        if charset_pos == -1:
            raise ParseException("Missing charset in RFC 2047 encoded-word: " + word)

        charset = word[2:charset_pos].lower()

        encoding_pos = word.find('?', charset_pos + 1)
        if encoding_pos == -1:
            raise ParseException("Missing encoding in RFC 2047 encoded-word: " + word)

        encoding = word[charset_pos + 1:encoding_pos]

        encoded_text_pos = word.find(MimeUtility.__ENCODED_TOKEN_FINISHER, encoding_pos + 1)
        if encoded_text_pos == -1:
            raise ParseException("Missing encoded text in RFC 2047 encoded-word: " + word)

        encoded_text = word[encoding_pos + 1:encoded_text_pos]

        if len(encoded_text) == 0:
            return ""

        try:
            out = io.BytesIO()

            encoded_data = encoded_text.encode(MimeUtility.__US_ASCII_CHARSET.lower().replace("-", "_"))

            if encoding == MimeUtility.__BASE64_ENCODING_MARKER:
                Base64Decoder.decode(encoded_data, out)
            elif encoding == MimeUtility.__QUOTEDPRINTABLE_ENCODING_MARKER:
                QuotedPrintableDecoder.decode(encoded_data, out)
            else:
                raise UnsupportedEncodingException("Unknown RFC 2047 encoding: " + encoding)

            decoded_data = out.getvalue()
            java_charset = MimeUtility.__javaCharset(charset)
            try:
                # Mirrors Java's `new String(bytes, charsetName)` semantics:
                # malformed or unmappable byte sequences are substituted
                # rather than raising an error. Only an unrecognized charset
                # name should result in UnsupportedEncodingException.
                return decoded_data.decode(java_charset, errors="replace")
            except LookupError:
                raise UnsupportedEncodingException(java_charset)
        except UnsupportedEncodingException:
            raise
        except IOError as e:
            # Mirrors Java's `catch (IOException e) { throw new ParseException(...) }`
            # This allows decodeText to gracefully fall back to the raw,
            # undecoded token when the encoded payload itself is malformed
            # (as opposed to an unsupported/unknown encoding marker, which
            # should propagate as UnsupportedEncodingException above).
            raise ParseException(str(e))

    def __init__(self) -> None:
        pass

    # Class Methods End
