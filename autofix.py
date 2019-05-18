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
    def __init__(self, snapshots, fs):
        self.config = MyConfig()

        self.title = self.config.text_field('TIT2')
        self.title_exception = self.config.text_field('TXXX', 'TITLEEXCEPTION')
        self.title_translation = self.config.text_field('TXXX', 'TITLETRANSLATION')
        self.title_appendix = self.config.text_field('TXXX', 'TITLEAPPENDIX')
        self.extended_title = self.config.text_field('TXXX', 'EXTENDEDTITLE')

        self.artist = self.config.multi_field('TPE1')
        self.artist_exception = self.config.multi_field('TXXX', 'ARTISTEXCEPTION')
        self.artist_translation = self.config.multi_field('TXXX', 'ARTISTTRANSLATION')
        self.artist_appendix = self.config.multi_field('TXXX', 'ARTISTAPPENDIX')
        self.extended_artist = self.config.multi_field('TXXX', 'EXTENDEDARTIST')

        self.track = self.config.text_field('TRCK')
        self.track_digits = self.config.text_field('TXXX', 'TRACKDIGITS')

        self.album = self.config.text_field('TALB')
        self.album_exception = self.config.text_field('TXXX', 'ALBUMEXCEPTION')
        self.album_translation = self.config.text_field('TXXX', 'ALBUMTRANSLATION')
        self.album_appendix = self.config.text_field('TXXX', 'ALBUMAPPENDIX')
        self.extended_album = self.config.text_field('TXXX', 'EXTENDEDALBUM')

        self.year = self.config.text_field('TDRC')
        self.year_order = self.config.text_field('TXXX', 'YEARORDER')
        self.year_order_digits = self.config.text_field('TXXX', 'YEARORDERDIGITS')

        self.albumartist = self.config.multi_field('TPE2')
        self.albumartist_exception = self.config.multi_field('TXXX', 'ALBUMARTISTEXCEPTION')
        self.series = self.config.text_field('TXXX', 'SERIES')
        self.series_exception = self.config.text_field('TXXX', 'SERIESEXCEPTION')
        self.country = self.config.text_field('TXXX', 'COUNTRY')
        self.group = self.config.text_field('TXXX', 'GROUP')

        self.genre = self.config.text_field('TCON')
        self.supergenre = self.config.text_field('TXXX', 'SUPERGENRE')
        self.subgenre = self.config.text_field('TXXX', 'SUBGENRE')
        self.genre_specifier = self.config.text_field('TXXX', 'GENRESPECIFIER')
        self.secondary_genres = self.config.multi_field('TXXX', 'SECONDARYGENRES')

        self.composer = self.config.multi_field('TCOM')
        self.performer = self.config.multi_field('TXXX', 'PERFORMER')

        self.rym_artist = self.config.text_field('TXXX', 'RYMARTIST')
        self.rym_artist_exception = self.config.text_field('TXXX', 'RYMARTISTEXCEPTION')
        self.rym_album = self.config.text_field('TXXX', 'RYMALBUM')
        self.rym_album_exception = self.config.text_field('TXXX', 'RYMALBUMEXCEPTION')
        self.rym_type = self.config.text_field('TXXX', 'RYMTYPE')
        self.rym_type_exception = self.config.text_field('TXXX', 'RYMTYPEEXCEPTION')

        self.picture = self.config.text_field('APIC')
        self.lyrics = self.config.text_field('USLT')

        self.path = fs['path']
        
        self.config.initialize(self)
        self.snapshots = snapshots

        self.config.read(self, fs['tags'])

    def fix(self):
        pass

    def write(self, fs):
        tags = self.config.write(self)
        if fs['path'] == self.path and fs['tags'] == tags:
            return
        fs['path'] = self.path
        fs['tags'] = tags
        fs['modified'] = -1


def fix_cs(snapshots, cs):
    for fs in cs:
        my_tags = MyTags(snapshots, fs)
        my_tags.fix()
        my_tags.write(fs)


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
