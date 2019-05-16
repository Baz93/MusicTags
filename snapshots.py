import os
import json
import hashlib
import mimetypes
from functools import wraps

from mutagen.id3 import ID3, PictureType, Encoding, ID3TimeStamp
import mutagen.id3


def replace_default(frame_type, name, default):
    for spec in frame_type._framespec:
        if spec.name == name:
            spec.default = default


replace_default(mutagen.id3.APIC, 'encoding', Encoding.LATIN1)
replace_default(mutagen.id3.TDRC, 'encoding', Encoding.LATIN1)
replace_default(mutagen.id3.TRCK, 'encoding', Encoding.LATIN1)


def get_extension_by_mime(mime):
    extension = mimetypes.guess_extension(mime, strict=False)
    if extension == '.jpe':
        extension = '.jpg'
    return extension


def get_mime_by_path(path):
    return mimetypes.guess_type(path)[0]


def get_kwargs(**kwargs):
    return kwargs


def serialize_check(serialize):
    @wraps(serialize)
    def with_check(self, obj):
        result = serialize(self, obj)
        deserialize = getattr(self, 'de' + serialize.__name__)
        assert repr(deserialize(result)) == repr(obj)
        return result
    return with_check


class Snapshots:
    def __init__(self, snapshot_root):
        self.snapshot_root = snapshot_root
        self.picture_dir = os.path.join(snapshot_root, 'pictures/')
        os.makedirs(self.picture_dir, exist_ok=True)

    def serialize_picture(self, data, mime):
        name = hashlib.md5(data).hexdigest()
        name += get_extension_by_mime(mime)
        path = os.path.join(self.picture_dir, name)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(data)
        return name

    def deserialize_picture(self, path):
        path = os.path.join(self.picture_dir, path)
        with open(path, 'rb') as f:
            data = f.read()
        return data

    @serialize_check
    def serialize_attr(self, attr):
        if type(attr) in [Encoding, PictureType]:
            return str(attr)
        elif type(attr) in [ID3TimeStamp]:
            return "%s(%r)" % (type(attr).__name__, attr)
        else:
            result = repr(attr)
        return result

    def deserialize_attr(self, attr_snapshot):
        return eval(attr_snapshot)

    @serialize_check
    def serialize_frame(self, frame):
        kw = []
        for spec in [frame._framespec, frame._optionalspec]:
            for attr_type in spec:
                if hasattr(frame, attr_type.name):
                    if type(frame) == mutagen.id3.APIC and attr_type.name == 'mime':
                        continue
                    if type(frame) == mutagen.id3.APIC and attr_type.name == 'data':
                        data = frame.data
                        mime = frame.mime
                        path = self.serialize_picture(data, mime)
                        kw.append('path=%r' % path)
                        if mime != get_mime_by_path(path):
                            kw.append('mime=%r' % mime)
                    else:
                        attr = getattr(frame, attr_type.name)
                        if attr == attr_type.default:
                            continue
                        attr_snapshot = self.serialize_attr(attr)
                        kw.append('%s=%s' % (attr_type.name, attr_snapshot))
            return '%s(%s)' % (type(frame).__name__, ', '.join(kw))

    def APIC(self, *args, **kwargs):
        if 'mime' not in kwargs and 'path' in kwargs:
            kwargs['mime'] = get_mime_by_path(kwargs['path'])
        if 'data' not in kwargs and 'path' in kwargs:
            kwargs['data'] = self.deserialize_picture(kwargs['path'])
        return mutagen.id3.APIC(*args, **kwargs)

    def deserialize_frame(self, frame_snapshot):
        prefix = 'self.' if frame_snapshot.startswith('APIC') else 'mutagen.id3.'
        return eval(prefix + frame_snapshot)

    def parse_frame_snapshot(self, frame_snapshot):
        name = frame_snapshot[:4]
        kwargs = eval('get_kwargs' + frame_snapshot[4:])
        return name, kwargs

    def frame_by_args(self, name, kwargs):
        prefix = 'self.' if name == 'APIC' else 'mutagen.id3.'
        return eval(prefix + name)(**kwargs)

    @serialize_check
    def serialize_tags(self, tags):
        result = []
        for key in tags:
            frame = tags[key]
            frame_snapshot = self.serialize_frame(frame)
            result.append(frame_snapshot)
        return result

    def deserialize_tags(self, tags_snapshot):
        result = ID3()
        for frame_snapshot in tags_snapshot:
            result.add(self.deserialize_frame(frame_snapshot))
        return result

    def save(self, snapshot, name):
        path = os.path.join(self.snapshot_root, name)
        with open(path, 'w') as f:
            json.dump(sorted(snapshot, key=lambda fs: fs['path']), f, indent=4, ensure_ascii=False)

    def load(self, name):
        path = os.path.join(self.snapshot_root, name)
        with open(path, 'r') as f:
            snapshot = json.load(f)
        return snapshot

    def filter_pictures(self, rool):
        for filename in os.listdir(self.picture_dir):
            if not rool(filename):
                os.remove(os.path.join(self.picture_dir, filename))
