#!/usr/bin/env python3
# -*- coding: utf-8 -*-


rssaddr = 'http://www.denik.cz/rss/hoffmanuv_denik.html'
outfile = './hoffmanpodcast.xml'

import httplib2
import sys, io, re
try:
	from lxml import etree
except ImportError:
	import xml.etree.ElementTree as etree

#httplib2.debuglevel=4
headers = { 'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:5.0) Gecko/20100101 Firefox/5.0' }
h = httplib2.Http('.cache')
response, content = h.request(rssaddr)
assert response.status == 200
#Make sure no double-XML document is returned (Server is buggy)
first, end, last = content.decode('utf-8').partition('</rss>')
content = '{}{}'.format(first, end)
rsstree = etree.parse(io.StringIO(content))

rsstree.find('channel/title').text = 'Hoffmanův Podcast'
for item in rsstree.getiterator('item'):
	try:
		link = item.find('link')
		response, content = h.request(link.text)
		if response.status != 200:
			raise ValueError('Nemohu najit odkazovany clanek, status {}.'.format(response.status));

		cont = content.decode('utf-8').partition('<!--FULLTEXTSTART-->')[2].partition('<!--FULLTEXTSTOP-->')[0]
		m = re.search(r'<div[^>]*>(.*)</div>', cont, re.S)
		if m.lastindex != 1:
			raise ValueError('Nenalezen hlavni obsah.');

		cont = m.group(1)
		celem = etree.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
		celem.text = '<p>{}</p>\n{}'.format(item.find('description').text, cont)


		m = re.search('"dataPath","(http://[^"]*)"', content.decode('utf-8'))
		if m.lastindex != 1:
			raise ValueError('Nenalezen datapath v HTML strance');
		playlisturl = m.group(1)
		response, content = h.request(playlisturl)
		if response.status != 200:
			raise ValueError('Nemohu nacist playlist, status {}.'.format(response.status));
		m = re.search('media_url="(http://[^"]+mp3)"', content.decode('utf-8'))
		if m.lastindex != 1:
			raise ValueError('Nenalezen MP3 soubor v playlistu.');
		mp3url = m.group(1)
		
		response, content = h.request(mp3url, 'HEAD', headers=headers)
		if response.status != 200:
			raise ValueError('Nelze zjistit info o MP3 souboru, status {}'.format(response.status));
		if response['content-type'] != 'audio/mpeg':
			raise ValueError('MP3 soubor neni typu audio/mpeg.');
		mp3len = response['content-length']
		etree.SubElement(item, 'enclosure', {'url': mp3url, 'type':'audio/mpeg', 'length':mp3len})
	except ValueError as e:
		print("Chyba: {}\nV zapisku: {}".format(e, item.find('title').text));
		print("Datum publikace: {}\n".format(item.find('pubDate').text));

#etree.dump(rsstree)
rsstree.write(outfile, 'utf-8')

