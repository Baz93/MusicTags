from collection import Snapshots, Collection


music_root = '/mnt/c/Users/Vasiliy Mokin/Music/'
snapshot_root = '/mnt/c/Programming/MusicTagsSnapshot'


if __name__ == '__main__':
    snapshots = Snapshots(snapshot_root)
    collection = Collection(snapshots, music_root)
    cs = collection.scan_collection()
    snapshots.save(cs, 'data.json')
    collection.remove_redundant_pictures(cs)
