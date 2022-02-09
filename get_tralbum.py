import json
import re
from html import unescape
from urllib.request import urlopen
from sys import exit

url = input('Enter url: ')
with urlopen(url) as fu:
    content = fu.read(1000000).decode('utf-8','ignore')

m = re.search(R'data-tralbum="([^"]*?)"',content)
if not m: exit()
data = m.group(1)
with open('ignore/out.json','w',encoding='utf-8') as f:
    json.dump(json.loads(unescape(data)),f,ensure_ascii=False,indent=2)
