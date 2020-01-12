import re
import functools

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
    def align(digits, number, default_digits):
        digits = MyTags.extract_number(digits)
        number = MyTags.extract_number(number)
        number = number and '0' * (int(digits or default_digits) - len(number)) + number
        return digits, number

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
    def fix_pre(s):
        s = re.sub(r'\[Pre-', '[pre-', s)
        return s

    def fix(self):
        for digits, number, default in [
            (TRACKDIGITS, TRACK, 2),
            (YEARORDERDIGITS, YEARORDER, 1),
        ]:
            self[digits], self[number] = self.align(self[digits], self[number], default)

        for key in [SERIES, ALBUMARTIST, ALBUM, ALBUMTRANSLATION, ARTIST, ARTISTTRANSLATION, TITLE, TITLETRANSLATION]:
            self[key] = self.capitalize(self[key])

        self[ALBUMARTIST] = self.fix_pre(self[ALBUMARTIST])

        for key, exception_key in [
            (SERIES, SERIESEXCEPTION),
            (ALBUMARTIST, ALBUMARTISTEXCEPTION),
            (ALBUM, ALBUMEXCEPTION),
            (ARTIST, ARTISTEXCEPTION),
            (TITLE, TITLEEXCEPTION),
        ]:
            self[key] = self[exception_key] or self[key]
