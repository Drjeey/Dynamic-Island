"""Keeps the page-to-Python bridge limited to Lumi's own pages and to the public methods of IslandAPI and SettingsAPI.

pywebview hides underscore names only from the list of functions it shows the page; when a call arrives it follows
any dotted name (for example "_ctrl.apply_setting"). It also gives the bridge to whatever document the webview
ends up showing. harden() closes both gaps before the windows are created. Call it once, before webview.start."""
import logging
import re
from urllib.parse import urlsplit

import webview

log = logging.getLogger(__name__)

# pywebview's own messages, which it handles before looking at the js_api object
_INTERNAL = {'pywebviewMoveWindow', 'pywebviewEventHandler', 'pywebviewAsyncCallback',
             'pywebviewStateUpdate', 'pywebviewStateDelete'}
_PUBLIC_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]*')  # one public method: no dots, no leading underscore
_done = False


def allowed_call(func_name):
    """True for a call the page may make: one of pywebview's own, or a public method name of the API object."""
    return isinstance(func_name, str) and (func_name in _INTERNAL or bool(_PUBLIC_NAME.fullmatch(func_name)))


def same_origin(url, page_url):
    """True when url is on the same scheme, host and port as the page Lumi loaded (the loopback ui/ server)."""
    try:
        a, b = urlsplit(str(url)), urlsplit(str(page_url))
    except ValueError:
        return False
    return bool(b.scheme) and (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port)


def harden():
    global _done
    if _done:
        return
    _done = True
    # The pages are served over loopback HTTP, so WebView2 never needs file:// access between files
    webview.settings['ALLOW_FILE_URLS'] = False

    from webview import util
    from webview.platforms import edgechromium

    original_call = util.js_bridge_call

    def guarded_call(window, func_name, param, value_id):
        if not allowed_call(func_name):
            log.warning('Refused a bridge call to %r', func_name)
            return
        return original_call(window, func_name, param, value_id)

    util.js_bridge_call = guarded_call
    edgechromium.js_bridge_call = guarded_call  # the WebView2 backend imported the original by name

    chrome = edgechromium.EdgeChrome
    original_init, original_start = chrome.__init__, chrome.on_navigation_start

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            self.webview.AllowExternalDrop = False  # a dropped link or file would otherwise open in the window
        except Exception as e:  # older WebView2 controls don't have the property; navigation is still checked below
            log.debug('AllowExternalDrop unavailable: %s', e)

    def on_navigation_start(self, sender, args):
        page = self.pywebview_window.real_url
        uri = str(args.Uri)
        if page and not same_origin(uri, page) and uri != 'about:blank':
            log.warning('Blocked navigation away from Lumi to %s', uri[:200])
            args.Cancel = True
            return
        return original_start(self, sender, args)

    chrome.__init__ = init
    chrome.on_navigation_start = on_navigation_start
