import sys
sys.path.insert(0,'/home/ale/Desktop/prova/env/lib/python3.10/site-packages')

activate_this='/home/ale/Desktop/prova/env/bin/activate_this.py'
with open(activate_this) as file:
    exec(file.read(),dict(__file__=activate_this))
    from app import app as application
