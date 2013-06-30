#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import httplib2
import urllib.parse
import io
import re
try:
	from lxml import etree
except ImportError:
	import xml.etree.ElementTree as etree
import translitfilter
import subprocess
if sys.stdout.encoding != 'UTF-8':
	sys.stdout = translitfilter.TranslitFilter(sys.stdout)


rssaddr = 'http://www.denik.cz/rss/hoffmanuv_denik.html'
current_path = os.path.dirname(sys.argv[0])
outfile = os.path.join(current_path, 'hoffmanpodcast.xml')
mp3path = os.path.join(current_path, 'audio')
mp3urlpath = "audio/"

#httplib2.debuglevel=4
h = httplib2.Http('.cache')
response, content = h.request(rssaddr)
assert response.status == 200
#Make sure no double-XML document is returned (Server is buggy)
first, end, last = content.partition(b'</rss>')
content = b''.join((first, end))
rsstree = etree.parse(io.BytesIO(content))

rsstree.find('channel/title').text = 'Hoffmanův Podcast'
for item in rsstree.getiterator('item'):
	try:
		link = item.find('link')
		response, content = h.request(link.text)
		if response.status != 200:
			raise ValueError('Nemohu najit odkazovany clanek, status {}.'.format(response.status))
		cont = content.decode('utf-8').partition('<p class="clanek-perex">')[2].partition('<p class="clanek-autor">')[0]

		m = re.search('<a href="(/galerie/[^"]*\.html\?mm=[0-9]+)">', content.decode('utf-8'))
		if m is None or m.lastindex != 1:
			raise ValueError('Nenalezen odkaz na galerii v HTML strance')
		playlisturl = m.group(1)
		response, content = h.request(urllib.parse.urljoin(link.text, playlisturl))
		if response.status != 200:
			raise ValueError('Nemohu nacist stranku s galerii, status {}.'.format(response.status))
		m = re.search('url: "(http:[^"]+mp3)"', content.decode('utf-8'))
		if m is None or m.lastindex != 1:
			raise ValueError('Nenalezen MP3 soubor v galerii.')
		mp3url = m.group(1).translate({ord("\\"):None})
		mp3base = os.path.basename(urllib.parse.urlsplit(mp3url).path)
		mp3fspath = os.path.join(mp3path, mp3base)
		
		if not os.path.exists(mp3fspath):
			response, content = h.request(mp3url)
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

		m = re.search(r'<div class="bbtext">(([^<]|</?p|</?span)*)</div>', cont, re.S)
		if m is None or m.lastindex != 1:
			raise ValueError('Nenalezen hlavni obsah.')

		cont = m.group(1)
		celem = etree.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
		celem.text = '<p>{}</p>\n{}'.format(item.find('description').text, cont)

	except ValueError as e:
		print("Chyba: {}\nV zapisku: {}".format(e, item.find('title').text))
		print("Datum publikace: {}\n".format(item.find('pubDate').text))

#etree.dump(rsstree)
rsstree.write(outfile, encoding='utf-8', xml_declaration=True)

