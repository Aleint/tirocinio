import sys
import os

here = os.path.dirname(os.path.realpath(__file__))


sys.path.insert(0, here)


from lpager_server import app as application
