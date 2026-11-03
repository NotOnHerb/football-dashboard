"""Stamps index.html from template.html: every __VER__ becomes a version (the current UTC minute, so browsers fetch
the new js/ and assets/ files) and __DATE__ the data's build date.

build.py calls stamp() at the end of every build, and pages.py when it redeploys the published data with new page
code. Run on its own from the repo root, `python restamp.py` restamps the page for the data.json already here
(META.built): no network, no Odds API credits.
"""
import datetime, json


def stamp(date, template='template.html', out='index.html'):
    """Writes OUT from TEMPLATE with __VER__ = the current UTC minute and __DATE__ = DATE. Returns the page."""
    ver = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M')
    html = open(template, encoding='utf-8').read().replace('__VER__', ver).replace('__DATE__', date)
    with open(out, 'w', encoding='utf-8') as f: f.write(html)
    return html


if __name__ == '__main__':
    built = json.load(open('data.json', encoding='utf-8'))['META']['built']
    print('index.html', len(stamp(built).encode()), 'bytes | data built', built)
