"""Check the guide, real ZIP download, PDF, and both HTML exports in a browser."""
import argparse
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=ROOT/'site')
    parser.add_argument('--out',type=Path,default=ROOT/'target/accessible-showcase-ui')
    parser.add_argument('--browser',default='chrome')
    parser.add_argument('--base-url')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    server=None
    if args.base_url:
        base=args.base_url.rstrip('/')
    else:
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(args.site.resolve())))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}'
    assets=ROOT/'docs/assets/accessible-showcase-alpha6'
    manifest=json.loads((assets/'source.json').read_text(encoding='utf-8'))
    validation=json.loads((assets/'validation.json').read_text(encoding='utf-8'))
    cases=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel=args.browser,headless=True)
            try:
                for width in (1440,390,320):
                    context=browser.new_context(viewport={'width':width,'height':1000},accept_downloads=True)
                    try:
                        page=context.new_page();errors=[]
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        response=page.goto(base+'/guides/accessible-showcase/',wait_until='networkidle')
                        assert response.status==200
                        assert page.get_by_role('heading',level=1).inner_text().startswith('An accessible document')
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        page.screenshot(path=str(args.out/f'guide-{width}.png'))
                        with page.expect_download() as downloaded:
                            page.get_by_role('link',name='Download the source kit',exact=True).click()
                        target=args.out/f'project-{width}.zip'
                        downloaded.value.save_as(str(target))
                        assert sha256(target.read_bytes()).hexdigest()==manifest['zip_sha256']
                        pdf=context.request.get(base+'/assets/accessible-showcase-alpha6/common-ground-guide.pdf')
                        assert pdf.status==200 and sha256(pdf.body()).hexdigest()==validation['pdf_sha256']
                        page.get_by_role('link',name='Open the responsive HTML',exact=True).click()
                        page.wait_for_load_state('networkidle');page.evaluate('document.fonts.ready')
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        assert page.locator('h1').count()==1 and page.locator('th[scope=col]').count()==3
                        assert page.locator('img').evaluate('x=>x.complete && x.naturalWidth>0')
                        if width<800:
                            assert page.locator('.programs').evaluate("x=>getComputedStyle(x).gridTemplateColumns.split(' ').length")==1
                        page.keyboard.press('Tab')
                        assert page.evaluate('document.activeElement.tagName')=='A'
                        page.screenshot(path=str(args.out/f'html-{width}.png'),full_page=True)
                        page.goto(base+'/assets/accessible-showcase-alpha6/guide-unstyled.html',wait_until='networkidle')
                        assert page.locator('style,[style],link[rel=stylesheet]').count()==0
                        assert page.locator('.program-card').count()==3 and page.locator('th[scope=col]').count()==3
                        assert not errors,errors
                        cases.append({'width':width,'guide':True,'download':True,'pdf_hash':True,
                                      'responsive_html':True,'unstyled_html':True,'keyboard_link':True})
                    finally:
                        context.close()
                version=browser.version
            finally:
                browser.close()
    finally:
        if server: server.shutdown();server.server_close()
    report={'ok':True,'browser':version,'cases':cases,'pdf_sha256':validation['pdf_sha256']}
    (args.out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    main()
