from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class ExternalAppView(BrowserView):

    template = ViewPageTemplateFile('externalapp.pt')

    def __call__(self):
        if self.request.get('app_on'):
            # set http headers to use in proxy wsgi middleware
            # TODO: ensure prefix is proper in virtual host setup
            self.request.response.setHeader('X-PROXY-TO', '%s||%s' %
                (self.context.url, '%s/app' %
                '/'.join(self.context.getPhysicalPath())))
        return self.template()
