from trac.core import *
from pkg_resources import resource_filename
from trac.config import Option, IntOption, ListOption, BoolOption
from trac.web.api import IRequestHandler, Href
from trac.util.translation import _
from trac.web.chrome import add_stylesheet, add_script, INavigationContributor, ITemplateProvider
import datetime
from trac.web.chrome import Chrome
from trac.util.datefmt import utc, to_timestamp
from genshi.template import TemplateLoader
from genshi.filters.transform import Transformer
from trac.web.api import ITemplateStreamFilter



class TracSprints(Component):
    implements(IRequestHandler, ITemplateProvider)
    
    #key = Option('github', 'apitoken', '', doc="""Your GitHub API Token found here: https://github.com/account, """)

    def __init__(self):
        pass
 

   
    # IRequestHandler methods
    def match_request(self, req):
        self.env.log.debug("Match Request")
        serve = req.path_info.rstrip('/') == '/sprints'
        self.env.log.debug("Handle Request: %s" % serve)
        return serve
    
    def process_request(self, req):
        #req.send_response(200)
        #req.send_header('Content-Type', 'text/plain')
        #req.end_headers()
        #req.write('Hello world!')
        data = {}
        add_script(req, "tracsprints/tracsprints.js")
        add_stylesheet(req, "tracsprints/tracsprints.css")
        return 'sprints.html', data, None


    def get_htdocs_dirs(self):
        """Return the absolute path of a directory containing additional
        static resources (such as images, style sheets, etc).
        """
        return [('tracsprints', resource_filename(__name__, 'htdocs'))]
 
    def get_templates_dirs(self):
        """Return the absolute path of the directory containing the provided
        genshi templates.
        """
        rtn = [resource_filename(__name__, 'templates')]
        return rtn
