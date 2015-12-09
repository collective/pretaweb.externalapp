# Overview

Make it easy to integrate external applications into plone efficiently and securely using middleware.

# Problem

You want to integrate an external app into your site. Diazo makes this easy via

```
<rules if-path="/myapp">
<replace css:theme="#content-container" css:content="#mycontent" href="http://example.com/form" />
</rules>
```

However this can result in running out zope instances really easily.
Plone is single threaded and synchronous so unless your external app is really
quick to respond then your zope instance is sitting idle unused while it's
waiting for a response. Since plone uses a lot of RAM it is an expensive to
scale up a lot of zope instances just to have them idle. The end result
queued requests, users waiting while CPU is still low.

# Solution

The solution is in three parts.

First run zope using wsgi and include a special middleware in front of zope.

```
[app:zope]
use = egg:Zope2#main
zope_conf = %(here)s/parts/instance/etc/zope.conf

[pipeline:main]
pipeline =
    egg:paste#evalerror
    egg:repoze.retry#retry
    egg:repoze.tm2#tm
    egg:pretaweb.externalapp#external_app
    zope

[server:main]
use = egg:paste#http
host = localhost
port = 8087
```

Next install the externalapp content type. This lets you determine which paths
in your site are taken over my your app.

Finally you add some diazo rules to determine how your external app will be
combined into your page.

```
<!-- A rule to determine that you are in the external app object in Plone -->
<rule css:if-content="#externalapp-myapp">
    <replace css:theme="#portal-column-content" css:content="div.main"
        href="http://my.external.app/path/to/%(externalapp_sub_path)s" method="ssi" />
</rule>
```


Optionally you can modify your app to accept the following headers

 - X-ZOPE-USER
 - X-ZOPE-USER-GROUPS
 - X-ZOPE-USER-ROLES

## How it works

- All requests are cached in the middleware including POST requests
- the request is first sent to zope/plone.
- if the request is for a externalapp object (or subpath) the result will
  be transformed by the diazo rule which includes ssi replace.
- the middleware will detect the ssi directive in the result.
- the middleware will replay the request with the added special user headers
- the middleware will combine the resulting two responses as per the SSI directive.
- the final combined response is returned to the user.

# Support

- Code repository:  https://github.com/collective/pretaweb.externalapp
- Report bugs at  https://github.com/collective/pretaweb.externalapp/issues

