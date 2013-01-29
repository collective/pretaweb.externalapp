from AccessControl import getSecurityManager
from Acquisition import aq_inner

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName


class ExternalAppView(BrowserView):

    template = ViewPageTemplateFile('externalapp.pt')

    def __call__(self):
        if self.request.get('app_on'):
            context = aq_inner(self.context)
            response = self.request.response

            # set http headers to use in proxy wsgi middleware
            # TODO: ensure prefix is proper in virtual host setup
            response.setHeader('X-PROXY-TO', '%s||%s' % (context.url,
                '/'.join(context.getPhysicalPath())))

            # set user related headers for external app to login plone user
            user = getSecurityManager().getUser()
            if user and getattr(user, 'name', None) != 'Anonymous User':
                response.setHeader('X-ZOPE-USER', user.getId())
                response.setHeader('X-ZOPE-USER-GROUPS',
                    ','.join(user.getGroups()))
                response.setHeader('X-ZOPE-USER-ROLES',
                    ','.join(user.getRolesInContext(context)))

        return self.template()
