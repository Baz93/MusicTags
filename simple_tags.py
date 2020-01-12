from plistlib import Dict
from typing import Any


class FieldProto:
    def __init__(self, frame, desc=None, multifield=False):
        self.frame = frame
        self.desc = desc
        self.multifield = multifield

    def set_name(self, name):
        if self.frame == 'TXXX' and self.desc is None:
            self.desc = name.upper()


def filter_proto(field_dict):
    return {k: v for k, v in field_dict.items() if isinstance(v, FieldProto)}


def simple_tags(field_dict):
    by_tag: Dict[Any, FieldProto] = {}

    for attr, proto in field_dict.items():
        proto.set_name(attr)
        by_tag[(proto.frame, proto.desc)] = proto

    class SimpleTags:
        def __getitem__(self, item: FieldProto):
            return self.data[(item.frame, item.desc)]

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
            self.data[(item.frame, item.desc)] = value

        def __init__(self, snapshots, fs):
            self.snapshots = snapshots

            self.data = {('PATH', None): fs['path']}

            for key, proto in by_tag.items():
                if proto.frame == 'PATH':
                    continue
                self.data[key] = [] if proto.multifield else ''

            for tag in fs['tags']:
                name, kwargs = self.snapshots.parse_frame_snapshot(tag)

                desc = kwargs.get('desc', None)
                if name != 'TXXX':
                    desc = None
                if desc is not None:
                    desc = desc.upper()

                key = (name, desc)

                if key not in by_tag:
                    continue
                proto = by_tag[key]

                if name == 'APIC':
                    value = kwargs['path']
                elif name == 'USLT':
                    value = kwargs['text']
                else:
                    value = kwargs['text']
                    if not proto.multifield:
                        value = value[0]

                self.data[key] = value

        def write(self, fs):
            path = self.data[('PATH', None)]

            tags = []
            for key, proto in by_tag.items():
                value = self.data[key]

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

    return SimpleTags
