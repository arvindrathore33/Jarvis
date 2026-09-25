from playwright.sync_api import sync_playwright
import os

def browse_target(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        page.goto(url, timeout=15000, wait_until='networkidle')
        data = {
            "title": page.title(),
            "url": page.url,
            "links": page.eval_on_selector_all("a", "els => els.map(e => e.href)")[:30],
            "forms": page.eval_on_selector_all("form", """els => els.map(e => ({
                action: e.action,
                method: e.method,
                inputs: Array.from(e.querySelectorAll('input')).map(i => ({
                    name: i.name, type: i.type
                }))
            }))"""),
            "scripts": page.eval_on_selector_all("script[src]", "els => els.map(e => e.src)")[:20],
            "comments": page.evaluate("""() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_COMMENT);
                const comments = [];
                while(walker.nextNode()) comments.push(walker.currentNode.data);
                return comments;
            }""")
        }
        browser.close()
        return data

def screenshot_target(url, path=None):
    if not path:
        path = os.path.expanduser("~/jarvis/output/screenshot.png")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=15000)
        page.screenshot(path=path, full_page=True)
        browser.close()
        return path

def intercept_requests(url):
    requests_log = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("request", lambda r: requests_log.append({
            "url": r.url,
            "method": r.method,
            "headers": dict(r.headers)
        }))
        page.goto(url, timeout=15000, wait_until='networkidle')
        browser.close()
        return requests_log[:30]
