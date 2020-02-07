from simple_tags import SimpleTags


class MyTags(SimpleTags):
    pass


MyTags.clear_storage()


PATH = MyTags.register_tag('PATH')

TITLE = MyTags.register_tag('TIT2')
TITLEEXCEPTION = MyTags.register_tag('TXXX')
TITLETRANSLATION = MyTags.register_tag('TXXX')
TITLEAPPENDIX = MyTags.register_tag('TXXX')
EXTENDEDTITLE = MyTags.register_tag('TXXX')

ARTIST = MyTags.register_tag('TPE1', multifield=True)
ARTISTEXCEPTION = MyTags.register_tag('TXXX', multifield=True)
ARTISTTRANSLATION = MyTags.register_tag('TXXX', multifield=True)
ARTISTAPPENDIX = MyTags.register_tag('TXXX', multifield=True)
EXTENDEDARTIST = MyTags.register_tag('TXXX', multifield=True)

TRACK = MyTags.register_tag('TRCK')
TRACKDIGITS = MyTags.register_tag('TXXX')

ALBUM = MyTags.register_tag('TALB')
ALBUMEXCEPTION = MyTags.register_tag('TXXX')
ALBUMTRANSLATION = MyTags.register_tag('TXXX')
ALBUMAPPENDIX = MyTags.register_tag('TXXX')
EXTENDEDALBUM = MyTags.register_tag('TXXX')

YEAR = MyTags.register_tag('TDRC')
YEARORDER = MyTags.register_tag('TXXX')
YEARORDERDIGITS = MyTags.register_tag('TXXX')

ALBUMARTIST = MyTags.register_tag('TPE2', multifield=True)
ALBUMARTISTEXCEPTION = MyTags.register_tag('TXXX', multifield=True)
SERIES = MyTags.register_tag('TXXX')
SERIESEXCEPTION = MyTags.register_tag('TXXX')
COUNTRY = MyTags.register_tag('TXXX')
GROUP = MyTags.register_tag('TXXX')

GENRE = MyTags.register_tag('TCON')
SUPERGENRE = MyTags.register_tag('TXXX')
SUBGENRE = MyTags.register_tag('TXXX')
GENRESPECIFIER = MyTags.register_tag('TXXX')
SECONDARYGENRES = MyTags.register_tag('TXXX', multifield=True)

COMPOSER = MyTags.register_tag('TCOM', multifield=True)
PERFORMER = MyTags.register_tag('TXXX', multifield=True)

RYMARTIST = MyTags.register_tag('TXXX')
RYMARTISTEXCEPTION = MyTags.register_tag('TXXX')
RYMALBUM = MyTags.register_tag('TXXX')
RYMALBUMEXCEPTION = MyTags.register_tag('TXXX')
RYMTYPE = MyTags.register_tag('TXXX')
RYMTYPEEXCEPTION = MyTags.register_tag('TXXX')

PICTURE = MyTags.register_tag('APIC')
LYRICS = MyTags.register_tag('USLT')


MyTags.finalize_storage(locals())
