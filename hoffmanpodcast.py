#!/usr/bin/env python3
# -*- coding: utf-8 -*-


rssaddr = 'http://www.denik.cz/rss/hoffmanuv_denik.html'

import os, sys
current_path = os.path.dirname(sys.argv[0])
outfile = os.path.join(current_path, 'hoffmanpodcast.xml')

import httplib2
from urllib.parse import urljoin
import io
import re
try:
	from lxml import etree
except ImportError:
	import xml.etree.ElementTree as etree

import translitfilter
if sys.stdout.encoding != 'UTF-8':
	sys.stdout = translitfilter.TranslitFilter(sys.stdout)

#httplib2.debuglevel=4
h = httplib2.Http()
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
		m = re.search(r'</div>(([^<]|<p|</p)*)', cont, re.S)
		if m is None or m.lastindex != 1:
			raise ValueError('Nenalezen hlavni obsah.')

		cont = m.group(1)
		celem = etree.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
		celem.text = '<p>{}</p>\n{}'.format(item.find('description').text, cont)


		m = re.search('<a href="(/galerie/[^"]*\.html\?mm=[0-9]+)">', content.decode('utf-8'))
		if m is None or m.lastindex != 1:
			raise ValueError('Nenalezen odkaz na galerii v HTML strance')
		playlisturl = m.group(1)
		response, content = h.request(urljoin(link.text, playlisturl))
		if response.status != 200:
			raise ValueError('Nemohu nacist stranku s galerii, status {}.'.format(response.status))
		m = re.search('url: "(http:[^"]+mp3)"', content.decode('utf-8'))
		if m is None or m.lastindex != 1:
			raise ValueError('Nenalezen MP3 soubor v galerii.')
		mp3url = m.group(1).translate({ord("\\"):None})
		
		response, content = h.request(mp3url, 'HEAD')
		if response.status != 200:
			raise ValueError('Nelze zjistit info o MP3 souboru, status {}'.format(response.status))
		if response['content-type'] != 'audio/mpeg':
			raise ValueError('MP3 soubor neni typu audio/mpeg.')
		mp3len = response['content-length']
		etree.SubElement(item, 'enclosure', {'url': mp3url, 'type':'audio/mpeg', 'length':mp3len})
	except ValueError as e:
		print("Chyba: {}\nV zapisku: {}".format(e, item.find('title').text))
		print("Datum publikace: {}\n".format(item.find('pubDate').text))

#etree.dump(rsstree)
rsstree.write(outfile, encoding='utf-8')

