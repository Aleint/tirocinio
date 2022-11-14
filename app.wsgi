import sys
sys.path.insert(0,'/var/www/html/prova')
sys.path.insert(0,'/var/www/html/prova/flask/lib/python3.10/site-packages')
from app import app as application
application.debug = True
