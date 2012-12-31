from zope.interface import Interface
# -*- Additional Imports Here -*-
from zope import schema

from pretaweb.externalapp import externalappMessageFactory as _



class IExternalApp(Interface):
    """External Application Entry Point"""

    # -*- schema definition goes here -*-
    url = schema.TextLine(
        title=_(u"URL"),
        required=True,
        description=_(u"External Application Root URL"),
    )
#
    username = schema.TextLine(
        title=_(u"Username"),
        required=False,
        description=_(u"Username to Login into External Application"),
    )
#
    password = schema.TextLine(
        title=_(u"Password"),
        required=False,
        description=_(u"Password to Login into External Application"),
    )
#
