from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class RedirectHandler(webapp.RequestHandler):
    def post(self):
        self.redirect("/blog/")
    def get(self, path):
        self.redirect("/blog/")
                    
application = webapp.WSGIApplication([
                ('(/.*)', RedirectHandler),])

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
