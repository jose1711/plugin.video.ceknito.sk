# -*- coding: UTF-8 -*-
# /*
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */

import html
import re
import urllib.request, urllib.error, urllib.parse
import http.cookiejar
import xbmcgui
from xml.etree.ElementTree import fromstring

import util
import resolver
from provider import ResolveException
from provider import ContentProvider


class CeknitoContentProvider(ContentProvider):
    def __init__(self, username=None, password=None, filter=None,
                 tmp_dir='/tmp'):
        ContentProvider.__init__(self, 'ceknito.sk',
                                 'https://ceknito.sk',
                                 username, password, filter, tmp_dir)
        # cookie support for util.request() (uses the global urllib opener)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.LWPCookieJar()))
        urllib.request.install_opener(opener)

    def capabilities(self):
        return ['categories', 'resolve', 'search']

    # dispatches internal "#action#" pseudo-urls to their handlers, otherwise
    # treats url as a regular /videa or category listing page
    def list(self, url):
        if url.find("#related#") == 0:
            return self.list_related(util.request(self._url(url[9:])))
        elif url.find("#comments#") == 0:
            return self.show_comments(self._url(url[10:]))
        elif url.find("#show_plot#") == 0:
            return self.show_plot(self._url(url[11:]))
        else:
            return self.list_content(util.request(self._url(url)), self._url(url))

    def search(self, keyword):
        return self.list_content(util.request(self._url('/vyhladavanie?q=' + urllib.parse.quote(keyword))))

    # returns the fixed sort shortcuts plus the live category list scraped
    # from /kategorie (name + numeric categ id)
    def categories(self):
        result = []
        item = self.dir_item()
        item['title'] = 'Najnovšie'
        item['url'] = '/videa?by=time&categ=0&period=all'
        result.append(item)

        item = self.dir_item()
        item['title'] = 'Najlepšie hodnotené'
        item['url'] = '/videa?by=rank&categ=0&period=all'
        result.append(item)

        item = self.dir_item()
        item['title'] = 'Najviac komentované'
        item['url'] = '/videa?by=comments&categ=0&period=all'
        result.append(item)

        data = util.request(self.base_url + '/kategorie')
        pattern = '<li><a href="/videa\\?categ=(?P<id>[0-9]+)">(?P<name>[^<]+?)\\s*<small>'
        for m in re.finditer(pattern, data, re.IGNORECASE):
            item = self.dir_item()
            item['title'] = html.unescape(m.group('name'))
            item['url'] = '/videa?by=time&categ=%s&period=all' % m.group('id')
            result.append(item)
        return result

    # parses a page of "theme2026-video-card" articles (used by homepage,
    # /videa listings, category listings and search results alike) plus its
    # next/prev pager links; article markup differs slightly between listing
    # types, so each field is located independently within the article block
    # rather than via one rigid pattern
    def list_content(self, page, url=None):
        result = []
        if not url:
            url = self.base_url
        article_re = re.compile(r'<article class="theme2026-video-card">(?P<block>.*?)</article>', re.DOTALL)
        for am in article_re.finditer(page):
            block = am.group('block')
            url_m = re.search(r'href="(?P<url>/video/[0-9]+)"', block)
            title_m = re.search(r'<h3><a[^>]*>(?P<title>[^<]*)</a></h3>', block)
            if not (url_m and title_m):
                continue
            img_m = re.search(r'<img src="(?P<img>[^"]+)"', block)
            dur_m = re.search(r'theme2026-time-badge">(?P<duration>[0-9:]+)<', block)
            plot_m = re.search(r'theme2026-video-description">(?P<plot>.*?)</p>', block, re.DOTALL)

            item = self.video_item()
            item['title'] = html.unescape(title_m.group('title')).strip()
            item['img'] = img_m.group('img') if img_m else ''
            item['url'] = url_m.group('url')
            item['duration'] = self.mmss_to_seconds(dur_m.group('duration')) if dur_m else 0
            plot = html.unescape(plot_m.group('plot')).strip() if plot_m else ''
            item['plot'] = plot
            item['info'] = plot
            item['menu'] = {'$30060': {'list': '#related#' + item['url'],
                                       'action-type': 'list'},
                            'Komentáre': {'list': '#comments#' + item['url'],
                                          'action-type': 'show_comments'},
                            'Popis': {'list': '#show_plot#' + item['url'],
                                      'action-type': 'show_plot'}
                            }
            self._filter(result, item)

        n = re.search(r'<a href="(?P<url>[^"]+)">[^<]*?da\S*šie', page)
        if n:
            item = self.dir_item()
            item['type'] = 'next'
            item['url'] = html.unescape(n.group('url'))
            result.append(item)
        n = re.search(r'<a href="(?P<url>[^"]+)">[^<]*?predch\S*dzaj\S*ce', page)
        if n:
            item = self.dir_item()
            item['type'] = 'prev'
            item['url'] = html.unescape(n.group('url'))
            result.append(item)

        return result

    # parses the "related videos" sidebar shown on a video detail page
    def list_related(self, page):
        result = []
        data = util.substr(page, '<ul class="theme2026-related-list">', '</ul>')
        pattern = ('<a class="theme2026-related-thumb" href="(?P<url>/video/[0-9]+)"[^>]*>\\s*'
                   '<img[^>]+src="(?P<img>[^"]+)"[^>]*>.*?'
                   '<p class="theme2026-related-title"><a[^>]*>(?P<title>[^<]*)</a></p>')
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            item = self.video_item()
            item['title'] = html.unescape(m.group('title')).strip()
            item['img'] = m.group('img')
            item['url'] = m.group('url')
            self._filter(result, item)
        return result

    # fetches the video detail page and displays its top-level comments
    # (author, date, body) in a text viewer dialog; replies are not fetched
    def show_comments(self, page):
        data = util.request(page)
        comments = ''
        pattern = ('<h5><a[^>]*>(?P<author>[^<]*)</a></h5>\\s*'
                   '<span class="theme2026-comment-time">(?P<date>[^<]*)</span>.*?'
                   '<div class="theme2026-comment-body">(?P<body>.*?)</div>')
        for m in re.finditer(pattern, data, re.IGNORECASE | re.DOTALL):
            author = html.unescape(m.group('author')).strip()
            date = html.unescape(m.group('date')).strip()
            body = html.unescape(re.sub('<[^>]+>', '', m.group('body'))).strip()
            comments += '[B]{author}[/B] {date}\n{body}\n\n'.format(author=author, date=date, body=body)
        if not comments:
            comments = '-- žiadne komentáre --'
        xbmcgui.Dialog().textviewer('Komentáre', comments)
        return []

    # shows the full (untruncated) video description from the video's XML
    # manifest, since listing pages only carry a shortened plot
    def show_plot(self, page):
        manifest = self._get_manifest(page)
        plot = manifest['description'] if manifest and manifest['description'] else '-- undefined --'
        xbmcgui.Dialog().textviewer('Popis', plot)
        return []

    # converts a "MM:SS" or "HH:MM:SS" duration badge into seconds
    def mmss_to_seconds(self, mmss):
        hours = 0
        if len(mmss.split(':')) > 2:
            hours, minutes, seconds = [int(x) for x in mmss.split(':')]
        else:
            minutes, seconds = [int(x) for x in mmss.split(':')]
        return (hours * 3600 + minutes * 60 + seconds)

    # fetches a video detail page, follows its data-manifest-url attribute
    # to the /xml/video.xml endpoint and returns {description, sources}
    # (sources = list of {resolution, url} sorted from worst to best quality)
    def _get_manifest(self, page_url):
        data = util.request(page_url)
        m = re.search('data-manifest-url="(?P<manifest>[^"]+)"', data)
        if not m:
            return None
        manifest_url = self._url(html.unescape(m.group('manifest')))
        xml_data = util.request(manifest_url)
        if isinstance(xml_data, str):
            xml_data = xml_data.encode('utf-8')
        root = fromstring(xml_data)
        description = root.findtext('description') or ''
        sources = []
        for source in root.find('sources'):
            sources.append({'resolution': int(source.get('resolution')),
                             'url': source.get('url')})
        sources.sort(key=lambda s: s['resolution'])
        return {'description': description, 'sources': sources}

    # resolves a video url into direct, playable mp4 stream urls (one per
    # available resolution, ascending) via the video's XML manifest
    def resolve(self, item, captcha_cb=None, select_cb=None):
        result = []
        item = item.copy()
        url = self._url(item['url'])

        manifest = self._get_manifest(url)
        if not manifest or not manifest['sources']:
            raise ResolveException('Video nie je dostupné')

        for q_index, source in enumerate(manifest['sources']):
            res_item = self.video_item()
            res_item['url'] = source['url']
            res_item['quality'] = q_index
            res_item['surl'] = source['url']
            result.append(res_item)
        return result
