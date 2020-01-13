from simple_tags import FieldProto, filter_proto, simple_tags


assert filter_proto(locals()) == {}


PATH = FieldProto('PATH')

TITLE = FieldProto('TIT2')
TITLEEXCEPTION = FieldProto('TXXX')
TITLETRANSLATION = FieldProto('TXXX')
TITLEAPPENDIX = FieldProto('TXXX')
EXTENDEDTITLE = FieldProto('TXXX')

ARTIST = FieldProto('TPE1', multifield=True)
ARTISTEXCEPTION = FieldProto('TXXX', multifield=True)
ARTISTTRANSLATION = FieldProto('TXXX', multifield=True)
ARTISTAPPENDIX = FieldProto('TXXX', multifield=True)
EXTENDEDARTIST = FieldProto('TXXX', multifield=True)

TRACK = FieldProto('TRCK')
TRACKDIGITS = FieldProto('TXXX')

ALBUM = FieldProto('TALB')
ALBUMEXCEPTION = FieldProto('TXXX')
ALBUMTRANSLATION = FieldProto('TXXX')
ALBUMAPPENDIX = FieldProto('TXXX')
EXTENDEDALBUM = FieldProto('TXXX')

YEAR = FieldProto('TDRC')
YEARORDER = FieldProto('TXXX')
YEARORDERDIGITS = FieldProto('TXXX')

ALBUMARTIST = FieldProto('TPE2', multifield=True)
ALBUMARTISTEXCEPTION = FieldProto('TXXX', multifield=True)
SERIES = FieldProto('TXXX')
SERIESEXCEPTION = FieldProto('TXXX')
COUNTRY = FieldProto('TXXX')
GROUP = FieldProto('TXXX')

GENRE = FieldProto('TCON')
SUPERGENRE = FieldProto('TXXX')
SUBGENRE = FieldProto('TXXX')
GENRESPECIFIER = FieldProto('TXXX')
SECONDARYGENRES = FieldProto('TXXX', multifield=True)

COMPOSER = FieldProto('TCOM', multifield=True)
PERFORMER = FieldProto('TXXX', multifield=True)

RYMARTIST = FieldProto('TXXX')
RYMARTISTEXCEPTION = FieldProto('TXXX')
RYMALBUM = FieldProto('TXXX')
RYMALBUMEXCEPTION = FieldProto('TXXX')
RYMTYPE = FieldProto('TXXX')
RYMTYPEEXCEPTION = FieldProto('TXXX')

PICTURE = FieldProto('APIC')
LYRICS = FieldProto('USLT')


MyTags = simple_tags(filter_proto(locals()))
