from config import snapshot_root, music_root
from collection import Snapshots, Collection

from typing import Union, List


class FieldProto:
    def __init__(self, name, desc=None, multifield=False):
        self.name = name
        self.desc = desc
        self.multifield = multifield


class MyConfig:
    def __init__(self):
        self.fields = {}

    @staticmethod
    def text_field(name, desc=None) -> Union[str, FieldProto]:
        return FieldProto(name, desc)

    @staticmethod
    def multi_field(name, desc=None) -> Union[List[str], FieldProto]:
        return FieldProto(name, desc, multifield=True)

    def initialize(self, obj):
        for attr in dir(obj):
            proto = getattr(obj, attr)
            if isinstance(proto, FieldProto):
                setattr(obj, attr, [] if proto.multifield else '')
                self.fields[(proto.name, proto.desc)] = (attr, proto)

    def read(self, obj, tags):
        for tag in tags:
            name, kwargs = obj.snapshots.parse_frame_snapshot(tag)

            desc = kwargs.get('desc', None)
            if name != 'TXXX':
                desc = None
            if desc is not None:
                desc = desc.upper()

            if (name, desc) not in self.fields:
                continue
            attr, proto = self.fields[(name, desc)]

            if name == 'APIC':
                value = kwargs['path']
            elif name == 'USLT':
                value = kwargs['text']
            else:
                value = kwargs['text']
                if not proto.multifield:
                    value = value[0]

            setattr(obj, attr, value)

    def write(self, obj):
        tags = []
        for (name, desc), (attr, proto) in self.fields.items():
            value = getattr(obj, attr)

            if not value:
                continue

            kwargs = {}
            if name == 'APIC':
                kwargs['path'] = value
            elif name == 'USLT':
                kwargs['lang'] = 'eng'
                kwargs['text'] = value
            else:
                if desc is not None:
                    kwargs['desc'] = desc
                if not proto.multifield:
                    value = [value]
                kwargs['text'] = value

            tag = snapshots.build_frame_snapshot(name, kwargs)
            tags.append(tag)

        tags = sorted(tags)
        return tags


class MyTags:
    config = MyConfig()

    title = config.text_field('TIT2')
    title_exception = config.text_field('TXXX', 'TITLEEXCEPTION')
    title_translation = config.text_field('TXXX', 'TITLETRANSLATION')
    title_appendix = config.text_field('TXXX', 'TITLEAPPENDIX')
    extended_title = config.text_field('TXXX', 'EXTENDEDTITLE')

    artist = config.multi_field('TPE1')
    artist_exception = config.multi_field('TXXX', 'ARTISTEXCEPTION')
    artist_translation = config.multi_field('TXXX', 'ARTISTTRANSLATION')
    artist_appendix = config.multi_field('TXXX', 'ARTISTAPPENDIX')
    extended_artist = config.multi_field('TXXX', 'EXTENDEDARTIST')
    
    track = config.text_field('TRCK')
    track_digits = config.text_field('TXXX', 'TRACKDIGITS')
    
    album = config.text_field('TALB')
    album_exception = config.text_field('TXXX', 'ALBUMEXCEPTION')
    album_translation = config.text_field('TXXX', 'ALBUMTRANSLATION')
    album_appendix = config.text_field('TXXX', 'ALBUMAPPENDIX')
    extended_album = config.text_field('TXXX', 'EXTENDEDALBUM')
    
    year = config.text_field('TDRC')
    year_order = config.text_field('TXXX', 'YEARORDER')
    year_order_digits = config.text_field('TXXX', 'YEARORDERDIGITS')
    
    albumartist = config.multi_field('TPE2')
    albumartist_exception = config.multi_field('TXXX', 'ALBUMARTISTEXCEPTION')
    series = config.text_field('TXXX', 'SERIES')
    series_exception = config.text_field('TXXX', 'SERIESEXCEPTION')
    country = config.text_field('TXXX', 'COUNTRY')
    group = config.text_field('TXXX', 'GROUP')
    
    genre = config.text_field('TCON')
    supergenre = config.text_field('TXXX', 'SUPERGENRE')
    subgenre = config.text_field('TXXX', 'SUBGENRE')
    genre_specifier = config.text_field('TXXX', 'GENRESPECIFIER')
    secondary_genres = config.multi_field('TXXX', 'SECONDARYGENRES')
    
    composer = config.multi_field('TCOM')
    performer = config.multi_field('TXXX', 'PERFORMER')
    
    rym_artist = config.text_field('TXXX', 'RYMARTIST')
    rym_artist_exception = config.text_field('TXXX', 'RYMARTISTEXCEPTION')
    rym_album = config.text_field('TXXX', 'RYMALBUM')
    rym_album_exception = config.text_field('TXXX', 'RYMALBUMEXCEPTION')
    rym_type = config.text_field('TXXX', 'RYMTYPE')
    rym_type_exception = config.text_field('TXXX', 'RYMTYPEEXCEPTION')

    picture = config.text_field('APIC')
    lyrics = config.text_field('USLT')

    def __init__(self, snapshots):
        self.config.initialize(self)
        self.snapshots = snapshots

    def read(self, tags):
        self.config.read(self, tags)

    def fix(self):
        pass

    def write(self):
        return self.config.write(self)


def fix_cs(snapshots, cs):
    for fs in cs:
        my_tags = MyTags(snapshots)
        my_tags.read(fs['tags'])
        my_tags.fix()
        tags = my_tags.write()

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

    fix_cs(snapshots, cs)
    
    snapshots.save(cs, 'data.json')
    collection.remove_unused_pictures()
