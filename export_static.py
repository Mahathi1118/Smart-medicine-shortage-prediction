"""Builds a static index.html (data embedded) so the dashboard works on GitHub Pages
or by double-clicking the file. Run:  python export_static.py
"""
import json
from medishare.service import build_dashboard

html = open("templates/index.html", encoding="utf-8").read()
data = json.dumps(build_dashboard("data"))
old = 'fetch("/api/dashboard").then(r => r.json()).then(d => {'
assert old in html
new = "Promise.resolve(" + data.replace("</", "<\\/") + ").then(d => {"
open("index.html", "w", encoding="utf-8").write(html.replace(old, new))
print("Wrote index.html")
