from zope.component import adapts
from zope.publisher.interfaces import IRequest
from ZPublisher.BaseRequest import DefaultPublishTraverse

from ..interfaces import IExternalApp


class ExternalAppTraverser(DefaultPublishTraverse):
    """Traversal adapter for External Application sub-requests"""

    adapts(IExternalApp, IRequest)

    def publishTraverse(self, request, name):
        if name != 'app':
            return super(ExternalAppTraverser, self).publishTraverse(request,
                name)

        path = ''
        if request['TraversalRequestNameStack']:
            path = '/'.join(reversed(request['TraversalRequestNameStack']))
            # do not do any deeper traversal
            request['TraversalRequestNameStack'] = []

        # set path variable so that External App view knows the url
        # to handle
        request.set('external_app_path', path)

        return self.context
