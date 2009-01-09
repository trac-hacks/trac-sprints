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
from trac.perm import IPermissionRequestor




class TracSprints(Component):
    implements(IRequestHandler, ITemplateProvider, IPermissionRequestor)
    
    #key = Option('github', 'apitoken', '', doc=""" """)
    permission = ListOption('tracsprints', 'permission', '')
    

    def __init__(self):
        self.db = self.env.get_db_cnx()
        self.defaultOrder = ['closed', 'accepted', 'assigned', 'new', 'reopened']
        self.colors = ['green', 'yellow', 'orange', 'red', 'purple']
        self.scaleFactor = 3
        self.currentMilestone = False
        self.perm = self.config.get('tracsprints', 'permission', '').upper()
        
        if not self.perm:
            self.perm = 'ROADMAP_VIEW'

        self.env.log.debug("Using Permission: %s" % self.perm)


    def get_permission_actions(self):
        yield self.perm

   
    # IRequestHandler methods
    def match_request(self, req):
        self.env.log.debug("Match Request")
        serve = req.path_info.rstrip('/') == '/burndown'
        self.env.log.debug("Handle Request: %s" % serve)
        if not self.perm in req.perm:
            self.env.log.debug("NO Permission IV")
            return False

        if req.args.get('milestone'):
            cursor = self.db.cursor()
            sql = "select name from milestone where (name = '%s')" % req.args.get('milestone')
            cursor.execute(sql)
            for name in cursor:
                self.currentMilestone = req.args.get('milestone')

        return serve
 
    def get_milestones(self):
        cursor = self.db.cursor()
        sql = "select name from milestone where (completed = 0)"
        cursor.execute(sql)
        self.env.log.debug("sql: %s" % sql)
        m = []
        for name in cursor:
            self.env.log.debug("name: %s" % name)
            n = {
                'name': name,
                'count': 0
            }
            m.append(n)
        
        for item in m:
            sql = "select count(*) as nCount from ticket where (milestone = '%s')" % item['name']
            cursor.execute(sql)
            for count in cursor:
                item['count'] = count

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
        #self.env.log.debug("devs: %s" % odevs)
        return odevs

    def get_dev_totals(self):
        users = self.get_users()
        data = []
        for u in users:
            tot = self.get_ordered_totals(u['username'])
            count = 0
            for i in tot:
                count = count + i['count']

            if count > 0:
                u['totals'] = tot
                data.append(u)

        return data

    def get_totals(self, user=None):
        cursor = self.db.cursor()
        if not user == None:
            sql = 'select status, count(*) as ncount from ticket where (milestone = "%s") and (owner = "%s") group by status' % (self.currentMilestone, user)
        else:
            sql = 'select status, count(*) as ncount from ticket where (milestone = "%s") group by status' % self.currentMilestone
        cursor.execute(sql)
        data = {}
        c = 0
        for status, count in cursor:
            data[status] = {
                'status': status,
                'count': count,
                'percent': 0,
                'width': 0
            }
            c = c + 1
        return data

    def get_ordered_totals(self, user=None):
        data = self.get_totals(user)
        ordered = []

        for k in self.defaultOrder:
            try:
                ordered.append(data[k])
            except KeyError:
                n = {}
                n[k] = {
                    'status': k,
                    'count': 0,
                    'percent': 0,
                    'width': 0
                }
                ordered.append(n[k])

        c = 0
        total = 0
        for d in ordered:
            total += d['count']
            d['color'] = self.colors[c]
            c = c + 1

        total = float(total)
        
        if not user == None:
            width = 0
            for i in ordered:
                try:
                    i['percent'] = (round((float(i['count']) / total), 3) * 100)
                    i['width'] = round(i['percent'])
                except ZeroDivisionError:
                    i['percent'] = 1
                    i['width'] = round(i['percent'])

                if i['percent'] == 0:
                    i['percent'] = 1
                    i['width'] = 1

                width = width + i['width']
                if width > 100:
                    diff = width - 100
                    i['width'] = i['width'] - diff

        return ordered

    def process_request(self, req):
        data = {}
        if self.currentMilestone == False:
            data['milestones'] = self.get_milestones()
        else:
            data['title'] = self.currentMilestone
            data['devs'] = self.get_users()
            data['dev_totals'] = self.get_dev_totals()
            data['totals'] = self.get_ordered_totals()
            self.env.log.debug("defaultOrder: %s" % data['totals'])
            
            total = 0
            for i in data['totals']:
                total += i['count']

            total = float(total)

            if total > 0:
                data['hasWork'] = True
            else:
                data['noWork'] = True
            
            width = 0
            for i in data['totals']:
                try:
                    i['percent'] = (round((float(i['count']) / total), 3) * 100)
                    i['width'] = round(i['percent'])
                except ZeroDivisionError:
                    i['percent'] = 1
                    i['width'] = round(i['percent'])

                width = width + i['width']
                if width > 100:
                    diff = width - 100
                    i['width'] = i['width'] - diff

            data['barWidth'] = self.scaleFactor * 100           


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
