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
        file_snapshot = OrderedDict()
        file_snapshot['path'] = path
        file_snapshot['modified'] = int(os.path.getmtime(real_path))
        tags = ID3(real_path)
        tags_snapshot = self.snapshots.serialize_tags(tags)
        file_snapshot['tags'] = tags_snapshot
        return file_snapshot

    def path_matches_snapshot(self, path, file_snapshot):
        real_path = os.path.join(self.music_root, path)
        return file_snapshot['modified'] == int(os.path.getmtime(real_path))

    def make_snapshot_producer(self, expected_cs=None):
        snapshot_by_path = {}
        if expected_cs is not None:
            for file_snapshot in expected_cs:
                snapshot_by_path[file_snapshot['path']] = file_snapshot

        def produce_snapshot(path):
            if path in snapshot_by_path:
                file_snapshot = snapshot_by_path[path]
                if self.path_matches_snapshot(path, file_snapshot):
                    return file_snapshot
            return self.read_file(path)
        return produce_snapshot

    def scan_collection(self, expected_cs=None):
        snapshot_producer = self.make_snapshot_producer(expected_cs)
        files = []
        self.music_search('', files)
        cs = []
        for num, file in enumerate(files):
            print("%d/%d" % (num + 1, len(files)), file)
            file_snapshot = snapshot_producer(file)
            cs.append(file_snapshot)
        return cs

    def get_used_pictures(self, cs):
        used_pictures = []
        for file_snapshot in cs:
            for frame_snapshot in file_snapshot['tags']:
                name, kwargs = self.snapshots.parse_frame_snapshot(frame_snapshot)
                if name == 'APIC':
                    used_pictures.append(kwargs['path'])
        return used_pictures

    def remove_redundant_pictures(self, cs):
        used_picrures = self.get_used_pictures(cs)
        self.snapshots.filter_pictures(lambda name: name in used_picrures)
