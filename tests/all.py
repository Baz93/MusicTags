import unittest
import os
import posixpath
import shutil
import filecmp
import json
import mutagen.id3

from collection import Snapshots, Collection


test_root = posixpath.dirname(posixpath.abspath(__file__))
test_data_root = posixpath.join(test_root, 'data')
work_root = posixpath.join(test_root, 'work')


def create_collection(data_path, snapshot_root, music_root, name):
    with open(data_path, 'r') as f:
        cs = json.load(f)
    os.makedirs(music_root, exist_ok=True)
    os.makedirs(snapshot_root, exist_ok=True)
    for fs in cs:
        path = posixpath.join(music_root, fs['path'])
        os.makedirs(posixpath.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(fs['data'])
        mutagen.id3.ID3().save(path)
    snapshots = Snapshots(snapshot_root)
    collection = Collection(snapshots, music_root)
    for fs in cs:
        tags = fs['tags']
        for i, tag in enumerate(tags):
            if tag.startswith('APIC'):
                tag = eval('mutagen.id3.' + tag)
                tag = snapshots.serialize_frame(tag)
                tags[i] = tag
        collection.set_tags(fs['path'], tags)
    snapshots.save(collection.state, name)


class AllTests(unittest.TestCase):
    def folders_equal(self, path1, path2):
        files1 = sorted(os.listdir(path1))
        files2 = sorted(os.listdir(path2))
        self.assertEqual(files1, files2)
        for f in files1:
            f1 = posixpath.join(path1, f)
            f2 = posixpath.join(path2, f)
            is_dir1 = posixpath.isdir(f1)
            is_dir2 = posixpath.isdir(f2)
            self.assertEqual(is_dir1, is_dir2)
            if is_dir1:
                self.folders_equal(f1, f2)
            else:
                self.assertTrue(filecmp.cmp(f1, f2))

    def snapshots_equal(self, path1, path2):
        with open(path1, 'r') as f:
            cs1 = json.load(f)
        with open(path2, 'r') as f:
            cs2 = json.load(f)
        for fs1, fs2 in zip(cs1, cs2):
            self.assertEqual(fs1['path'], fs2['path'])
            self.assertEqual(fs1['hash'], fs2['hash'])
            self.assertEqual(fs1['tags'], fs2['tags'])

    def impl_test_create(self, data_name, test_name):
        work_dir = posixpath.join(work_root, test_name)
        if posixpath.isdir(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        test_data = posixpath.join(test_data_root, data_name)

        music_dir = posixpath.join(work_dir, 'music')
        result_dir = posixpath.join(work_dir, 'result')

        create_collection(posixpath.join(test_data, 'image.json'), result_dir, music_dir, 'data.json')

        self.folders_equal(music_dir, posixpath.join(test_data, 'music'))
        self.folders_equal(posixpath.join(result_dir, 'pictures'), posixpath.join(work_dir, 'result', 'pictures'))
        self.snapshots_equal(posixpath.join(result_dir, 'data.json'), posixpath.join(work_dir, 'result', 'data.json'))

    def impl_test_scan(self, data_name, test_name):
        work_dir = posixpath.join(work_root, test_name)
        if posixpath.isdir(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        test_data = posixpath.join(test_data_root, data_name)

        result_dir = posixpath.join(work_dir, 'result')

        snapshots = Snapshots(result_dir)
        collection = Collection(snapshots, posixpath.join(test_data, 'music'))
        cs = collection.state
        snapshots.save(cs, 'data.json')

        self.folders_equal(posixpath.join(result_dir, 'pictures'), posixpath.join(work_dir, 'result', 'pictures'))
        self.snapshots_equal(posixpath.join(result_dir, 'data.json'), posixpath.join(work_dir, 'result', 'data.json'))

    def impl_test_apply(self, data_name, test_name):
        work_dir = posixpath.join(work_root, test_name)
        if posixpath.isdir(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        test_data = posixpath.join(test_data_root, data_name)

        music1_dir = posixpath.join(work_dir, 'music1')
        result1_dir = posixpath.join(work_dir, 'result1')
        music2_dir = posixpath.join(work_dir, 'music2')
        result2_dir = posixpath.join(work_dir, 'result2')

        create_collection(posixpath.join(test_data, 'image1.json'), result1_dir, music1_dir, 'data.json')
        create_collection(posixpath.join(test_data, 'image2.json'), result2_dir, music2_dir, 'data.json')

        snapshots1 = Snapshots(result1_dir)
        collection1 = Collection(snapshots1, music1_dir)
        snapshots2 = Snapshots(result2_dir)
        Collection(snapshots1, music2_dir)

        collection1.apply_snapshot(snapshots2.load('data.json'))
        collection1.remove_unused_pictures()
        snapshots1.save(collection1.state, 'data.json')

        self.folders_equal(music1_dir, music2_dir)
        self.folders_equal(posixpath.join(result1_dir, 'pictures'), posixpath.join(result2_dir, 'pictures'))
        self.snapshots_equal(posixpath.join(result1_dir, 'data.json'), posixpath.join(result2_dir, 'data.json'))

    def test_create_one_big_file(self):
        self.impl_test_create('one_big_file', 'create_one_big_file')

    def test_scan_one_big_file(self):
        self.impl_test_scan('one_big_file', 'scan_one_big_file')

    def test_create_multiple_files(self):
        self.impl_test_create('multiple_files', 'create_multiple_files')

    def test_scan_multiple_files(self):
        self.impl_test_scan('multiple_files', 'scan_multiple_files')

    def test_apply_identical(self):
        self.impl_test_apply('apply_identical', 'apply_identical')

    def test_apply_one_file(self):
        self.impl_test_apply('apply_one_file', 'apply_one_file')

    def test_apply_no_collisions(self):
        self.impl_test_apply('apply_no_collisions', 'apply_no_collisions')

    def test_apply_chain(self):
        self.impl_test_apply('apply_chain', 'apply_chain')

    def test_apply_cycle(self):
        self.impl_test_apply('apply_cycle', 'apply_cycle')


if __name__ == '__main__':
    unittest.main()
