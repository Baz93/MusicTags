import shutil
from collections import OrderedDict

from mutagen.id3 import ID3
from mutagen.id3._specs import Encoding, PictureType, ID3TimeStamp
import mutagen.id3
import os
import json
import hashlib
import mimetypes


def get_extension_by_mime(mime):
    extension = mimetypes.guess_extension(mime, strict=False)
    if extension == '.jpe':
        extension = '.jpg'
    return extension


def get_mime_by_path(path):
    return mimetypes.guess_type(path)[0]


def replace_default(frame_type, name, default):
    for spec in frame_type._framespec:
        if spec.name == name:
            spec.default = default


replace_default(mutagen.id3.APIC, 'encoding', Encoding.LATIN1)
replace_default(mutagen.id3.TDRC, 'encoding', Encoding.LATIN1)
replace_default(mutagen.id3.TRCK, 'encoding', Encoding.LATIN1)


def APIC_init_modifier(init):
    def new_init(self, *args, **kwargs):
        if 'mime' not in kwargs and 'path' in kwargs:
            kwargs['mime'] = get_mime_by_path(kwargs['path'])
        if 'data' not in kwargs and 'path' in kwargs:
            kwargs['data'] = load_picture(kwargs['path'])
        init(self, *args, **kwargs)
    return new_init


mutagen.id3.APIC.__init__ = APIC_init_modifier(mutagen.id3.APIC.__init__)


music_root = '/mnt/c/Users/Vasiliy Mokin/Music/'
snapshot_root = '/mnt/c/Programming/MusicTagsSnapshot'
picture_dir = os.path.join(snapshot_root, 'pictures/')
data_file = os.path.join(snapshot_root, 'data.json')


def music_search(path, res):
    if os.path.isfile(path):
        if path.endswith('.mp3'):
            res.append(path)
        else:
            print('Bad extension:', path)
        return

    for f in os.listdir(path):
        music_search(os.path.join(path, f), res)


def save_picture(data, mime):
    name = hashlib.md5(data).hexdigest()
    name += get_extension_by_mime(mime)
    path = os.path.join(picture_dir, name)
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.write(data)
    return name


def load_picture(path):
    path = os.path.join(picture_dir, path)
    with open(path, 'rb') as f:
        data = f.read()
    return data


def save_attr(attr):
    if type(attr) in [Encoding, PictureType]:
        return str(attr)
    elif type(attr) in [ID3TimeStamp]:
        return "%s(%r)" % (type(attr).__name__, attr)
    else:
        result = repr(attr)
    return result


def load_attr(attr_snapshot):
    return eval(attr_snapshot)


def save_frame(frame):
    kw = []
    for spec in [frame._framespec, frame._optionalspec]:
        for attr_type in spec:
            if hasattr(frame, attr_type.name):
                if type(frame) == mutagen.id3.APIC and attr_type.name == 'mime':
                    continue
                if type(frame) == mutagen.id3.APIC and attr_type.name == 'data':
                    data = frame.data
                    mime = frame.mime
                    path = save_picture(data, mime)
                    kw.append('path=%r' % path)
                    if mime != get_mime_by_path(path):
                        kw.append('mime=%r' % mime)
                else:
                    attr = getattr(frame, attr_type.name)
                    if attr == attr_type.default:
                        continue
                    attr_snapshot = save_attr(attr)
                    # assert repr(load_attr(attr_snapshot)) == repr(attr)
                    kw.append('%s=%s' % (attr_type.name, attr_snapshot))
        return '%s(%s)' % (type(frame).__name__, ', '.join(kw))


def load_frame(frame_snapshot):
    return eval('mutagen.id3.' + frame_snapshot)


def save_tags(tags):
    result = []
    for key in tags:
        frame = tags[key]
        frame_snapshot = save_frame(frame)
        # assert repr(load_frame(frame_snapshot)) == repr(frame)
        result.append(frame_snapshot)
    return result


def load_tags(tags_snapshot):
    result = ID3()
    for frame_snapshot in tags_snapshot:
        result.add(load_frame(frame_snapshot))
    return result


def read_config(path):
    config = OrderedDict()
    config['path'] = path
    tags = ID3(path)
    tags_snapshot = save_tags(tags)
    assert repr(load_tags(tags_snapshot)) == repr(tags)
    config['tags'] = tags_snapshot
    return config


if __name__ == '__main__':
    if os.path.exists(picture_dir):
        shutil.rmtree(picture_dir)
    os.makedirs(picture_dir)

    files = []

    music_search(music_root, files)

    data = []

    for num, file in enumerate(files):
        print("%d/%d" % (num + 1, len(files)), file)
        config = read_config(file)
        data.append(config)

    with open(data_file, 'w') as out:
        json.dump(data, out, indent=4, ensure_ascii=False)
