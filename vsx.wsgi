#vsx.wsgi
import sys
sys.path.insert(0, '/var/www/html/VSX')

from vsx import app as application