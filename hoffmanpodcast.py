#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import httplib2
import urllib.parse
import io
import re
from lxml import etree
from lxml import html
import translitfilter
import subprocess

from local import outfile, mp3path, mp3urlpath
if sys.stdout.encoding != 'UTF-8':
        sys.stdout = translitfilter.TranslitFilter(sys.stdout)


rssaddr = 'http://www.denik.cz/rss/hoffmanuv_denik.html'

#httplib2.debuglevel=4
h = httplib2.Http('.cache')
headers = {'Connection': 'close'}
response, content = h.request(rssaddr, headers=headers)
assert response.status == 200
#Make sure no double-XML document is returned (Server is buggy)
first, end, last = content.partition(b'</rss>')
content = b''.join((first, end))
rsstree = etree.parse(io.BytesIO(content))

rsstree.find('channel/title').text = 'Hoffmanův Podcast'
for item in rsstree.getiterator('item'):
        try:
                link = item.find('link')
                #print("getting {}".format(link.text))
                conttree = html.parse(link.text)

                fulltext = conttree.findall('//div[@class="dv3-clanek-content-left bbtext"]/p')
                if fulltext:
                        celem = etree.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
                        celem.text = '<p>{}</p>\n{}'.format(item.find('description').text, "\n".join(etree.tounicode(text) for text in fulltext))
                else:
                        print("Nenalezen hlavni obsah v zapisku: {}".format(item.find('title').text))
                        print("Datum publikace: {}\n".format(item.find('pubDate').text))

                playlistlink = conttree.xpath('//a[contains(concat(" ", normalize-space(@class), " "), " btn ")]')
                if playlistlink is None:
                        raise ValueError('Nenalezen odkaz na galerii v HTML strance')
                playlisturl = playlistlink[0].get('href')
                galtree = html.parse(urllib.parse.urljoin(link.text, playlisturl))
                audiotag = galtree.find('//audio')
                if audiotag is None:
                        raise ValueError('Nenalezen Audio tag v galerii.')
                mp3url = audiotag.get('src')
                if mp3url is None:
                        raise ValueError('Nenalezen MP3 soubor v galerii.')
                mp3base = os.path.basename(urllib.parse.urlsplit(mp3url).path)
                mp3fspath = os.path.join(mp3path, mp3base)
                
                if not os.path.exists(mp3fspath):
                        response, content = h.request(mp3url, headers=headers)
                        if response.status != 200:
                                raise ValueError('Nelze ziskat MP3 soubor {}, status {}'.format(mp3url, response.status))
                        if response['content-type'] != 'audio/mpeg':
                                raise ValueError('MP3 soubor neni typu audio/mpeg.')
                        with open(mp3fspath, "wb") as mp3_f:
                                mp3_f.write(content)
                        subprocess.check_call(["normalize-mp3", "--mp3decode=lame --decode %m %w",
                                               "--mp3encode=lame %w %m", mp3fspath])

                mp3len = str(os.path.getsize(mp3fspath))
                etree.SubElement(item, 'enclosure', {'url': urllib.parse.urljoin(mp3urlpath, mp3base), 'type':'audio/mpeg', 'length':mp3len})


        except (ValueError, OSError) as e:
                print("Chyba: {}\nV zapisku: {}".format(e, item.find('title').text))
                print("Datum publikace: {}\n".format(item.find('pubDate').text))

#etree.dump(rsstree)
rsstree.write(outfile, encoding='utf-8', xml_declaration=True)

