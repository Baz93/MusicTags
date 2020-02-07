from collections import OrderedDict
from typing import Any, List, Mapping, Optional


class FieldProto:
    def __init__(self, frame, desc=None, multifield=False):
        self.name = None
        self.frame = frame
        self.desc = desc
        self.multifield = multifield

    def set_name(self, name):
        self.name = name
        if self.frame == 'TXXX' and self.desc is None:
            self.desc = name.upper()

    def key(self):
        return self.frame, self.desc


class FieldStorage:
    class FieldStorageFinalizeError(Exception):
        def __init__(self, field, names):
            self.field = field
            self.names = names

        def __str__(self):
            return (
                f'For field (id={id(self.field)}, frame={self.field.frame}, desc={self.field.desc}) '
                f'exactly one name must specified: {self.names}'
            )

    def __init__(self):
        self.fields: List[FieldProto] = []
        self.by_key: Mapping[Any, FieldProto] = OrderedDict()
        self.is_finalized = False

    def add(self, *args, **kwargs):
        if self.is_finalized:
            raise ValueError('Storage is already finalized')
        field = FieldProto(*args, **kwargs)
        self.fields.append(field)
        return field

    def finalize(self, variables):
        if self.is_finalized:
            raise ValueError('Storage is already finalized')
        self.is_finalized = True
        names_by_id = {id(field): [] for field in self.fields}
        for name, value in variables.items():
            if id(value) in names_by_id:
                names_by_id[id(value)].append(name)
        for field in self.fields:
            names = names_by_id[id(field)]
            if len(names) != 1:
                raise self.FieldStorageFinalizeError(field, names)
            field.set_name(names[0])
            self.by_key[field.key()] = field


class SimpleTags:
    _field_storage: Optional[FieldStorage] = None

    @classmethod
    def clear_storage(cls):
        cls._field_storage = FieldStorage()

    @classmethod
    def register_tag(cls, *args, **kwargs):
        return cls._field_storage.add(*args, **kwargs)

    @classmethod
    def finalize_storage(cls, variables):
        cls._field_storage.finalize(variables)

    def __getitem__(self, item: FieldProto):
        return self.data[item.key()]

    def __setitem__(self, item: FieldProto, value):
        if item.multifield:
            if not isinstance(value, list):
                raise TypeError()
            for s in value:
                if not isinstance(s, str):
                    raise TypeError()
        else:
            if not isinstance(value, str):
                raise TypeError()
        self.data[item.key()] = value

    def __delitem__(self, item: FieldProto):
        self[item] = [] if item.multifield else ''

    def __init__(self, snapshots, fs):
        if not self._field_storage.is_finalized:
            raise ValueError("Class is not finalized")

        self.snapshots = snapshots
        self.data = {}

        self[FieldProto('PATH')] = fs['path']

        for proto in self._field_storage.by_key.values():
            if proto.frame == 'PATH':
                continue
            del self[proto]

        for tag in fs['tags']:
            name, kwargs = self.snapshots.parse_frame_snapshot(tag)

            desc = kwargs.get('desc', None)
            if name != 'TXXX':
                desc = None
            if desc is not None:
                desc = desc.upper()

            key = (name, desc)

            if key not in self._field_storage.by_key:
                continue
            proto = self._field_storage.by_key[key]

            if name == 'APIC':
                value = kwargs['path']
            elif name == 'USLT':
                value = kwargs['text']
            else:
                value = kwargs['text']
                if not proto.multifield:
                    value = value[0]

            self[proto] = value

    def write(self, fs):
        path = self[FieldProto('PATH')]

        tags = []
        for proto in self._field_storage.by_key.values():
            value = self[proto]

            if not value:
                continue

            kwargs = {}
            if proto.frame == 'PATH':
                continue
            elif proto.frame == 'APIC':
                kwargs['path'] = value
            elif proto.frame == 'USLT':
                kwargs['lang'] = 'eng'
                kwargs['text'] = value
            else:
                if proto.desc is not None:
                    kwargs['desc'] = proto.desc
                if not proto.multifield:
                    value = [value]
                kwargs['text'] = value

            tag = self.snapshots.build_frame_snapshot(proto.frame, kwargs)
            tags.append(tag)

        tags = sorted(tags)

        if fs['path'] == path and fs['tags'] == tags:
            return
        fs['path'] = path
        fs['tags'] = tags
        fs['modified'] = -1
