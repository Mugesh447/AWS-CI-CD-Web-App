from pathlib import Path

base = Path(__file__).resolve().parent
html_path = base / 'standalone-auth.html'
css_path = base / 'app' / 'static' / 'style-webapp.css'

html = html_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')
needle = '<link rel="stylesheet" href="app/static/style-webapp.css">'
if needle not in html:
    raise SystemExit('needle not found')
new_html = html.replace(needle, '<style>\n' + css + '\n</style>', 1)
html_path.write_text(new_html, encoding='utf-8')
updated = html_path.read_text(encoding='utf-8')
print('style_present=', '<style>' in updated)
print('link_present=', 'href="app/static/style-webapp.css"' in updated)
print('line_6=', updated.splitlines()[5])
