import SimpleHTTPServer
import SocketServer
import random

PORT = 18000

template = """
<html>
    <head>
        <title>Trivial Application</title>        
	<base href="http://%(host)s/" />
    </head>

    <body>

        <h1>Trivial Application</h1>
        
        
        <div id="main">
            <a href="">Index Page</a> | <a href="print_headers">Print Headers</a> | <a href="numbers">Numbers</a>
            | <a href="cats/show_cat">A Cat</a>
        
            <hr/>
            %(message)s
            <hr/>
            <pre>
                %(info)s
            </pre>
        </div>
        
    </body>

</html>
"""



class TestingHTTPRequestHandler (SimpleHTTPServer.SimpleHTTPRequestHandler):


    def do_POST (self):
        if self.path == "/letterbox":    
                self.info_page("Letter Box, thankyou for your message")
        else:
            self.send_response (404, 'not found')

        
    def do_GET (self):
    
    
        path = self.path.split("?")[0]
        if path == "/":
            self.info_page ("""
                           Would you like to post to the letterbox?<br/>
                           <form method="POST" action="letterbox" >
                                <input type="text" name="message"/>
                                <input type="submit" />    
                            </form>
                """)
                
        elif path.startswith("/numbers"):
            numbers = [int(round(random.random() * 10)) for i in range(4)]
            self.info_page ("some special numbers for you %s" % numbers)


        elif path == "/cats/show_cat":
            self.info_page ("<img src='cat.jpeg' /><br/><a href='cat.jpeg' >original</a>")
           		
                
                
                
        elif path == "/print_headers":    
            self.info_page("Print Headers Page")
            
            
        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
    
    
    
    
    def info_page (self, message=""):
            
            info = "\n"
            info += "%s %s\n\n" % (self.command, self.path)
            
            for name, key in self.headers.items():
                info += "%s: %s\n" % (name, key)
            
            if int(self.headers.get('content-length', 0)) > 0:
                info += "\nHTTP BODY\n\n"
                info += self.rfile.read(int(self.headers['content-length']))
                info += "\n"
            
            doc = template % {'message':message, 'info':info, 'host': self.headers.get("host", "localhost:18000")}
            
            self.send_response(200)
            self.send_header("content-type", "text/html")
            self.send_header('content-length', len(doc))
            self.end_headers()
            self.wfile.write(doc)
            self.wfile.close()
            
    

Handler = TestingHTTPRequestHandler
httpd = SocketServer.TCPServer(("", PORT), Handler)
if __name__ == "__main__":
    print "serving at port", PORT
    httpd.serve_forever()

