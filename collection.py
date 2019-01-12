import os
from collections import OrderedDict
import hashlib
import tempfile
import shutil
import uuid
from copy import deepcopy

from mutagen.id3 import ID3

from snapshots import Snapshots


def get_mp3_hash(path):
    with tempfile.TemporaryDirectory() as td:
        tf = os.path.join(td, 'a.mp3')
        shutil.copy2(path, tf)
        tags = ID3(tf)
        tags.delete()
        tags.save()
        with open(tf, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()


def modified_timestamp(path):
    return int(os.path.getmtime(path))


class Collection:
    def __init__(self, snapshots: Snapshots, music_root):
        self.snapshots = snapshots
        self.music_root = music_root

    def is_good_path(self, path):
        # TODO
        return True

    def delete_empty_folders(self, path):
        real_path = os.path.join(self.music_root, path)
        if os.path.isfile(real_path):
            return
        for f in os.listdir(real_path):
            self.delete_empty_folders(os.path.join(path, f))
        if len(os.listdir(real_path)) == 0:
            os.rmdir(real_path)

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
        file_snapshot['modified'] = modified_timestamp(real_path)
        file_snapshot['hash'] = get_mp3_hash(real_path)
        tags = ID3(real_path)
        tags_snapshot = self.snapshots.serialize_tags(tags)
        file_snapshot['tags'] = tags_snapshot
        return file_snapshot

    def path_matches_snapshot(self, path, file_snapshot):
        real_path = os.path.join(self.music_root, path)
        return file_snapshot['modified'] == modified_timestamp(real_path)

    def make_snapshot_producer(self, expected_cs=None):
        snapshot_by_path = {}
        if expected_cs is not None:
            for file_snapshot in expected_cs:
                snapshot_by_path[file_snapshot['path']] = file_snapshot

        def produce_snapshot(path):
            if path in snapshot_by_path:
                file_snapshot = snapshot_by_path[path]
                if self.path_matches_snapshot(path, file_snapshot):
                    return deepcopy(file_snapshot)
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

    def move_file(self, cur_path, new_path):
        cur_real_path = os.path.join(self.music_root, cur_path)
        new_real_path = os.path.join(self.music_root, new_path)
        shutil.move(cur_real_path, new_real_path)

    def apply_file_snapshot(self, path, fs):
        cur_real_path = os.path.join(self.music_root, path)
        new_real_path = os.path.join(self.music_root, fs['path'])
        os.makedirs(os.path.dirname(new_real_path), exist_ok=True)
        shutil.copy2(cur_real_path, new_real_path)
        try:
            tags = self.snapshots.deserialize_tags(fs['tags'])
            tags.save(new_real_path)
            tags = ID3(new_real_path)
            assert repr(sorted(self.snapshots.serialize_tags(tags))) == repr(sorted(fs['tags']))
        except:
            os.remove(new_real_path)
            assert False
        os.remove(cur_real_path)
        fs['modified'] = modified_timestamp(new_real_path)

    def apply_snapshot(self, cur_cs, new_cs):
        assert len(set(fs['path'] for fs in new_cs)) == len(new_cs)
        for fs in new_cs:
            assert self.is_good_path(fs['path'])

        untouched = set(map(repr, cur_cs)) & set(map(repr, new_cs))
        cur_cs = filter(lambda fs: repr(fs) not in untouched, cur_cs)
        new_cs = filter(lambda fs: repr(fs) not in untouched, new_cs)

        cur_cs = sorted(cur_cs, key=lambda fs: fs['hash'])
        new_cs = sorted(new_cs, key=lambda fs: fs['hash'])
        assert len(cur_cs) == len(new_cs)
        for cur_fs, new_fs in zip(cur_cs, new_cs):
            assert cur_fs['hash'] == new_fs['hash']

        if len(cur_cs) == 0:
            return

        cur_cs, new_cs = zip(*sorted(zip(cur_cs, new_cs), key=lambda pair: pair[0]['path']))

        todo = dict((fs['path'], i) for i, fs in enumerate(cur_cs))

        def rec(path, first=False):
            if path not in todo:
                return
            i = todo[path]
            del todo[path]
            if first:
                temp = uuid.uuid4().hex + '.mp3'
                self.move_file(path, temp)
                path = temp
            rec(new_cs[i]['path'])
            self.apply_file_snapshot(path, new_cs[i])

        for cur_fs in cur_cs:
            rec(cur_fs['path'], True)

        self.delete_empty_folders('')

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
