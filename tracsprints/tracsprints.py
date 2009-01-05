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
        self.db = self.env.get_db_cnx()

   
    # IRequestHandler methods
    def match_request(self, req):
        self.env.log.debug("Match Request")
        serve = req.path_info.rstrip('/') == '/burndown'
        self.env.log.debug("Handle Request: %s" % serve)
        return serve
 
    def get_milestones(self):
        cursor = self.db.cursor()
        sql = "select name from milestone where (completed = 0)"
        cursor.execute(sql)
        self.env.log.debug("sql: %s" % sql)
        m = []
        for name in cursor: 
            self.env.log.debug("name: %s" % name)
            m.append(name)
        
        return m
    
    def get_users(self):
        devs = self.env.get_known_users()
        odevs = []
        for username,name,email in devs:
            data = {
                'username': username,
                'name': name,
                'email': email
            }
            odevs.append(data)
        self.env.log.debug("devs: %s" % odevs)
        return odevs

    def get_totals(self):
        cursor = self.db.cursor()
        sql = 'select status, count(*) as ncount from ticket where (milestone = "one") group by status'
        cursor.execute(sql)
        data = []
        c = 0
        colors = ['red', 'green', 'orange', 'yellow', 'purple']
        for status, count in cursor:
            n = {
                'status': status,
                'count': count,
                'percent': 0,
                'color': colors[c]
            }
            data.append(n)
            c = c + 1
        return data


    def process_request(self, req):
        data = {}
        data['milestones'] = self.get_milestones()
        data['devs'] = self.get_users()
        data['totals'] = self.get_totals()
        
        total = 0
        for i in data['totals']:
            total += i['count']

        total = float(total)

        for i in data['totals']:
            i['percent'] = (round((float(i['count']) / total), 3) * 100)
        

        data['percents'] = {
            'total': total
        }

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
