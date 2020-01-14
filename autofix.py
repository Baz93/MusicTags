import os
import re
import regex
import functools
from unidecode import unidecode
from itertools import zip_longest

from config import snapshot_root, music_root
from collection import Snapshots, Collection
from my_tags import *


unsorted_folder = '__Unsorted'


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


def extract_number(tags, key):
    number = (re.findall(r'\d+', tags[key]) or [''])[0]
    tags[key] = number
    return number


def align(tags, number_key, digits_key, default_digits):
    digits = extract_number(tags, digits_key) or default_digits
    number = extract_number(tags, number_key)
    if number:
        tags[number_key] = '0' * (int(digits) - len(number)) + number


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


def fix_exception(tags, key, exception_key):
    if tags[exception_key] == tags[key]:
        del tags[exception_key]
    tags[key] = tags[exception_key] or tags[key]


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


def extract_group(path):
    tokens = path.split(os.sep)
    if tokens[0] == unsorted_folder:
        return tokens[1]
    return tokens[0]


def compress(s):
    if len(s) > 30:
        s = s[:20] + '...' + s[-10:]
    return s


def set_rym_values(tags):
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
    if tags[PATH].startswith(unsorted_folder + os.sep):
        tokens.insert(0, unsorted_folder)
    tokens = [re.sub(r'[/\\?*"<>|:]', '-', token) for token in tokens]
    path = os.path.join(*tokens)
    tags[PATH] = path


def fix(tags):
    align(tags, TRACK, TRACKDIGITS, 2)
    align(tags, YEARORDER, YEARORDERDIGITS, 1)

    for key in [SERIES, ALBUMARTIST, ALBUM, ALBUMTRANSLATION, ARTIST, ARTISTTRANSLATION, TITLE, TITLETRANSLATION]:
        tags[key] = capitalize(tags[key])
        tags[key] = fix_dashes(tags[key])

    tags[ALBUMARTIST] = fix_pre(tags[ALBUMARTIST])

    fix_exception(tags, SERIES, SERIESEXCEPTION)
    fix_exception(tags, ALBUMARTIST, ALBUMARTISTEXCEPTION)
    fix_exception(tags, ALBUM, ALBUMEXCEPTION)
    fix_exception(tags, ARTIST, ARTISTEXCEPTION)
    fix_exception(tags, TITLE, TITLEEXCEPTION)

    for extended_key, key, key_translation, key_appendix in [
        (EXTENDEDALBUM, ALBUM, ALBUMTRANSLATION, ALBUMAPPENDIX),
        (EXTENDEDARTIST, ARTIST, ARTISTTRANSLATION, ARTISTAPPENDIX),
        (EXTENDEDTITLE, TITLE, TITLETRANSLATION, TITLEAPPENDIX),
    ]:
        values = (tags[key], tags[key_translation], tags[key_appendix])
        if key.multifield:
            values = list(zip_longest(*values))
        tags[extended_key] = compile_extended(values)

    tags[ALBUMARTIST] = tags[ALBUMARTIST] or tags[EXTENDEDARTIST]
    tags[SERIES] = tags[SERIES] or (tags[ALBUMARTIST][0] if len(tags[ALBUMARTIST]) == 1 else "Various Artists")
    tags[COUNTRY] = tags[COUNTRY] or 'Unknown'
    tags[GROUP] = tags[GROUP] or extract_group(tags[PATH])

    set_rym_values(tags)

    fix_exception(tags, RYMALBUM, RYMALBUMEXCEPTION)
    fix_exception(tags, RYMARTIST, RYMARTISTEXCEPTION)
    fix_exception(tags, RYMTYPE, RYMTYPEEXCEPTION)

    set_path(tags)


def fix_cs(snapshots, cs):
    for fs in cs:
        if fs['path'].startswith(unsorted_folder + os.sep):
            continue
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
