import json
import re
from html import unescape
from os import makedirs
from os import replace as filemove
from os.path import dirname
from os.path import join as pathjoin
from threading import Thread
from urllib.request import urlopen

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TPE2, TRCK


with open('settings.json', encoding='utf-8') as f:
    settings = json.load(f)


class Metadata:

    _attrs = ('mp3url', 'muhash', 'labi', 'albi', 'titi', 'labn', 'albn', 'artn', 'titn', 'trck')
    count = 0
    total_count = 0

    def __init__(self, meta: dict):
        for name in self._attrs:
            if name in meta:
                setattr(self, name, meta[name])
            else:
                setattr(self, name, None)
        if self.mp3url and not self.muhash:
            self.muhash = self.mp3url[29:61]

    def as_dict(self):
        return {name: getattr(self, name) for name in self._attrs}

    def __eq__(self, other):
        return self.muhash == other.muhash

    def __hash__(self):
        return hash(self.muhash)


def get_meta(url):
    print('Looking up metadata for {}'.format(url))
    # TODO detect page type and extract metadata

def download_file(meta):
    print('Downloading {}'.format(meta.muhash))
    path = R'temp/{}.mp3'.format(meta.muhash)
    with urlopen(meta.mp3url) as fu, open(path, 'wb') as fp:
        fp.write(fu.read())
    Metadata.count += 1
    print('Finished downloading {}/{}'.format(Metadata.count, Metadata.total_count))


def add_tags(meta):
    path = 'temp/{}.mp3'.format(meta.muhash)
    try:
        tags = ID3(path)
        tags.delete()
    except ID3NoHeaderError:
        tags = ID3()
    if meta.labn is not None:
        tags.add(TPE2(1, meta.labn))
    if meta.albn is not None:
        tags.add(TALB(1, meta.albn))
    if meta.artn is not None:
        tags.add(TPE1(1, meta.artn))
    if meta.titn is not None:
        tags.add(TIT2(1, meta.titn))
    if meta.trck is not None:
        tags.add(TRCK(1, str(meta.trck)))
    tags.save(path, v2_version=3)


def move_file(meta):
    path_src = R'temp\{}.mp3'.format(meta.muhash)
    if meta.albi:
        path_dst = settings['path_album'].format(**meta.as_dict())
    else:
        path_dst = settings['path_track'].format(**meta.as_dict())
    path_dst = pathjoin(settings['path_root'], path_dst)
    makedirs(dirname(path_dst), exist_ok=True)
    filemove(path_src, path_dst)


def download(urls):
    metas = {meta for url in urls for meta in get_meta(url)}
    Metadata.total_count = len(metas)
    Metadata.count = 0
    print('downloading {} mp3 file(s)'.format(Metadata.total_count))
    threads = [Thread(target=download_file, args=(meta,)) for meta in metas]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print('adding metadata')
    for meta in metas:
        add_tags(meta)
        move_file(meta)
