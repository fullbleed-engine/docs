"""Check the real generated walkthrough, captions, and playground link in Chromium."""
import argparse
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from playwright.sync_api import sync_playwright, expect
from walkthrough_server import RangeRequestHandler

parser = argparse.ArgumentParser()
parser.add_argument('--site', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--browser', choices=['chromium', 'chrome'], default='chromium')
args = parser.parse_args()
site = args.site.resolve()
out = args.out.resolve()
assert (site / 'guides/playground-walkthrough/index.html').is_file()
assert not out.exists()
out.mkdir(parents=True)
assets = site / 'assets/walkthroughs/invoice-20261102'
asset_hashes = {name: sha256((assets / name).read_bytes()).hexdigest() for name in ['walkthrough.mp4', 'poster.png', 'captions.vtt']}
assert (assets / 'captions.vtt').read_text(encoding='utf8').startswith('WEBVTT\n')
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(RangeRequestHandler, directory=str(site)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f'http://127.0.0.1:{server.server_address[1]}'
errors = []
results = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({'channel': 'chrome'} if args.browser == 'chrome' else {}))
        browser_version = browser.version
        try:
            for label, viewport in [('desktop', {'width': 1280, 'height': 900}), ('mobile', {'width': 390, 'height': 844})]:
                context = browser.new_context(viewport=viewport, color_scheme='light')
                try:
                    media_requests = []
                    context.on('page', lambda page: page.on('pageerror', lambda error: errors.append(str(error))))
                    context.on('request', lambda request: media_requests.append(request.url) if request.url.endswith('/walkthrough.mp4') else None)
                    playground = None
                    if label == 'desktop':
                        playground = context.new_page()
                        response = playground.goto(base + '/playground/', wait_until='domcontentloaded')
                        assert response and response.status == 200
                        expect(playground.locator('#pg-html')).to_be_enabled(timeout=120000)
                        expect(playground.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
                        edited = playground.locator('#pg-html').input_value() + '\n<!-- Keep this edit while watching the walkthrough. -->'
                        playground.locator('#pg-html').fill(edited)
                        link = playground.locator('#pg-walkthrough-link')
                        expect(link).to_have_attribute('target', '_blank')
                        assert 'noopener' in link.get_attribute('rel').split()
                        with playground.expect_popup() as opened:
                            link.click()
                        page = opened.value
                        page.wait_for_load_state('domcontentloaded')
                        assert page.url == base + '/guides/playground-walkthrough/'
                        assert playground.locator('#pg-html').input_value() == edited
                    else:
                        page = context.new_page()
                        response = page.goto(base + '/guides/playground-walkthrough/', wait_until='domcontentloaded')
                        assert response and response.status == 200
                    video = page.locator('#invoice-walkthrough')
                    expect(video).to_be_visible()
                    assert video.get_attribute('preload') == 'none'
                    assert video.get_attribute('autoplay') is None
                    assert video.evaluate('(video) => video.controls')
                    expect(page.locator('#transcript')).to_be_visible()
                    text = page.locator('main').inner_text()
                    expect(page.locator('main h1')).to_contain_text('Customize an invoice in the playground')
                    expect(page.locator('meta[name="description"]')).to_have_attribute('content', 'Watch a short Fullbleed walkthrough: edit an invoice with HTML and CSS, download the PDF, and run the exported Node.js project locally.')
                    assert 'title: Customize' not in text and 'description: Watch' not in text
                    for required in ['Willow', 'Node.js 22 or newer', 'npm ci --ignore-scripts', 'npm run render', 'output/document.pdf']:
                        assert required in text, required
                    assert not media_requests, 'Video downloaded before the viewer requested playback.'
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    await_fonts = 'document.fonts.status === "loaded"'
                    page.wait_for_function(await_fonts)
                    page.screenshot(path=str(out / f'{label}-poster.png'), full_page=True)
                    video.evaluate('(video) => video.play()')
                    page.wait_for_function('document.querySelector("#invoice-walkthrough").currentTime >= 1', timeout=30000)
                    video.evaluate('(video) => video.pause()')
                    media = video.evaluate('(video) => ({width:video.videoWidth,height:video.videoHeight,duration:video.duration,time:video.currentTime,error:video.error?.message||null,frames:video.getVideoPlaybackQuality().totalVideoFrames})')
                    assert media['width'] == 1920 and media['height'] == 1080 and 15 < media['duration'] < 120
                    assert media['time'] >= 1 and media['frames'] > 0 and not media['error']
                    assert media_requests
                    track = video.locator('track')
                    expect(track).to_have_attribute('kind', 'captions')
                    expect(track).to_have_attribute('srclang', 'en')
                    video.evaluate('(video) => { video.textTracks[0].mode="hidden"; }')
                    page.wait_for_function('document.querySelector("#invoice-walkthrough").textTracks[0].cues?.length > 0', timeout=15000)
                    captions = video.evaluate('(video) => Array.from(video.textTracks[0].cues, cue => ({start:cue.startTime,end:cue.endTime,text:cue.text}))')
                    assert len(captions) >= 5 and captions[0]['start'] == 0
                    assert all(0 <= cue['start'] < cue['end'] <= media['duration'] + 0.1 for cue in captions)
                    assert abs(captions[-1]['end'] - media['duration']) < 0.15
                    page.screenshot(path=str(out / f'{label}-playback.png'), full_page=True)
                    if playground:
                        page.close()
                        assert playground.locator('#pg-html').input_value() == edited
                    results.append({'viewport': label, 'media': media, 'captionCues': len(captions), 'mediaDeferredUntilPlayback': True,
                                    'horizontalOverflow': False, 'playgroundEditsPreserved': True if playground else None})
                finally:
                    context.close()
            assert not errors
        finally:
            browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
assert not thread.is_alive()
record = {'at': datetime.now(timezone.utc).isoformat(), 'status': 'passed', 'assets': asset_hashes,
          'results': results, 'pageErrors': errors, 'serverStopped': True, 'browser': args.browser, 'browserVersion': browser_version,
          'scope': 'Actual generated page, desktop/mobile layout, playback and captions, optional link preserving source edits. No general accessibility-conformance claim.'}
(out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
print(json.dumps(record))
