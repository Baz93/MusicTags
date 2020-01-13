import re
import regex
import functools
from unidecode import unidecode
from itertools import zip_longest

from my_fields import *


def recursive_apply(f):
    @functools.wraps(f)
    def g(s, *args, **kwargs):
        if isinstance(s, list):
            return [g(x, *args, **kwargs) for x in s]
        return f(s, *args, **kwargs)
    return g


roman_number_pattern = re.compile(
    r'\b(?i:(?=[MDCLXVI])((M{0,3})((C[DM])|(D?C{0,3}))?((X[LC])|(L?X{0,3})|L)?((I[VX])|(V?(I{0,3}))|V)?))\b'
)


class MyTags(MyTagsBase):
    @staticmethod
    def extract_number(s):
        return (re.findall(r'\d+', s) or [''])[0]

    @staticmethod
    def align(number, digits, default_digits):
        digits = MyTags.extract_number(digits)
        number = MyTags.extract_number(number)
        number = number and '0' * (int(digits or default_digits) - len(number)) + number
        return number, digits

    @staticmethod
    @recursive_apply
    def capitalize(s):
        s = re.sub(r'^\s+|\s+$', r'', s)  # trim
        s = re.sub(r'\s+', r' ', s)  # remove extra spaces
        s = s.lower()
        s = re.sub(r'(^|(?<=[^\w\'])|(?<=\W\'))\w', lambda match: match.group(0).upper(), s)  # mixed case
        s = re.sub(r'(?<=\bO\')\w', lambda match: match.group(0).upper(), s)  # for cases like O'Bannon
        s = re.sub(roman_number_pattern, lambda match: match.group(0).upper(), s)  # fix roman numbers
        s = re.sub(r'\'M\b', r"'m", s)
        s = re.sub(r'\bMIX\b', r'Mix', s)
        s = re.sub(r'\bOst\b', r'OST', s)
        s = re.sub(r'\bDj\b', r'DJ', s)
        return s

    @staticmethod
    @recursive_apply
    def fix_dashes(s):
        return regex.sub(r'(^|\s)\p{Pd}+(\s|$)', r'\1–\2', s)

    @staticmethod
    @recursive_apply
    def fix_pre(s):
        return re.sub(r'\[Pre-', '[pre-', s)

    @staticmethod
    @recursive_apply
    def remove_extentions(s):
        s = re.sub(r" \[.*\]$", '', s)
        s = re.sub(r" \{.*\}$", '', s)
        return s

    @staticmethod
    def rym_escape_character(s):
        s = s.lower()

        d = {
            '–': '_',
            '[': '[',
            ']': ']',
        }
        if s in d:
            return d[s]

        if not regex.fullmatch(r'\p{IsLatin}|\p{ASCII}', s):
            return s

        d = {
            'þ': 'd',
        }
        if s in d:
            return d[s]

        s = unidecode(s)
        d = {
            ' ': '_',
            '&': 'and',
            '"': '',
            "'": '',
        }
        if s in d:
            return d[s]

        if re.fullmatch(r'\W', s):
            return '_'
        return s

    @staticmethod
    @recursive_apply
    def rym_escape(s):
        return ''.join(map(MyTags.rym_escape_character, s))

    @staticmethod
    @recursive_apply
    def compile_extended(values):
        s, s_translation, s_appendix = values
        l = []
        if s:
            l.append(s)
        if s_translation:
            l.append(f'{{{s_translation}}}')
        if s_appendix:
            l.append(f'[{s_appendix}]')
        return ' '.join(l)

    def fix(self):
        for number, digits, default in [
            (TRACK, TRACKDIGITS, 2),
            (YEARORDER, YEARORDERDIGITS, 1),
        ]:
            self[number], self[digits] = self.align(self[number], self[digits], default)

        for key in [SERIES, ALBUMARTIST, ALBUM, ALBUMTRANSLATION, ARTIST, ARTISTTRANSLATION, TITLE, TITLETRANSLATION]:
            self[key] = self.capitalize(self[key])
            self[key] = self.fix_dashes(self[key])

        self[ALBUMARTIST] = self.fix_pre(self[ALBUMARTIST])

        self[RYMARTIST] = self.rym_escape(self.remove_extentions(' and '.join(self[ALBUMARTIST])))
        self[RYMALBUM] = self.rym_escape(self[ALBUM])

        for pattern, rym_type in [
            (r'\b(EP|Demo)\b', 'ep'),
            (r'\bSingle\b', 'single'),
            (r'\bCompilation\b', 'comp'),
        ]:
            if re.search(pattern, self[ALBUMAPPENDIX]):
                self[RYMTYPE] = rym_type
                break
        else:
            self[RYMTYPE] = 'album'

        for key, exception_key in [
            (SERIES, SERIESEXCEPTION),
            (ALBUMARTIST, ALBUMARTISTEXCEPTION),
            (ALBUM, ALBUMEXCEPTION),
            (ARTIST, ARTISTEXCEPTION),
            (TITLE, TITLEEXCEPTION),
            (RYMALBUM, RYMALBUMEXCEPTION),
            (RYMARTIST, RYMARTISTEXCEPTION),
            (RYMTYPE, RYMTYPEEXCEPTION),
        ]:
            if self[exception_key] == self[key]:
                del self[exception_key]
            self[key] = self[exception_key] or self[key]

        for extended_key, key, key_translation, key_appendix in [
            (EXTENDEDALBUM, ALBUM, ALBUMTRANSLATION, ALBUMAPPENDIX),
            (EXTENDEDARTIST, ARTIST, ARTISTTRANSLATION, ARTISTAPPENDIX),
            (EXTENDEDTITLE, TITLE, TITLETRANSLATION, TITLEAPPENDIX),
        ]:
            values = (self[key], self[key_translation], self[key_appendix])
            if key.multifield:
                values = list(zip_longest(*values))
            self[extended_key] = self.compile_extended(values)
