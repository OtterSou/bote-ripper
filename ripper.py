import json
import re
from html import unescape
from os import makedirs
from os import replace as filemove
from os.path import dirname, expandvars
from os.path import join as pathjoin
from threading import Thread
from urllib.error import URLError
from urllib.request import urlopen

from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, TPE2, TRCK


class Metadata:

    _attrs = ('mp3url', 'muhash', 'labi', 'albi', 'titi', 'alan', 'albn', 'artn', 'titn', 'trck')
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


def trad2json(content):
    m = re.search(r'data-tralbum="([^"]*?)"', content)
    trj = json.loads(unescape(m.group(1)))
    m = re.search(r'data-embed="([^"]*?)"', content)
    trj.update(json.loads(unescape(m.group(1))))
    return trj


def get_meta(url, _cache={}):
    print('Looking up metadata for {}'.format(url))
    try:
        with urlopen(url) as fu:
            content = fu.read(1000000).decode('utf-8', 'ignore')
    except URLError:
        print('failed opening url')
        return []
    pattern = r'<meta property="og:url" +content="https://([0-9a-z-]+)\.bandcamp\.com(?:/(track|album)/([0-9a-z-]+))?">'
    m = re.search(pattern, content)
    if not m:
        print('not a bandcamp website')
        return []
    labi, utype, tai = m.groups()
    if utype:
        trj = trad2json(content)
        metad_parent = {'labi': labi}
        if utype == 'album':
            # album
            metad_parent['alan'] = trj['artist']
            metad_parent['albi'] = tai
            metad_parent['albn'] = trj['current']['title']
            metad_parent['artn'] = metad_parent['alan']
            _cache[url] = metad_parent['alan']
        elif 'album_title' in trj:
            # album track
            alb_url_full = 'https://{}.bandcamp.com{}'.format(labi, trj['album_url'])
            if alb_url_full in _cache:
                metad_parent['alan'] = _cache[alb_url_full]
            else:
                with urlopen(alb_url_full) as fu:
                    alb_content = fu.read(1000000).decode('utf-8', 'ignore')
                metad_parent['alan'] = trad2json(alb_content)['artist']
                _cache[alb_url_full] = metad_parent['alan']
            metad_parent['albi'] = trj['album_url'][7:]
            metad_parent['albn'] = trj['album_title']
            metad_parent['artn'] = metad_parent['alan']
        else:
            # standalone track
            metad_parent['alan'] = None
            metad_parent['albi'] = None
            metad_parent['albn'] = None
            metad_parent['artn'] = trj['artist']
        out = []
        for track in trj['trackinfo']:
            metad = metad_parent.copy()
            if not track['file']:
                continue
            metad['mp3url'] = track['file']['mp3-128']
            if track['artist'] is None:
                metad['titn'] = track['title']
            else:
                metad['artn'] = track['artist']
                metad['titn'] = track['title'][len(track['artist'])+3:]
            metad['titi'] = track['title_link'][7:]
            metad['trck'] = track['track_num']
            out.append(Metadata(metad))
        return out
    else:
        # artist
        pattern = r'<a href="/((?:album|track)/[0-9a-z-]+)">'
        urls = ['https://{}.bandcamp.com/{}'.format(labi, m.group(1)) for m in re.finditer(pattern, content)]
        return [item for url in urls for item in get_meta(url)]


def download_file(meta):
    print('Downloading {}'.format(meta.muhash), flush=True)
    path = R'temp/{}.mp3'.format(meta.muhash)
    with urlopen(meta.mp3url) as fu, open(path, 'wb') as fp:
        fp.write(fu.read())
    Metadata.count += 1
    print('Finished downloading {}/{}'.format(Metadata.count, Metadata.total_count), flush=True)


def add_tags(meta):
    path = 'temp/{}.mp3'.format(meta.muhash)
    try:
        tags = ID3(path)
        tags.delete()
    except ID3NoHeaderError:
        tags = ID3()
    if meta.alan is not None:
        tags.add(TPE2(1, meta.alan))
    if meta.albn is not None:
        tags.add(TALB(1, meta.albn))
    if meta.artn is not None:
        tags.add(TPE1(1, meta.artn))
    if meta.titn is not None:
        tags.add(TIT2(1, meta.titn))
    if meta.trck is not None:
        tags.add(TRCK(1, str(meta.trck)))
    tags.save(path, v2_version=3)


def move_file(meta, settings):
    path_src = R'temp\{}.mp3'.format(meta.muhash)
    if meta.albi:
        path_dst = settings['path_album'].format(**meta.as_dict())
    else:
        path_dst = settings['path_track'].format(**meta.as_dict())
    path_dst = pathjoin(expandvars(settings['path_root']), path_dst)
    makedirs(dirname(path_dst), exist_ok=True)
    filemove(path_src, path_dst)


def download(urls, settings):
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
        move_file(meta, settings)


if __name__ == '__main__':
    with open('settings.json', encoding='utf-8') as f:
        settings = json.load(f)
    print('''\
Bandcamp One-Twenty-Eight Ripper v2
Enter URL of artist/album/track page in Bandcamp:
add empty line when done
''')
    urls = set()
    while True:
        sin = input()
        if not sin:
            break
        urls.add(sin)
    download(urls, settings)
