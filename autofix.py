from config import snapshot_root, music_root
from collection import Snapshots, Collection

from copy import deepcopy


def fix_tag_desc(tag):
    name, kwargs = snapshots.parse_frame_snapshot(tag)
    if name != 'TXXX':
        return tag
    kwargs['desc'] = kwargs['desc'].upper()
    return snapshots.serialize_frame(snapshots.frame_by_args(name, kwargs))


def useful_tag(tag):
    name, kwargs = snapshots.parse_frame_snapshot(tag)
    if name == 'TXXX':
        return kwargs['desc'] in [
            'GROUP',
            'SERIES',
            'YEARORDER',
            'YEARORDERDIGITS',
            'ALBUMTRANSLATION',
            'ALBUMAPPENDIX',
            'EXTENDEDALBUM',
            'TRACKDIGITS',
            'ARTISTTRANSLATION',
            'ARTISTAPPENDIX',
            'EXTENDEDARTIST',
            'TITLETRANSLATION',
            'TITLEAPPENDIX',
            'EXTENDEDTITLE',
            'COUNTRY',
            'SUPERGENRE',
            'SUBGENRE',
            'GENRESPECIFIER',
            'SECONDARYGENRES',
            'PERFORMER',
            'RYMARTIST',
            'RYMALBUM',
            'RYMTYPE',
            'SERIESEXCEPTION',
            'ALBUMARTISTEXCEPTION',
            'ALBUMEXCEPTION',
            'ARTISTEXCEPTION',
            'TITLEEXCEPTION',
            'RYMARTISTEXCEPTION',
            'RYMALBUMEXCEPTION',
            'RYMTYPEEXCEPTION',
        ]
    return name in [
        'TDRC',
        'TPE1',
        'TALB',
        'TRCK',
        'TPE2',
        'TIT2',
        'TCON',
        'APIC',
        'USLT',
        'TCOM',
    ]


def fix_cs(cs):
    for fs in cs:
        tags = deepcopy(fs['tags'])
        tags = list(filter(useful_tag, map(fix_tag_desc, tags)))

        if fs['tags'] != tags:
            fs['tags'] = tags
            fs['modified'] = -1


if __name__ == '__main__':
    snapshots = Snapshots(snapshot_root)
    try:
        cs = snapshots.load('data.json')
    except FileNotFoundError:
        cs = None
    collection = Collection(snapshots, music_root, expected_cs=cs)
    cs = collection.state

    fix_cs(cs)
    
    snapshots.save(cs, 'data.json')
    collection.remove_unused_pictures()
