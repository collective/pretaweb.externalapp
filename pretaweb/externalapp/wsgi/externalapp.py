import re
import gzip
from urlparse import urlparse
from urllib import unquote
from lxml import etree
from lxml.html import document_fromstring, tostring
from StringIO import StringIO

from webob import Request
from wsgiproxy.app import WSGIProxyApp
from wsgiproxy.middleware import WSGIProxyMiddleware

try:
    from Products.CMFPlone.utils import safe_unicode
except ImportError:
    def safe_unicode(value, encoding='utf-8'):
        if isinstance(value, unicode):
            return value
        elif isinstance(value, basestring):
            try:
                value = unicode(value, encoding)
            except (UnicodeDecodeError):
                value = value.decode('utf-8', 'replace')
        return value

from .rules import DEFAULT_DIAZO_RULES

import logging

log = logging.getLogger('pretaweb.externalapp')


INCLUDE_PATTERN = re.compile(ur'<!--#include\s+virtual="([^"]*)"\s*-->')



class ExternalAppMiddleware(object):
    """Intercepts headers from application and if required
    sends proxy request to another url, applying xslt transformation
    to response body.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):

        
        #First we been to cache the request body
        # HACK - we should do this lazily and to disk?

        postbuf = environ['wsgi.input'].read()

        # get response from main app
        reqenvironment = environ.copy()
        reqenvironment['wsgi.input'] = StringIO(postbuf)

        req = Request(reqenvironment)
        resp = req.get_response(self.app)

        environ['wsgi.input'] = StringIO(postbuf)

        # this will tell us if we need to proxy request or not
        prefix = self._proxy_app_prefix(req, resp)

        # default response from main app, no proxy needed
        if not prefix:
            return resp(environ, start_response)

        # after main app read input restore file pointer
        # so we can check for includes
        # import pdb;pdb.set_trace()
        environ['wsgi.input'].seek(0)

        # extract SSI includes to see if we need to anything at all
        includes = self._extract_ssi_includes(req, resp)
        if not includes:
            return resp(environ, start_response)

        # parse, fetch and inject SSI includes
        proxy_resp = self._inject_ssi_includes(environ, includes, req, resp,
            prefix)

        return proxy_resp(environ, start_response)

    def _proxy_app_prefix(self, request, response):
        """Returns proxy app prefix: traversal path to exteranl app within
        main application.
        """
        prefix = None
        if response.headers.get('X-PROXY-PREFIX'):
            prefix = response.headers['X-PROXY-PREFIX']
        return prefix

    def _extract_ssi_includes(self, request, response):
        # do not parse if non html response
        if not response.content_type or \
           not response.content_type.startswith('text/html'):
            return []

        # get external app url from include
        includes = []
        for include in re.finditer(INCLUDE_PATTERN,
            safe_unicode(response.body)):
            virtual = unquote(include.group(1))

            # extract xpath, if no xpath found - insert full page body
            if u'filter_xpath' in virtual:
                xpath = virtual[
                    virtual.index(u'filter_xpath')+len(u'filter_xpath='):]
                url = virtual[:virtual.index(u'filter_xpath')]
            else:
                xpath = u'//body'
                url = virtual

            # parse url: http://external.app.url/path/%(externalapp_sub_path)s
            if u'/%(externalapp_sub_path)s' in url:
                url = url[:url.rindex(u'/%(externalapp_sub_path)s')]

            includes.append({
                'include': include.group(0),
                'url': url,
                'xpath': xpath,
            })

        return includes

    def _inject_ssi_includes(self, environ, includes, request, app_resp,
                             prefix):
        """Here we replace all ssi include in our application body with snippets
        (extracted by xpath expression) from proxy applications body, and set
        resulting html into proxy response object.
        """
        # keep track of already fetched external pages
        fetched = {}
        # keep track of inserted url + xpath pairs
        injected = []

        app_content = safe_unicode(app_resp.body)
        orig_base = request.host_url + prefix

        for include in includes:
            # check if we already injected given include
            virtual = include['include']
            if virtual in injected:
                continue

            # check if we already fetched this page
            url = include['url']
            if url in fetched:
                proxy_dom = fetched[url]
            else:
                proxy_resp = self._do_proxy_call(environ, app_resp, url, prefix)

                # if we have non-html response, return it w/o further processing
                if not proxy_resp.content_type or \
                   not proxy_resp.content_type.startswith('text/html'):
                    return proxy_resp

                proxy_content = safe_unicode(self._get_response_body(
                    proxy_resp))
                proxy_dom = document_fromstring(proxy_content, base_url=url)
                self._rewrite_links(proxy_dom, orig_base, url)

                # remember our proxy dom
                fetched[url] = proxy_dom

            # get xpath-ed snippet from proxy response body
            snippet = u''
            found = proxy_dom.xpath(include['xpath'])
            if len(found) > 0:
                snippet = u''.join([safe_unicode(tostring(f)) for f in found])

            # insert proxy piece into app body
            app_content = app_content.replace(virtual, snippet)

            # remember our injection
            injected.append(virtual)

        proxy_resp.body = app_content.encode('utf-8')
        return proxy_resp

    def _rewrite_links(self, dom, orig_base, proxied_base):
        """Rewrite links to make it work within our site."""
        exact_proxied_base = proxied_base
        if not proxied_base.endswith('/'):
            proxied_base += '/'
        exact_orig_base = orig_base
        if not orig_base.endswith('/'):
            orig_base += '/'

        def link_repl_func(link):
            """Rewrites a link to point to this proxy"""
            if link == exact_proxied_base:
                return exact_orig_base
            if not link.startswith(proxied_base):
                # External link, so we don't rewrite it
                return link
            new = orig_base + link[len(proxied_base):]
            return new

        dom.make_links_absolute()
        dom.rewrite_links(link_repl_func)

    def _copy_user_headers(self, _from, _to):
        """Copies user related headers from response to request"""
        for header in ('X-ZOPE-USER', 'X-ZOPE-USER-GROUPS',
            'X-ZOPE-USER-ROLES'):
            if _from.headers.get(header):
                _to.headers[header] = _from.headers[header]

    def _purge_cache_headers(self, request):
        """Remove any caching related headers."""
        for header in ('If-Modified-Since', 'If-None-Match'):
            if request.headers.has_key(header):
                del request.headers[header]

    def _do_proxy_call(self, environ, orig_response, url, prefix):
        # TODO: wrap it all into try/except and display main app page with
        # traceback in it
        log.debug('SSI proxy call to "%s"'%url)
        proxy = WSGIProxyApp(url)
        o = urlparse(url)
        middleware = WSGIProxyMiddleware(proxy, 
            scheme=o.scheme, domain=o.hostname, port=(o.port or '80'))

        # after parse includes process reads input restore file pointer so proxy
        # can still read all post data
        # environ['wsgi.input'].seek(0)

        reqenv = environ.copy()
        if reqenv['PATH_INFO'].startswith(prefix):
            reqenv['PATH_INFO'] = reqenv['PATH_INFO'][len(prefix):]
            reqenv['RAW_URI'] = reqenv['RAW_URI'][len(prefix):]

        proxy_req = Request(reqenv)

        # tweak proxy request headers a bit
        self._copy_user_headers(orig_response, proxy_req)
        self._purge_cache_headers(proxy_req)

        proxy_resp = proxy_req.get_response(middleware)

        # ignore redirects
        # TODO: redirect only when location is within proxy_url
        proxy_resp.location = None
        return proxy_resp

    def _transform(self, response, main_response, req, proxy_url, prefix):
        """Applies xslt transformation to proxied page.

        @response - response from proxied app
        @main_response - response from main application, we use it to get main
          page layout for transformation to apply, as theme for diazo
        @req - original request made by user from inside our main app
        @proxy_url - external application url
        @prefix - path to embedded external application within our main app
        """
        # do not transform non html reponse
        if not response.content_type or \
           not response.content_type.startswith('text/html'):
            return response

        # prepare rules file
        # TODO: get diazo rules from External Application content object
        rules = StringIO(safe_unicode(DEFAULT_DIAZO_RULES))

        # prepare theme file which is our application template
        theme = StringIO(safe_unicode(main_response.body))

        # compile our theme
        from diazo.compiler import compile_theme
        compiled_theme = compile_theme(rules, theme,
            xsl_params={
                'external_app_url': proxy_url,
                'app_url': req.host_url + prefix,
                'url': req.path_url,
                'path': req.path,
                'base_url': req.path_url
            }
        )
        transform = etree.XSLT(compiled_theme)

        # prepare content page which is external app page
        content = StringIO(safe_unicode(self._get_response_body(response)))
        content = etree.parse(content, etree.HTMLParser())

        # finally apply transformation
        transformed = transform(content)
        output = etree.tostring(transformed)
        response.body = output
        return response

    def _get_response_body(self, response):
        """If in gzip, then unzip it"""
        body = response.body
        if response.headers.get('Content-Encoding') == 'gzip':
            gzipper = gzip.GzipFile(fileobj=StringIO(body))
            body = gzipper.read()

            # fix headers
            response.headers['Content-Encoding'] = None

        return body

def make_externalapp_middleware(app, global_conf=None, **kw):
    return ExternalAppMiddleware(app, **kw)

def safe_unicode(value, encoding='utf-8'):
    """Converts a value to unicode, even it is already a unicode string.

        >>> from Products.CMFPlone.utils import safe_unicode

        >>> safe_unicode('spam')
        u'spam'
        >>> safe_unicode(u'spam')
        u'spam'
        >>> safe_unicode(u'spam'.encode('utf-8'))
        u'spam'
        >>> safe_unicode('\xc6\xb5')
        u'\u01b5'
        >>> safe_unicode(u'\xc6\xb5'.encode('iso-8859-1'))
        u'\u01b5'
        >>> safe_unicode('\xc6\xb5', encoding='ascii')
        u'\u01b5'
        >>> safe_unicode(1)
        1
        >>> print safe_unicode(None)
        None
    """
    if isinstance(value, unicode):
        return value
    elif isinstance(value, basestring):
        try:
            value = unicode(value, encoding)
        except (UnicodeDecodeError):
            value = value.decode('utf-8', 'replace')
    return value
