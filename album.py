import os
import re
from collections import OrderedDict
from copy import deepcopy
from typing import List

import regex
import functools
from unidecode import unidecode
from itertools import zip_longest

from config import snapshot_root, music_root
from collection import Snapshots, Collection
from my_tags import *
from autofix import capitalize, fix_dashes


unsorted_folder = '__Unsorted'


def bool_box():
    while True:
        s = input().lower()
        if s == 'y' or s == 'yes':
            return True
        if s == 'n' or s == 'no':
            return False


def input_box(multiline=False, suggestions=None, fixes=None):
    if suggestions is None:
        suggestions = []
    if fixes is None:
        fixes = []

    print("Suggestions:")
    for i, suggestion in enumerate(suggestions):
        print("{}. {}".format(i + 1, suggestion))

    if multiline:
        result = []
        while True:
            s = input()
            if not s:
                break
            result.append(s)
    else:
        result = input()

    for fix in fixes:
        fixed_result = fix(result)
        if fixed_result == result:
            continue
        print("Apply the following fix?")
        if isinstance(fixed_result, list):
            for s in fixed_result:
                print(s)
        else:
            print(fixed_result)
        if bool_box():
            result = fixed_result

    return result


def get_suggestions(tags, tag_keys):
    suggestions = OrderedDict()
    for tag_key in tag_keys:
        for tags in tags:
            values = tags[tag_key]
            if not values:
                continue
            for value in values if isinstance(values, list) else [values]:
                if value not in suggestions:
                    suggestions[value] = None
    return suggestions.values()


def fix(snapshots, album_tracks):
    album_tags = [MyTags(snapshots, fs) for fs in album_tracks]

    value = input_box(suggestions=get_suggestions(album_tags, [GROUP]))
    for fs in album_tracks:
        fs[GROUP] = value

    value = input_box(suggestions=get_suggestions(album_tags, [SERIESEXCEPTION, SERIES]))
    for fs in album_tracks:
        fs[SERIES] = value
        fs[SERIESEXCEPTION] = value

    value = input_box(suggestions=get_suggestions(album_tags, [COUNTRY]))
    for fs in album_tracks:
        fs[COUNTRY] = value

    value = input_box(multiline=True, suggestions=get_suggestions(album_tags, [ALBUMARTISTEXCEPTION, ALBUMARTIST, SERIESEXCEPTION, SERIES]))
    for fs in album_tracks:
        fs[ALBUMARTIST] = value
        fs[ALBUMARTISTEXCEPTION] = value

    value = input_box(suggestions=get_suggestions(album_tags, [ALBUMEXCEPTION. ALBUM]), fixes=[capitalize, fix_dashes])
    for fs in album_tracks:
        fs[ALBUM] = value
        fs[ALBUMEXCEPTION] = value

    value = input_box(suggestions=get_suggestions(album_tags, [ALBUMTRANSLATION]), fixes=[capitalize, fix_dashes])
    for fs in album_tracks:
        fs[ALBUMTRANSLATION] = value

    value = input_box(suggestions=get_suggestions(album_tags, [ALBUMAPPENDIX]), fixes=[capitalize, fix_dashes])
    for fs in album_tracks:
        fs[ALBUMAPPENDIX] = value



