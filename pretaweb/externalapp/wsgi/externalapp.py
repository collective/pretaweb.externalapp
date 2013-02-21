import re
import gzip
from urlparse import urlparse
from urllib import unquote
from lxml import etree
from StringIO import StringIO

from webob import Request
from wsgiproxy.app import WSGIProxyApp
from wsgiproxy.middleware import WSGIProxyMiddleware
from diazo.compiler import compile_theme

from Products.CMFPlone.utils import safe_unicode
from .rules import DEFAULT_DIAZO_RULES


# TODO: fix <base> tag either on plone level with custom viewlet or with diazo
# rules, so we always have /app/ and if needed sub-path to current page within
# external app to make all relative urls on a page work

INCLUDE_PATTERN = re.compile(ur'<!--#include\s+virtual="([^"]*)"\s*-->')

class ExternalAppMiddleware(object):
    """Intercepts headers from application and if required
    sends proxy request to another url, applying xslt transformation
    to response body.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # get response from main app
        req = Request(environ.copy())
        resp = req.get_response(self.app)

        # this will tell us if we need to proxy request or not
        # TODO: this data we should get from ssi includes
        proxy_url, prefix = self._proxy_app_url(req, resp)

        # default response from main app, no proxy needed
        if not proxy_url:
            return resp(environ, start_response)

        # after main app read input restore file pointer so we can check for
        # includes
        environ['wsgi.input'].seek(0)

        # extract SSI includes to see if we need to anything at all
        includes = self._extract_ssi_includes(req, resp)
        if not includes:
            return resp(environ, start_response)

        # do proxy stuff
        proxy_resp = self._do_proxy_call(environ, resp, proxy_url, prefix)

        # inject SSI includes
        proxy_resp = self._inject_ssi_includes(includes, proxy_resp, resp)

        return proxy_resp(environ, start_response)

    def _inject_ssi_includes(self, includes, proxy_resp, app_resp):
        """Here we replace all ssi include in our application body with snippets
        (extracted by xpath expression) from proxy application body, and set
        resulting html into proxy response object.
        """
        proxy_content = safe_unicode(self._get_response_body(proxy_resp))
        proxy_dom = etree.parse(StringIO(proxy_content), etree.HTMLParser())
        app_content = safe_unicode(app_resp.body)

        injected = []
        for include in includes:
            # check if we already injected given include
            virtual = include['include']
            if virtual in injected:
                continue

            # get xpath-ed snippet from proxy response body
            snippet = u''
            found = proxy_dom.xpath(include['xpath'])
            if len(found) > 0:
                snippet = u''.join([etree.tostring(f) for f in found])

            # insert proxy piece into app body
            app_content = app_content.replace(virtual, snippet)

            # remember our injection
            injected.append(virtual)

        proxy_resp.body = app_content.encode('utf-8')
        return proxy_resp

    def _extract_ssi_includes(self, request, response):
        # do parse if non html response
        if not response.content_type or \
           not response.content_type.startswith('text/html'):
            return []

        # TODO: process external app url from include, for now we only
        # get it from ExternalApp header sent to us from zope
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

            includes.append({
                'include': include.group(0),
                'url': url,
                'xpath': xpath,
            })

        return includes

    def _proxy_app_url(self, request, response):
        """Returns root proxy app url and traversal path to exteranl app within
        main application.
        """
        url = prefix = None
        if response.headers.get('X-PROXY-TO'):
            url, prefix = response.headers['X-PROXY-TO'].split('||')
            # make sure our proxy url has no trailing slash
            if url.endswith('/'):
                url = url[:-1]
        return url, prefix

    def _copy_user_headers(self, _from, _to):
        """Copies user related headers from response to request"""
        for header in ('X-ZOPE-USER', 'X-ZOPE-USER-GROUPS',
            'X-ZOPE-USER-ROLES'):
            if _from.headers.get(header):
                _to.headers[header] = _from.headers[header]

    def _do_proxy_call(self, environ, orig_response, url, prefix):
        # TODO: wrap it all into try/except and display main app page with
        # traceback in it
        proxy = WSGIProxyApp(url)
        o = urlparse(url)
        middleware = WSGIProxyMiddleware(proxy, pop_prefix=prefix,
            scheme=o.scheme, domain=o.hostname, port=(o.port or '80'))

        # after parse includes process reads input restore file pointer so proxy
        # can still read all post data
        environ['wsgi.input'].seek(0)

        proxy_req = Request(environ.copy())
        self._copy_user_headers(orig_response, proxy_req)
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
