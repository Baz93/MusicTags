import os
import json
import hashlib
import mimetypes
import posixpath
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
        assert self.equal(deserialize(result), obj)
        return result
    return with_check


class Snapshots:
    def __init__(self, snapshot_root):
        self.snapshot_root = snapshot_root
        self.picture_dir = posixpath.join(snapshot_root, 'pictures/')
        os.makedirs(self.picture_dir, exist_ok=True)

    def equal(self, lhs, rhs):
        if isinstance(lhs, ID3) and isinstance(rhs, ID3):
            return sorted(map(repr, lhs.items())) == sorted(map(repr, rhs.items()))
        return repr(lhs) == repr(rhs)

    def serialize_picture(self, data, mime):
        name = hashlib.md5(data).hexdigest()
        name += get_extension_by_mime(mime)
        path = posixpath.join(self.picture_dir, name)
        if not posixpath.exists(path):
            with open(path, 'wb') as f:
                f.write(data)
        return name

    def deserialize_picture(self, path):
        path = posixpath.join(self.picture_dir, path)
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

    def _make_frame_snapshot(self, name, has_attr, get_attr, get_pic):
        kw = []
        cls = eval('mutagen.id3.' + name)
        for spec in [cls._framespec, cls._optionalspec]:
            for attr_type in spec:
                attr_name = attr_type.name
                if name == 'APIC' and attr_name == 'mime':
                    continue
                elif name == 'APIC' and attr_name == 'data':
                    path, mime = get_pic()
                    kw.append('path=%r' % path)
                    if mime != get_mime_by_path(path):
                        kw.append('mime=%r' % mime)
                elif has_attr(attr_name):
                    attr = get_attr(attr_name)
                    if attr == attr_type.default:
                        continue
                    attr_snapshot = self.serialize_attr(attr)
                    kw.append('%s=%s' % (attr_name, attr_snapshot))
            return '%s(%s)' % (name, ', '.join(kw))

    @serialize_check
    def serialize_frame(self, frame):
        def get_pic():
            data = frame.data
            mime = frame.mime
            path = self.serialize_picture(data, mime)
            return path, mime

        return self._make_frame_snapshot(
            type(frame).__name__,
            lambda attr: hasattr(frame, attr),
            lambda attr: getattr(frame, attr),
            get_pic
        )

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

    def build_frame_snapshot(self, name, kwargs):
        def get_pic():
            path = kwargs['path']
            if 'mime' in kwargs:
                mime = kwargs['mime']
            else:
                mime = get_mime_by_path(path)
            return path, mime

        return self._make_frame_snapshot(
            name,
            lambda attr: attr in kwargs,
            lambda attr: kwargs[attr],
            get_pic
        )

    @serialize_check
    def serialize_tags(self, tags):
        result = []
        for key in tags:
            frame = tags[key]
            frame_snapshot = self.serialize_frame(frame)
            result.append(frame_snapshot)
        return sorted(result)

    def deserialize_tags(self, tags_snapshot):
        result = ID3()
        for frame_snapshot in tags_snapshot:
            result.add(self.deserialize_frame(frame_snapshot))
        return result

    def save(self, snapshot, name, sort=True):
        path = posixpath.join(self.snapshot_root, name)
        if sort:
            snapshot = sorted(snapshot, key=lambda fs: fs['path'])
        with open(path, 'w', encoding='utf8', newline='\n') as f:
            json.dump(snapshot, f, indent=4, ensure_ascii=False)

    def load(self, name):
        path = posixpath.join(self.snapshot_root, name)
        with open(path, 'r', encoding='utf8') as f:
            snapshot = json.load(f)
        return snapshot

    def filter_pictures(self, rool):
        for filename in os.listdir(self.picture_dir):
            if not rool(filename):
                os.remove(posixpath.join(self.picture_dir, filename))
