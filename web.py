# web.py - optional: skeleton for webhook hosting (Flask)
# Only needed if you want webhook deployment. Leave unused for polling.

from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/")
def index():
    return "AnonChat webhook endpoint"

@app.route("/health")
def health():
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
  
