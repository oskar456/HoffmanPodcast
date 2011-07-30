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

h = httplib2.Http('.cache')
response, content = h.request(rssaddr)
assert response.status == 200

#Make sure no double-XML document is returned (Server is buggy)
first, end, last = content.decode('utf-8').partition('</rss>')
content = '{}{}'.format(first, end)
rsstree = etree.parse(io.StringIO(content))

rsstree.find('channel/title').text = 'Hoffmanův Podcast'
for item in rsstree.getiterator('item'):
	link = item.find('link')
	response, content = h.request(link.text)
	assert response.status == 200

	cont = content.decode('utf-8').partition('<!--FULLTEXTSTART-->')[2].partition('<!--FULLTEXTSTOP-->')[0]
	m = re.search(r'<div[^>]*>(.*)</div>', cont, re.S)
	assert m.lastindex == 1
	cont = m.group(1)
	celem = etree.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
	celem.text = '<p>{}</p>\n{}'.format(item.find('description').text, cont)


	m = re.search('"dataPath","(http://[^"]*)"', content.decode('utf-8'))
	assert m.lastindex == 1
	playlisturl = m.group(1)
	response, content = h.request(playlisturl)
	assert response.status == 200
	m = re.search('media_url="(http://[^"]+)"', content.decode('utf-8'))
	assert m.lastindex == 1
	mp3url = m.group(1)
	
	response, content = h.request(mp3url, 'HEAD')
	assert response.status == 200
	mp3len = response['content-length']
	assert int(mp3len) > 0
	assert response['content-type'] == 'audio/mpeg'
	etree.SubElement(item, 'enclosure', {'url': mp3url, 'type':'audio/mpeg', 'length':mp3len})

#etree.dump(rsstree)
rsstree.write(outfile, 'utf-8')

