from collection import Snapshots, Collection


music_root = '/mnt/c/Users/Vasiliy Mokin/Music/'
snapshot_root = '/mnt/c/Programming/MusicTagsSnapshot'


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
