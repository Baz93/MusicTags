import os
from collections import OrderedDict

from mutagen.id3 import ID3

from snapshots import Snapshots


class Collection:
    def __init__(self, snapshots: Snapshots, music_root):
        self.snapshots = snapshots
        self.music_root = music_root

    def music_search(self, path, res):
        real_path = os.path.join(self.music_root, path)
        if os.path.isfile(real_path):
            if real_path.endswith('.mp3'):
                res.append(path)
            else:
                print('Bad extension:', real_path)
            return
        for f in os.listdir(real_path):
            self.music_search(os.path.join(path, f), res)

    def read_file(self, path):
        real_path = os.path.join(self.music_root, path)
        config = OrderedDict()
        config['path'] = path
        tags = ID3(real_path)
        tags_snapshot = self.snapshots.serialize_tags(tags)
        config['tags'] = tags_snapshot
        return config

    def scan_collection(self):
        files = []
        self.music_search('', files)
        cs = []
        for num, file in enumerate(files):
            print("%d/%d" % (num + 1, len(files)), file)
            config = self.read_file(file)
            cs.append(config)
        return cs

    def get_used_pictures(self, cs):
        used_pictures = []
        for tags_snapshot in cs:
            for frame_snapshot in tags_snapshot['tags']:
                name, kwargs = self.snapshots.parse_frame_snapshot(frame_snapshot)
                if name == 'APIC':
                    used_pictures.append(kwargs['path'])
        return used_pictures

    def remove_redundant_pictures(self, cs):
        used_picrures = self.get_used_pictures(cs)
        self.snapshots.filter_pictures(lambda name: name in used_picrures)
