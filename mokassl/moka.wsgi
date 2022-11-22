import sys
import os

here = os.path.dirname(os.path.realpath(__file__))

sys.path.insert(0, here)
activate_this = '/var/www/mokassl/flask/bin/activate_this.py'
with open(activate_this) as file:
     exec(file.read(), dict(__file__=activate_this))
     
from main_parser import app as application
application.debug = True
