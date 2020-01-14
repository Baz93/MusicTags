import os
import re
import regex
import functools
from unidecode import unidecode
from itertools import zip_longest

from config import snapshot_root, music_root
from collection import Snapshots, Collection
from my_tags import *


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


def extract_number(s):
    return (re.findall(r'\d+', s) or [''])[0]


def align(number, digits, default_digits):
    digits = extract_number(digits)
    number = extract_number(number)
    number = number and '0' * (int(digits or default_digits) - len(number)) + number
    return number, digits


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


@recursive_apply
def fix_dashes(s):
    return regex.sub(r'(^|\s)\p{Pd}+(\s|$)', r'\1–\2', s)


@recursive_apply
def fix_pre(s):
    return re.sub(r'\[Pre-', '[pre-', s)


@recursive_apply
def remove_extentions(s):
    s = re.sub(r" \[.*\]$", '', s)
    s = re.sub(r" \{.*\}$", '', s)
    return s


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


@recursive_apply
def rym_escape(s):
    return ''.join(map(rym_escape_character, s))


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


def compress(s):
    if len(s) > 30:
        s = s[:20] + '...' + s[-10:]
    return s


def set_path(tags):
    extension = tags[PATH].split('.')[-1]

    combined_albumartist = '; '.join(tags[ALBUMARTIST])
    combined_artist = '; '.join(tags[EXTENDEDARTIST])
    filename = f'{tags[TRACK]}. ' if tags[TRACK] else ''
    if combined_artist != (combined_albumartist if tags[TRACK] else tags[SERIES]):
        filename += f'{compress(combined_artist)} – '
    filename += compress(tags[EXTENDEDTITLE])

    if tags[TRACK]:
        dirname = tags[YEAR]
        if tags[YEARORDER]:
            dirname += f'({tags[YEARORDER]})'
        dirname += ' – '
        if combined_albumartist != tags[SERIES]:
            dirname += f'{compress(combined_albumartist)} – '
        dirname += compress(tags[EXTENDEDALBUM])
    else:
        dirname = f'0000 – {filename}'

    tokens = [
        tags[GROUP],
        tags[COUNTRY],
        compress(tags[SERIES]),
        dirname,
        '.'.join([filename, extension]),
    ]
    if tags[PATH].startswith('__Unsorted' + os.sep):
        tokens.insert(0, '__Unsorted')
    tokens = [re.sub(r'[/\\?*"<>|:]', '-', token) for token in tokens]
    path = os.path.join(*tokens)
    tags[PATH] = path


def fix(tags):
    for number, digits, default in [
        (TRACK, TRACKDIGITS, 2),
        (YEARORDER, YEARORDERDIGITS, 1),
    ]:
        tags[number], tags[digits] = align(tags[number], tags[digits], default)

    for key in [SERIES, ALBUMARTIST, ALBUM, ALBUMTRANSLATION, ARTIST, ARTISTTRANSLATION, TITLE, TITLETRANSLATION]:
        tags[key] = capitalize(tags[key])
        tags[key] = fix_dashes(tags[key])

    tags[ALBUMARTIST] = fix_pre(tags[ALBUMARTIST])

    tags[RYMARTIST] = rym_escape(remove_extentions(' and '.join(tags[ALBUMARTIST])))
    tags[RYMALBUM] = rym_escape(tags[ALBUM])

    for pattern, rym_type in [
        (r'\b(EP|Demo)\b', 'ep'),
        (r'\bSingle\b', 'single'),
        (r'\bCompilation\b', 'comp'),
    ]:
        if re.search(pattern, tags[ALBUMAPPENDIX]):
            tags[RYMTYPE] = rym_type
            break
    else:
        tags[RYMTYPE] = 'album'

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
        if tags[exception_key] == tags[key]:
            del tags[exception_key]
        tags[key] = tags[exception_key] or tags[key]

    for extended_key, key, key_translation, key_appendix in [
        (EXTENDEDALBUM, ALBUM, ALBUMTRANSLATION, ALBUMAPPENDIX),
        (EXTENDEDARTIST, ARTIST, ARTISTTRANSLATION, ARTISTAPPENDIX),
        (EXTENDEDTITLE, TITLE, TITLETRANSLATION, TITLEAPPENDIX),
    ]:
        values = (tags[key], tags[key_translation], tags[key_appendix])
        if key.multifield:
            values = list(zip_longest(*values))
        tags[extended_key] = compile_extended(values)

    set_path(tags)


def fix_cs(snapshots, cs):
    for fs in cs:
        my_tags = MyTags(snapshots, fs)
        fix(my_tags)
        my_tags.write(fs)


if __name__ == '__main__':
    snapshots = Snapshots(snapshot_root)
    try:
        cs = snapshots.load('data.json')
    except FileNotFoundError:
        cs = None
    collection = Collection(snapshots, music_root, expected_cs=cs)
    cs = collection.state
    cs = sorted(cs, key=lambda fs: fs['path'])

    fix_cs(snapshots, cs)
    
    snapshots.save(cs, 'data.json', sort=False)
    collection.remove_unused_pictures()
