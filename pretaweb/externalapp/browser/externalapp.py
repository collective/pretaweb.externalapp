import sys
import logging
from StringIO import StringIO
from lxml import etree
import urllib

from plone.memoize.instance import memoize
from diazo.compiler import compile_theme

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone.utils import safe_unicode


logger = logging.getLogger('pretaweb.externalapp')
def logException(msg, context=None):
    logger.exception(msg)
    if context is not None:
        error_log = getattr(context, 'error_log', None)
        if error_log is not None:
            error_log.raising(sys.exc_info())

# TODO: make comprehensive url resolvers work: absolute, with base, w/o base,
# relative links (., .., /, etc...), with base on current page/folder, with base
# from app root

# TODO: insert base in case there is no base tag in content page

# TODO: move rules into ExternApp content type field
RULES = """
<rules
    xmlns="http://namespaces.plone.org/diazo"
    xmlns:css="http://namespaces.plone.org/diazo/css"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xi="http://www.w3.org/2001/XInclude">

  <!-- Insert only main content body from external page -->
  <replace css:theme-children="#content" css:content-children="#content" />
<!--  <replace css:theme-children="#content" css:content-children="body" />-->
<!--  <copy css:theme="base" css:content="base" />-->

  <!-- Adjust base tag href -->
<!--  <replace css:theme="base" css:content="base" css:if-content="base" />-->
  <replace css:theme="base" attributes="href" css:content="a" />
<!--    <xsl:copy-of select="$base_url" />
  </replace>-->
<!--  <replace css:theme="base" css:if-not-content="base">
    <base>
      <xsl:attribute name="href"><xsl:copy-of select="$base_url" /></xsl:attribute>
    </base>
  </replace>-->
  
<!--  
  <xsl:template match="base">
    <xsl:copy>
      <xsl:attribute name="href"><xsl:copy-of select="$base_url" /></xsl:attribute>
    </xsl:copy>
  </xsl:template>
-->

  <!-- Handle Elements with ACTION attribute -->
  <xsl:template match="*[@action]">
    <xsl:copy>

      <!-- Update ACTION attribute -->
      <xsl:choose>

        <!-- Absolute Link -->
        <xsl:when test="starts-with(@action, $external_app_url)">
          <xsl:attribute name="action"><xsl:value-of select="$app_url" /><xsl:value-of select="substring(@action,  string-length($external_app_url)+2)" /></xsl:attribute>
        </xsl:when>

        <!-- Relative Link starting from / -->
        <xsl:when test="starts-with(@action, '/')">
          <xsl:attribute name="action"><xsl:value-of select="$app_url" />.<xsl:value-of select="@action" /></xsl:attribute>
        </xsl:when>

        <!-- Else: only add app part -->
        <xsl:otherwise>
          <xsl:copy-of select="@action" />
        </xsl:otherwise>
      </xsl:choose>

      <xsl:copy-of select="@*[name()!='action']|node()" />
    </xsl:copy>
  </xsl:template>

  <!-- Handle Elements with HREF attribute -->
  <xsl:template match="*[@href][name()!='base']">
    <xsl:copy>

      <!-- Update HREF attribute -->
      <xsl:choose>

        <!-- Absolute Link -->
        <xsl:when test="starts-with(@href, $external_app_url)">
          <xsl:attribute name="href"><xsl:value-of select="$app_url" /><xsl:value-of select="substring(@href,  string-length($external_app_url)+2)" /></xsl:attribute>
        </xsl:when>

        <!-- Relative Link starting from / -->
        <xsl:when test="starts-with(@href, '/')">
          <xsl:attribute name="href"><xsl:value-of select="$app_url" />.<xsl:value-of select="@href" /></xsl:attribute>
        </xsl:when>

        <!-- Else: copy it as it is -->
        <xsl:otherwise>
          <xsl:copy-of select="@href" />
        </xsl:otherwise>

      </xsl:choose>

      <xsl:copy-of select="@*[name()!='href']|node()" />
    </xsl:copy>
  </xsl:template>

  <!-- Handle Elements with SRC attribute -->
  <xsl:template match="*[@src]">
    <xsl:copy>

      <!-- Update SRC attribute -->
      <xsl:choose>

        <!-- Absolute Link -->
        <xsl:when test="starts-with(@src, $external_app_url)">
          <xsl:attribute name="src">$app_url<xsl:value-of select="substring(@src,  string-length($external_app_url)+2)" /></xsl:attribute>
        </xsl:when>

        <!-- Relative Link starting from / -->
        <xsl:when test="starts-with(@src, '/')">
          <xsl:attribute name="src"><xsl:value-of select="$app_url" />.<xsl:value-of select="@src" /></xsl:attribute>
        </xsl:when>

        <!-- Else: copy it as it is -->
        <xsl:otherwise>
          <xsl:copy-of select="@src" />
        </xsl:otherwise>
      </xsl:choose>

      <xsl:copy-of select="@*[name()!='src']|node()" />
    </xsl:copy>
  </xsl:template>
</rules>
"""

