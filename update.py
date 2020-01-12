from config import snapshot_root, music_root
from collection import Snapshots, Collection


if __name__ == '__main__':
    snapshots = Snapshots(snapshot_root)
    try:
        cs = snapshots.load('data.json')
    except FileNotFoundError:
        cs = None
    collection = Collection(snapshots, music_root, expected_cs=cs)
    cs = collection.state
    snapshots.save(cs, 'data.json')
    collection.remove_unused_pictures()
