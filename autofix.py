from config import snapshot_root, music_root
from collection import Snapshots, Collection
from my_tags import MyTags


def fix_cs(snapshots, cs):
    for fs in cs:
        my_tags = MyTags(snapshots, fs)
        my_tags.fix()
        my_tags.write(fs)


if __name__ == '__main__':
    snapshots = Snapshots(snapshot_root)
    try:
        cs = snapshots.load('data.json')
    except FileNotFoundError:
        cs = None
    collection = Collection(snapshots, music_root, expected_cs=cs)
    cs = collection.state

    fix_cs(snapshots, cs)
    
    snapshots.save(cs, 'data.json')
    collection.remove_unused_pictures()
