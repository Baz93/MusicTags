from config import snapshot_root, music_root
from collection import Snapshots, Collection


if __name__ == '__main__':
    snapshots = Snapshots(snapshot_root)
    cs = snapshots.load('data.json')
    collection = Collection(snapshots, music_root, expected_cs=cs)
    collection.apply_snapshot(cs)
    cs = collection.state
    snapshots.save(cs, 'data.json')
    collection.remove_unused_pictures()
