import unittest
import os
import shutil
import filecmp
import json

from ..collection import Snapshots, Collection


test_root = os.path.dirname(os.path.abspath(__file__))
test_data = os.path.join(test_root, 'data')
work_root = os.path.join(test_root, 'work')


class AllTests(unittest.TestCase):
    def picture_dirs_equal(self, path1, path2):
        files1 = sorted(os.listdir(path1))
        files2 = sorted(os.listdir(path2))
        self.assertEqual(files1, files2)
        for f in files1:
            self.assertTrue(filecmp.cmp(os.path.join(path1, f), os.path.join(path2, f)))

    def snapshots_equal(self, path1, path2):
        with open(path1, 'r') as f:
            cs1 = json.load(f)
        with open(path2, 'r') as f:
            cs2 = json.load(f)
        for fs1, fs2 in zip(cs1, cs2):
            self.assertEqual(fs1['path'], fs2['path'])
            self.assertEqual(fs1['hash'], fs2['hash'])
            self.assertEqual(fs1['tags'], fs2['tags'])

    def test_one_big_file(self):
        testname = 'one_big_file'
        musicdir = os.path.join(test_data, 'one_big_file', 'music')
        resultdir = os.path.join(test_data, 'one_big_file', 'result')
        workdir = os.path.join(work_root, testname)
        if os.path.isdir(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir)

        snapshots = Snapshots(workdir)
        collection = Collection(snapshots, musicdir)
        cs = collection.state
        snapshots.save(cs, 'data.json')

        self.picture_dirs_equal(os.path.join(resultdir, 'pictures'), os.path.join(workdir, 'pictures'))
        self.snapshots_equal(os.path.join(resultdir, 'data.json'), os.path.join(workdir, 'data.json'))



if __name__ == '__main__':
    unittest.main()