# TODO: switch to using this prefix instead of making link absolute by ourselves
absolute_prefix = ""

class ExternalAppView(BrowserView):

    template = ViewPageTemplateFile('externalapp.pt')

    def __init__(self, context, request):
        super(ExternalAppView, self).__init__(context, request)
        self._path = request.get('external_app_path', '')

    def __call__(self):
        # try to open external resource
        try:
            resource = self._open()
        except Exception, e:
            msg = 'Error during fetching external app page (%s): %s' % (
                self._cur_url(), str(e))
            logException(msg, self.context)
            return self.template(body=msg)

        # try to transform external resource
        try:
            output = self._transform(resource)
        except Exception, e:
            msg = 'Error during transforming external app page (%s): %s' % (
                self._cur_url(), str(e))
            logException(msg, self.context)
            return self.template(body=msg)

        # copy headers
        self.copy_headers(resource)

        return output

    def copy_headers(self, resource):
        _set = self.request.response.setHeader
        for k, v in resource.info().dict.items():
            _set(k, v)

    def _open(self):
        url = self._login()
        opener = urllib.FancyURLopener()
        if self.request.method == 'POST':
            data = urllib.urlencode(self.request.form)
            resource = opener.open(url, data)
        else:
            resource = opener.open(url)
        return resource

    def _transform(self, resource):
        # do not transform non html reponse
        if not resource.info().getheader('Content-Type').startswith(
           'text/html'):
            return resource.read()

        # prepare rules file
        rules = StringIO(safe_unicode(RULES))

        # prepare theme file which is our application template
        theme = StringIO(safe_unicode(self._theme()))

        # compile our theme
        compiled_theme = compile_theme(rules, theme,
            absolute_prefix=absolute_prefix,
            xsl_params={'external_app_url': self._external_app_url(),
            'app_url': self._app_url(),
            'url': self._cur_url(),
            'path': self._path, 'base_url': self._base_url()})
        transform = etree.XSLT(compiled_theme)

        # prepare content page which is external app page
        content = StringIO(safe_unicode(resource.read()))
        content = etree.parse(content, etree.HTMLParser())

        # finally apply transformation
        transformed = transform(content)
        output = etree.tostring(transformed)
        return output

    def _theme(self):
        return self.template()

    def _login(self):
        # TODO: make login work: Basic Auth
        # Basic Auth
        if self.context.username and self.context.password:
            url = 'https://%s:%s@arm.auscert.org.au/' % (self.context.username,
                self.context.password)
        else:
            url = self._cur_url()
        return url

    def _cur_url(self):
        """Returns current request url.

        This is entry point for parent traverser to let us know current request
        url, by setting _url attribute on this view directly.
        """
        url = '%s%s' % (self._external_app_url(), self._path and
            ('/' + self._path) or '')
        return url

    def _base_url(self):
        path = self._path
        if path:
            path = path + '/'
        return '%s/app/%s' % (self.context.absolute_url(), path)

    @memoize
    def _app_url(self):
        return '%s/app/' % self.context.absolute_url()

    @memoize
    def _external_app_url(self):
        url = self.context.url
        if url.endswith('/'):
            url = url[:-1]
        return url
