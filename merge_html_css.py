from pathlib import Path

workspace = Path(r"c:\Users\Mukesh\OneDrive\Desktop\AWS CI and CD pipeline for a containerized web app on AWS\aws-cicd-webapp")
html_path = workspace / "standalone-auth.html"
css_path = workspace / "app/static/style-webapp.css"

html = html_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
old = '<link rel="stylesheet" href="app/static/style-webapp.css">'
new = '<style>\n' + css + '\n</style>'

if old not in html:
    raise SystemExit("Target link tag not found in standalone-auth.html")

html = html.replace(old, new, 1)
html_path.write_text(html, encoding="utf-8")
print("Merged CSS into standalone-auth.html")
