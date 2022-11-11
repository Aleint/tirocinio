from flask import Flask,render_template
from jinja2.utils import markupsafe

app = Flask(__name__)


@app.route("/")
def home():

    return render_template('prova.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
