from zope.interface import Interface
# -*- Additional Imports Here -*-
from zope import schema

from zope.i18nmessageid import MessageFactory
# Define a message factory for when this product is internationalised.
# This will be imported with the special name "_" in most modules. Strings
# like _(u"message") will then be extracted by i18n tools for translation.

externalappMessageFactory = MessageFactory('pretaweb.externalapp')


_ = externalappMessageFactory



class IExternalApp(Interface):
    """External Application Entry Point"""

    # -*- schema definition goes here -*-
    html_class = schema.TextLine(
        title=_(u"HTML Wrapper Class"),
        required=True,
        description=_(u"It is used on External App object view to bind Diazo xml rules."),
    )
#
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
