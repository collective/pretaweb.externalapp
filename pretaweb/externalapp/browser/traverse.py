from zope.component import adapts
from zope.publisher.interfaces import IRequest

from ZPublisher.BaseRequest import DefaultPublishTraverse

from ..interfaces import IExternalApp

PLONE_PATHS = (
    'folder_contents',
    'edit',
    'atct_edit',
    'updateLockInfo',
    'kssValidateField',
    '@@manage-content-rules',
    'manage-content-rules',
    '@@sharing',
    'sharing',
    'object_cut',
    'cutObject',
    'object_copy',
    'copyObject',
    'delete_confirmation',
    'object_rename',
    'select_default_view',
    'selectViewTemplate',
    'folder_factories',
    'createObject',
    'content_status_history',
    'content_status_modify',
)

class ExternalAppTraverser(DefaultPublishTraverse):
    """Traversal adapter for External Application sub-requests"""

    adapts(IExternalApp, IRequest)

    def publishTraverse(self, request, name):
        if name not in PLONE_PATHS:
            # do not do any deeper traversal
            if request['TraversalRequestNameStack']:
                request['TraversalRequestNameStack'] = []

            request.set('app_on', True)
            return super(ExternalAppTraverser, self).publishTraverse(request,
                'view')

        return super(ExternalAppTraverser, self).publishTraverse(request,
            name)
