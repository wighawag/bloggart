import datetime
import hashlib

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.datastore import entity_pb
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import fix_path
import aetycoon
import config
import utils


HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"

TYPE_HOME = 0x0001 # 'Homepage'
TYPE_POST = 0x0002 # 'Post'
TYPE_PAGE = 0x0004 # 'Page'
TYPE_INDEX = 0x008 # 'Index' (i.e. Listing, Pagination, Tag, Archive, Search)
TYPE_OTHER = 0x0010 # 'Other' (i.e. atom feed, robots.txt, ...)

SITEMAP_DATA_MAPPING = {
   TYPE_HOME : { "priority" : 1, "changefreq" : "daily" },
   TYPE_POST : { "priority" : 0.8, "changefreq" : "weekly" },
   TYPE_PAGE : { "priority" : 0.7, "changefreq" : "monthly" },
   TYPE_INDEX : { "priority" : 0.3, "changefreq" : "weekly" },
   TYPE_OTHER : { "priority" : 0.3, "changefreq" : "yearly" }
}

if config.google_site_verification is not None:
    ROOT_ONLY_FILES = ['/robots.txt','/' + config.google_site_verification]
else:
    ROOT_ONLY_FILES = ['/robots.txt']

class StaticContent(db.Model):
  """Container for statically served content.

  The serving path for content is provided in the key name.
  """
  body = db.BlobProperty();
  content_type = db.StringProperty();
  status = db.IntegerProperty(required=True, default=200);
  last_modified = db.DateTimeProperty(required=True);
  etag = aetycoon.DerivedProperty(lambda x: hashlib.sha1(x.body).hexdigest());
  indexed = db.BooleanProperty(required=True, default=True);
  headers = db.StringListProperty();
  type = db.IntegerProperty(choices=(TYPE_HOME, TYPE_POST, TYPE_PAGE, TYPE_INDEX, TYPE_OTHER), default=TYPE_POST);


def get(path):
  """Returns the StaticContent object for the provided path.

  Args:
    path: The path to retrieve StaticContent for.
  Returns:
    A StaticContent object, or None if no content exists for this path.
  """
  entity = None;
  if ( config.memcaching ): 
    entity = memcache.get(path);
    
  if entity:
    entity = db.model_from_protobuf(entity_pb.EntityProto(entity))
  else:
    entity = StaticContent.get_by_key_name(path)
    if entity:
      memcache.set(path, db.model_to_protobuf(entity).Encode())

  return entity


def set(path, body, content_type, indexed=True, last_modified=None, type=TYPE_POST, **kwargs):
  import static
  """Sets the StaticContent for the provided path.

  Args:
    path: The path to store the content against.
    body: The data to serve for that path.
    content_type: The MIME type to serve the content as.
    indexed: Index this page in the sitemap?
    type: The type of StaticContent (a post? a page? an index?...).
    **kwargs: Additional arguments to be passed to the StaticContent constructor
  Returns:
    A StaticContent object.
  """
  if last_modified is None:
    last_modified = datetime.datetime.now(utils.tzinfo()).replace(second=0, microsecond=0)
  defaults = {
    "last_modified": last_modified,
  }
  defaults.update(kwargs)
  content = StaticContent(
      key_name = path,
      body = body,
      content_type = content_type,
      indexed = indexed,
      type = static.TYPE_HOME if path == '/' else type,
      **defaults);
  content.put()
  memcache.replace(path, db.model_to_protobuf(content).Encode())

  if indexed:
    regenerate_sitemap()

  return content

def regenerate_sitemap():
  try:
    now = datetime.datetime.now(utils.tzinfo()).replace(second=0, microsecond=0)
    eta = now.replace(second=0, microsecond=0) + datetime.timedelta(seconds=config.sitemap_generation_delay_sec)

    # Queue a Deferred Task to regenerate the 'sitemap.xml', in 5 minutes from now
    deferred.defer(
        utils._regenerate_sitemap,
        _name='sitemap-%s' % (now.strftime('%Y%m%d%H'),), # Run max 1 per hour
        _eta=eta)
  except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError), e:
    pass

def add(path, body, content_type, indexed=True, **kwargs):
  """Adds a new StaticContent and returns it.

  Args:
    As per set().
  Returns:
    A StaticContent object, or None if one already exists at the given path.
  """
  def _tx():
    if StaticContent.get_by_key_name(path):
      return None
    return set(path, body, content_type, indexed=indexed, **kwargs)
  return db.run_in_transaction(_tx)

def remove(path):
  """Deletes a StaticContent.

  Args:
    path: Path of the static content to be removed.
  """
  memcache.delete(path)
  def _tx():
    content = StaticContent.get_by_key_name(path)
    if not content:
      return
    content.delete()
  return db.run_in_transaction(_tx)

"""
	This function is a wrapper to "get", and redirects the client if it does not come from the correct HOST
	I see no reason to use this fucntion.
"""
def canonical_redirect(func):
  def _dec(self, path):
    if not self.request.host == config.host:
      self.redirect("%s://%s%s" % (self.request.scheme, config.host, path), True)
    else:
      func(self, path)
  return _dec

class StaticContentHandler(webapp.RequestHandler):
  PAGE_NOT_FOUND_404_PATH = "404.html";
  
  def output_content(self, content, serve=True):
    if content.content_type:
      self.response.headers['Content-Type'] = content.content_type
    last_modified = content.last_modified.strftime(HTTP_DATE_FMT)
    self.response.headers['Last-Modified'] = last_modified
    self.response.headers['ETag'] = '"%s"' % (content.etag,)
    for header in content.headers:
      key, value = header.split(':', 1)
      self.response.headers[key] = value.strip()
    if serve:
      self.response.set_status(content.status)
      self.response.out.write(content.body)
    else:
      self.response.set_status(304)

  #@canonical_redirect
  #I see no reason to decorate "get" with "canonical_redirect"
  def get(self, path):
    if not path.startswith(config.url_prefix):
      if path not in ROOT_ONLY_FILES:
        self.error(404)
        self.response.out.write(utils.render_template( StaticContentHandler.PAGE_NOT_FOUND_404_PATH ));
        return
    else:
      if config.url_prefix != '':
        path = path[len(config.url_prefix):]# Strip off prefix
        if path in ROOT_ONLY_FILES:# This lives at root
          self.error(404)
          self.response.out.write(utils.render_template( StaticContentHandler.PAGE_NOT_FOUND_404_PATH ));
          return
    if path == '':
        path = '/'
    content = get(path)
    if not content:
      self.error(404)
      self.response.out.write(utils.render_template( StaticContentHandler.PAGE_NOT_FOUND_404_PATH ));
      return

    serve = True
    if 'If-Modified-Since' in self.request.headers:
      try:
        last_seen = datetime.datetime.strptime(
            self.request.headers['If-Modified-Since'].split(';')[0],# IE8 '; length=XXXX' as extra arg bug
            HTTP_DATE_FMT)
        if last_seen >= content.last_modified.replace(microsecond=0):
          serve = False
      except ValueError, e:
        import logging
        logging.error('StaticContentHandler in static.py, ValueError:' + self.request.headers['If-Modified-Since'])
    if 'If-None-Match' in self.request.headers:
      etags = [x.strip('" ')
               for x in self.request.headers['If-None-Match'].split(',')]
      if content.etag in etags:
        serve = False
    self.output_content(content, serve)


application = webapp.WSGIApplication([
                ('(/.*)', StaticContentHandler),
              ])


def main():
  fix_path.fix_sys_path()
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
