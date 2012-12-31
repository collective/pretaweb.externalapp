"""Definition of the External App content type
"""

from zope.interface import implements

from Products.Archetypes import atapi
from Products.ATContentTypes.content import folder
from Products.ATContentTypes.content import schemata

# -*- Message Factory Imported Here -*-
from pretaweb.externalapp import externalappMessageFactory as _

from pretaweb.externalapp.interfaces import IExternalApp
from pretaweb.externalapp.config import PROJECTNAME

ExternalAppSchema = folder.ATFolderSchema.copy() + atapi.Schema((

    # -*- Your Archetypes field definitions here ... -*-

    atapi.StringField(
        'url',
        storage=atapi.AnnotationStorage(),
        widget=atapi.StringWidget(
            label=_(u"URL"),
            description=_(u"External Application Root URL"),
        ),
        required=True,
        default=_(u"http://"),
        validators=('isURL'),
    ),


    atapi.StringField(
        'username',
        storage=atapi.AnnotationStorage(),
        widget=atapi.StringWidget(
            label=_(u"Username"),
            description=_(u"Username to Login into External Application"),
        ),
    ),


    atapi.StringField(
        'password',
        storage=atapi.AnnotationStorage(),
        widget=atapi.PasswordWidget(
            label=_(u"Password"),
            description=_(u"Password to Login into External Application"),
        ),
    ),


))

# Set storage on fields copied from ATFolderSchema, making sure
# they work well with the python bridge properties.

ExternalAppSchema['title'].storage = atapi.AnnotationStorage()
ExternalAppSchema['description'].storage = atapi.AnnotationStorage()

schemata.finalizeATCTSchema(
    ExternalAppSchema,
    folderish=True,
    moveDiscussion=False
)


class ExternalApp(folder.ATFolder):
    """External Application Entry Point"""
    implements(IExternalApp)

    meta_type = "ExternalApp"
    schema = ExternalAppSchema

    title = atapi.ATFieldProperty('title')
    description = atapi.ATFieldProperty('description')

    # -*- Your ATSchema to Python Property Bridges Here ... -*-
    url = atapi.ATFieldProperty('url')

    username = atapi.ATFieldProperty('username')

    password = atapi.ATFieldProperty('password')


atapi.registerType(ExternalApp, PROJECTNAME)
