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
    def __init__(self, snapshots: Snapshots, music_root, expected_cs=None, need_update=True):
        if expected_cs is None:
            expected_cs = []

        self.snapshots = snapshots
        self.music_root = music_root
        self.state = None
        self.by_path = None
        self.set_state(expected_cs)
        if need_update:
            self.update()

    def set_state(self, state):
        self.state = state
        self.by_path = dict((fs['path'], fs) for fs in state)

    def real_path(self, path):
        return os.path.join(self.music_root, path)

    def is_good_path(self, path):
        # TODO
        return True

    def delete_empty_folders(self, path):
        real_path = self.real_path(path)
        if os.path.isfile(real_path):
            return
        for f in os.listdir(real_path):
            self.delete_empty_folders(os.path.join(path, f))
        if len(os.listdir(real_path)) == 0:
            os.rmdir(real_path)

    def music_search(self, path, res):
        real_path = self.real_path(path)
        if os.path.isfile(real_path):
            if real_path.endswith('.mp3'):
                res.append(path)
            else:
                print('Bad extension:', real_path)
            return
        for f in os.listdir(real_path):
            self.music_search(os.path.join(path, f), res)

    def read_file(self, path):
        real_path = self.real_path(path)
        fs = OrderedDict()
        fs['path'] = path
        fs['modified'] = modified_timestamp(real_path)
        fs['hash'] = get_mp3_hash(real_path)
        fs['tags'] = self.snapshots.serialize_tags(ID3(real_path))
        return fs

    def load_fs(self, path):
        if path in self.by_path:
            fs = self.by_path[path]
            if fs['modified'] == modified_timestamp(self.real_path(path)):
                return deepcopy(fs)
        return self.read_file(path)

    def update(self):
        files = []
        self.music_search('', files)
        cs = []
        for num, path in enumerate(files):
            print("%d/%d" % (num + 1, len(files)), path)
            cs.append(self.load_fs(path))
        self.set_state(cs)

    def move_file(self, cur_path, new_path):
        if new_path == cur_path:
            return
        cur_real_path = self.real_path(cur_path)
        new_real_path = self.real_path(new_path)
        assert new_path not in self.by_path
        os.makedirs(os.path.dirname(new_real_path), exist_ok=True)
        fs = self.by_path[cur_path]
        shutil.move(cur_real_path, new_real_path)
        del self.by_path[cur_path]
        fs['path'] = new_path
        fs['modified'] = modified_timestamp(new_real_path)
        self.by_path[new_path] = fs

    def set_tags(self, path, serialized_tags):
        tags = self.snapshots.deserialize_tags(serialized_tags)
        serialized_tags = self.snapshots.serialize_tags(tags)
        temp = uuid.uuid4().hex + '.mp3'
        real_path = self.real_path(path)
        real_temp = self.real_path(temp)
        shutil.copy2(real_path, real_temp)
        try:
            tags.save(real_temp)
            result_tags = self.snapshots.serialize_tags(ID3(real_temp))
            assert (
                sorted(serialized_tags) ==
                sorted(result_tags)
            )
        except Exception as ex:
            os.remove(real_temp)
            raise ex
        os.remove(real_path)
        fs = self.by_path[path]
        shutil.move(real_temp, real_path)
        fs['modified'] = modified_timestamp(real_path)
        fs['tags'] = serialized_tags

    def apply_snapshot(self, new_cs):
        cur_cs = self.state

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
            to = new_cs[i]['path']
            rec(to)

            self.move_file(path, to)
            self.set_tags(to, new_cs[i]['tags'])

        for cur_fs in cur_cs:
            rec(cur_fs['path'], True)

        self.delete_empty_folders('')

    def get_used_pictures(self):
        used_pictures = []
        for fs in self.state:
            for frame_snapshot in fs['tags']:
                name, kwargs = self.snapshots.parse_frame_snapshot(frame_snapshot)
                if name == 'APIC':
                    used_pictures.append(kwargs['path'])
        return used_pictures

    def remove_unused_pictures(self):
        used_picrures = self.get_used_pictures()
        self.snapshots.filter_pictures(lambda name: name in used_picrures)
