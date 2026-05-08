"""
SkyRoute Graph - Flask Web Application.

REST API layer that bridges the backend graph loader with the HTML/JS frontend.
"""

import os
from flask import Flask, render_template, send_from_directory
from routes.graph_routes import graph_bp

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "presentacion", "vistas")
STYLES_DIR = os.path.join(BASE_DIR, "presentacion", "estilos")
SCRIPTS_DIR = os.path.join(BASE_DIR, "presentacion", "scripts")

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STYLES_DIR,
    static_url_path="/estilos",
)

app.register_blueprint(graph_bp)

@app.route("/scripts/<path:filename>")
def scripts_static(filename):
    """Serve static JS files from the presentation scripts directory."""
    return send_from_directory(SCRIPTS_DIR, filename)

@app.route("/")
def index():
    """Serve the graph demo page."""
    return render_template("graph_index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)