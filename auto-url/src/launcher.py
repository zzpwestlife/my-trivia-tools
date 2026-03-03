import subprocess
import urllib.parse
from typing import Optional
from .models import Logger


class URLLauncherService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.logger = Logger("URLLauncherService")
        self._initialized = True

    def open_url(self, url: str, browser_bundle_id: Optional[str] = None, new_window: bool = True) -> bool:
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            if browser_bundle_id:
                if new_window:
                    script = f'''
                    tell application id "{browser_bundle_id}"
                        activate
                        make new window
                        set URL of active tab of front window to "{url}"
                    end tell
                    '''
                else:
                    script = f'''
                    tell application id "{browser_bundle_id}"
                        activate
                        open location "{url}"
                    end tell
                    '''
                subprocess.run(['osascript', '-e', script], check=True)
                self.logger.info(f"Opened URL with {browser_bundle_id}: {url}")
            else:
                if new_window:
                    subprocess.run(['open', '-n', url], check=True)
                else:
                    subprocess.run(['open', url], check=True)
                self.logger.info(f"Opened URL: {url}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to open URL {url}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error opening URL {url}: {e}")
            return False

    def open_urls(self, urls, browser_bundle_id: Optional[str] = None, delay: float = 0.5, new_window: bool = True):
        import time
        for url_item in urls:
            if url_item.enabled:
                self.open_url(url_item.url, browser_bundle_id, new_window)
                time.sleep(delay)
        self.logger.info(f"Opened {len(urls)} URLs")

    def validate_url(self, url: str) -> tuple[bool, Optional[str]]:
        if not url:
            return False, "URL 不能为空"

        if not url.startswith(('http://', 'https://')):
            try:
                result = urllib.parse.urlparse(url)
                if not result.netloc:
                    return False, "URL 格式不正确"
            except:
                pass

        return True, None

    def get_installed_browsers(self) -> list[dict]:
        browsers = []
        try:
            script = '''
            tell application "System Events"
                set browserList to {}
                repeat with proc in (every process whose background only is false)
                    try
                        set procName to name of proc
                        if procName contains "Chrome" or procName contains "Safari" or procName contains "Firefox" or procName contains "Edge" or procName contains "Brave" or procName contains "Opera" then
                            set end of browserList to procName
                        end if
                    end try
                end repeat
                return browserList
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if result.returncode == 0:
                browser_names = [b.strip() for b in result.stdout.strip().split('\n') if b.strip()]
                for name in browser_names:
                    browsers.append({
                        'name': name,
                        'bundle_id': self._get_bundle_id(name)
                    })
        except Exception as e:
            self.logger.error(f"Failed to get browsers: {e}")
        return browsers

    def _get_bundle_id(self, app_name: str) -> Optional[str]:
        bundle_ids = {
            'Safari': 'com.apple.Safari',
            'Google Chrome': 'com.google.Chrome',
            'Microsoft Edge': 'com.microsoft.edgemac',
            'Firefox': 'org.mozilla.firefox',
            'Brave Browser': 'com.brave.Browser',
        }
        return bundle_ids.get(app_name)
