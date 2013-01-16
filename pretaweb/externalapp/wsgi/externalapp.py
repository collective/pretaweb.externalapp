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

# TODO: handle at least Basic authentication

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
        proxy_url, prefix = self._proxy_app_url(req, resp)

        # default response from main app, no proxy needed
        if not proxy_url:
            return resp(environ, start_response)

        # do proxy stuff
        # TODO: fix REFERER, HTTP_ORIGIN, etc... headers to point to original
        # external app url if needed
        # TODO: wrap it all into try/except and display main app page with
        # traceback in it
        proxy = WSGIProxyApp(proxy_url)
        middleware = WSGIProxyMiddleware(proxy, pop_prefix=prefix)

        # after main app read input restore file pointer so proxy can still
        # read all post data
        environ['wsgi.input'].seek(0)

        proxy_req = Request(environ.copy())
        proxy_resp = proxy_req.get_response(middleware)

        # ignore redirects
        # TODO: redirect only when location is within proxy_url
        proxy_resp.location = None

        # apply transformation
        # TODO: wrap it all into try/except and display main app page with
        # traceback in it
        proxy_resp = self._transform(proxy_resp, resp, req, proxy_url, prefix)

        return proxy_resp(environ, start_response)

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
        content = StringIO(safe_unicode(response.body))
        content = etree.parse(content, etree.HTMLParser())

        # finally apply transformation
        transformed = transform(content)
        output = etree.tostring(transformed)
        response.body = output
        return response

def make_externalapp_middleware(app, global_conf=None, **kw):
    return ExternalAppMiddleware(app, **kw)
