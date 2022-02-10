# this file exists only for testing. do not run this

import json
import re
from html import unescape
from urllib.request import urlopen
from sys import exit

url = input('Enter url: ')

from ripper import get_meta
print('\n'.join(str(m.as_dict()) for m in get_meta(url)))

# with urlopen(url) as fu:
#     content = fu.read(1000000).decode('utf-8','ignore')
# m = re.search(R'data-tralbum="([^"]*?)"',content)
# if not m: exit()
# data = json.loads(unescape(m.group(1)))
# m = re.search(R'data-embed="([^"]*?)"',content)
# data.update(json.loads(unescape(m.group(1))))

# with open('ignore/out.json','w',encoding='utf-8') as f:
#     json.dump(data,f,ensure_ascii=False,indent=2)

