from lxml import etree
from StringIO import StringIO

from webob import Request
from paste.proxy import Proxy
from wsgiproxy.app import WSGIProxyApp
from wsgiproxy.middleware import WSGIProxyMiddleware
from diazo.compiler import compile_theme

from Products.CMFPlone.utils import safe_unicode
from .rules import DEFAULT_DIAZO_RULES


class ExternalAppMiddleware(object):
    """Intercepts headers from application and if required
    sends proxy request to another url, applying xslt transformation
    to response body.
    """

    # TODO: handle errors during proxy fetch and xslt transformation
    # TODO: make proxy url and prefix configured

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        self.prefix = '/externalapp/news'
        self.proxy_url = 'http://www.test.com'
        self._orig_environ = environ.copy()
        
        # call application to get headers and decide what to do next
        # main_app_status, main_app_headers = None, None
        # def fake_start_response(status, headers, exc_info=None):
        #     main_app_status = status
        #     main_app_headers = headers

        # req = Request(environ)
        # resp = req.get_response(self.app)
        # if 

        
        # apply proxy only to news section
        if environ['PATH_INFO'].startswith(self.prefix):
            proxy = WSGIProxyApp(self.proxy_url)
            middleware = WSGIProxyMiddleware(proxy, pop_prefix=self.prefix)
            req = Request(environ)
            resp = req.get_response(middleware)

            # ignore redirects
            resp.location = None

            # apply transformation
            resp = self._transform(resp, self._orig_environ)
        else:
            req = Request(environ)
            resp = req.get_response(self.app)

        return resp(self._orig_environ, start_response)

    def _transform(self, response, environ):
        # do not transform non html reponse
        if not response.content_type or \
           not response.content_type.startswith('text/html'):
            return response

        # prepare rules file
        rules = StringIO(safe_unicode(DEFAULT_DIAZO_RULES))

        # prepare theme file which is our application template
        path = environ['PATH_INFO']
        environ['PATH_INFO'] = self.prefix
        req = Request(environ)
        theme = ''.join(self.app(environ, lambda x,y:None))
        environ['PATH_INFO'] = path
        theme = StringIO(safe_unicode(theme))

        # compile our theme
        absolute_prefix = '%s%s/' % (req.host_url, self.prefix)
        compiled_theme = compile_theme(rules, theme,
            absolute_prefix=absolute_prefix,
            # absolute_prefix='',
            xsl_params={
                'external_app_url': self.proxy_url,
                'app_url': absolute_prefix,
                'url': req.path_url,
                'path': req.path,
                'base_url': req.path_url
            }
        )
        transform = etree.XSLT(compiled_theme)

        # prepare content page which is external app page
        content = StringIO(safe_unicode(response.body))
        content = etree.parse(content, etree.HTMLParser())

        # finally apply transformation
        transformed = transform(content)
        output = etree.tostring(transformed)
        response.body = output
        return response

def make_externalapp_middleware(app, global_conf=None, **kw):
    return ExternalAppMiddleware(app, **kw)
