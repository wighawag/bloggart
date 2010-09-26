import logging
import wsgiref.handlers
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.api import memcache

# Fix sys.path
import fix_path
fix_path.fix_sys_path()

# Import markup module from lib/
import jsmin
import cssmin

class CssMinifier( webapp.RequestHandler ):
   def get(self, requestedTheme, requestedCss):
      self.response.out.write(requestedTheme + "{ css: "+requestedCss+"}");
      return;
      
class JSMinifier( webapp.RequestHandler ):
   def get(self, requestedTheme, requestedJS):
      self.response.out.write("var " + requestedTheme + " = '"+requestedJS+"';");
      return;

# """
# Request Handler for "./style/*".
# This allows to apply Templating and Minification to CSS Stylesheets.
# """
# class CssMinifier( webapp.RequestHandler ):      
#    def get( self, requestedCssFilename ):
#       logging.debug("Requested CSS: "+requestedCssFilename);
#       # Build the Path to the CSS and check if we already have rendered it and is sitting in Memcache ready to use
#       cssPath = os.path.join( os.path.dirname( __file__ ), 'style/' + requestedCssFilename );
#       if ( not os.path.exists(cssPath) ):
#          logging.error("CSS not found: "+cssPath);
#          # Client Error 4xx - 404 Not Found
#          util.setErrorResponse(self, 404);
#          return;
#       
#       cssPathMemcacheKey = cssPath + '-' + self.request.headers['User-Agent'];
#       cssRenderingResult = None;
#       if ( config_constants.AGGRESSIVE_MEMCACHING ):
#          cssRenderingResult = memcache.get(cssPathMemcacheKey);
#       
#       # In case the Memcache didn't contain the CSS rendered
#       if ( cssRenderingResult is None ):         
#          # Retrieving 'browser_name' and 'browser_version'
#          browserDetailsDic = util.getBrowserDetails(self.request.headers['User-Agent']);
#       
#          logging.debug("Rendering CSS: "+requestedCssFilename);   
#          # Render the CSS
#          cssRenderingResult = template.render(cssPath, browserDetailsDic);
# 
#          # Minify ONLY IF NOT Debugging
#          if ( config_constants.LOGGING_LEVEL != logging.DEBUG ):
#             logging.debug("Minifying CSS: "+requestedCssFilename);
#             # Minify CSS
#             cssRenderingResult = cssmin.minify(cssRenderingResult);
#          
#          # Save in Memcache
#          memcache.set(cssPathMemcacheKey, cssRenderingResult);
#          
#       # Setting Content-Type as "text/javascript"
#       self.response.headers['Content-Type'] = 'text/css'
#       logging.debug("Serving Minified CSS: "+requestedCssFilename);
#       # Rendering the Result
#       self.response.out.write( cssRenderingResult );
# 
# 
# """
# Request Handler for "./js/*".
# This allows to apply Templating and Minification to Javascript.
# """
# class JSMinifier( webapp.RequestHandler ):      
#    def get( self, requestedJsFilename ):
#       logging.debug("Requested Javascript: "+requestedJsFilename);
#       # Build the Path to the Javascript and check if we already have rendered it and is sitting in Memcache ready to use
#       jsPath = os.path.join( os.path.dirname( __file__ ), 'js/' + requestedJsFilename );
#       if ( not os.path.exists(jsPath) ):
#          logging.error("Javascript not found: "+jsPath);
#          # Client Error 4xx - 404 Not Found
#          util.setErrorResponse(self, 404);
#          return;
#       
#       jsPathMemcacheKey = jsPath + '-' + self.request.headers['User-Agent'];
#       jsRenderingResult = None;
#       if ( config_constants.AGGRESSIVE_MEMCACHING ):
#          jsRenderingResult = memcache.get(jsPathMemcacheKey);
#       
#       # In case the Memcache didn't contain the Javascript rendered
#       if ( jsRenderingResult is None ):         
#          # Retrieving 'browser_name' and 'browser_version'
#          browserDetailsDic = util.getBrowserDetails(self.request.headers['User-Agent']);
#       
#          logging.debug("Rendering Javascript: "+requestedJsFilename);   
#          # Render the Javascript
#          jsRenderingResult = template.render(jsPath, browserDetailsDic);
# 
#          # Minify ONLY IF NOT Debugging
#          if ( config_constants.LOGGING_LEVEL != logging.DEBUG ):
#             logging.debug("Minifying Javascript: "+requestedJsFilename);
#             # Minify Javascript
#             jsRenderingResult = jsmin.jsmin(jsRenderingResult);
#          
#          # Save in Memcache
#          memcache.set(jsPathMemcacheKey, jsRenderingResult);
#          
#       # Setting Content-Type as "text/javascript"
#       self.response.headers['Content-Type'] = 'text/javascript'
#       logging.debug("Serving Minified Javascript: "+requestedJsFilename);
#       # Rendering the Result
#       self.response.out.write( jsRenderingResult );

# Creating a WSGI Application Handler
application = webapp.WSGIApplication([
                                      ( '/static/([^/]+)/(.*\.js)$', JSMinifier ),
                                      ( '/static/([^/]+)/(.*\.css)$', CssMinifier )
                                      ], debug=True )

def main():
   #logging.getLogger().setLevel(config_constants.LOGGING_LEVEL);
   # Executing the WSGI Application
   wsgiref.handlers.CGIHandler().run( application )

if __name__ == "__main__":
   main()
