from zope.component import adapts
from zope.publisher.interfaces import IRequest

from ZPublisher.BaseRequest import DefaultPublishTraverse

from ..interfaces import IExternalApp


class ExternalAppTraverser(DefaultPublishTraverse):
    """Traversal adapter for External Application sub-requests"""

    adapts(IExternalApp, IRequest)

    def publishTraverse(self, request, name):
        if name == 'app':
            # do not do any deeper traversal
            if request['TraversalRequestNameStack']:
                request['TraversalRequestNameStack'] = []

            request.set('app_on', True)
            return super(ExternalAppTraverser, self).publishTraverse(request,
                'view')

        return super(ExternalAppTraverser, self).publishTraverse(request,
            name)
