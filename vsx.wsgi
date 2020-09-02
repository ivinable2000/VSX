#vsx.wsgi
import sys
sys.path.insert(0, '/var/www/VSX')

from vsx import app as application