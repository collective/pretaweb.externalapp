
from wsgiproxy.app import WSGIProxyApp

class WSGIProxyPreserveHost (WSGIProxyApp):
    def setup_forwarded_environ(self, environ):
    	host = environ.get("HTTP_HOST", None)
        super(WSGIProxyPreserveHost, self).setup_forwarded_environ(environ)
        if host is not None:
        	environ["HTTP_HOST"] = host
        from pprint import pprint

def make_app(
    global_conf,
    href=None,
    secret_file=None):
    if href is None:
        raise ValueError(
            "You must give an href value")
    if secret_file is None and 'secret_file' in global_conf:
        secret_file = global_conf['secret_file']
    return WSGIProxyPreserveHost(href=href, secret_file=secret_file)
