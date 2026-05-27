from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Le bot est en ligne sale PD de merde !"

def run():
    # Render impose sa propre variable PORT
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
