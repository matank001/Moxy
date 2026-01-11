"""
Browser management for browser-use
"""

import asyncio
import threading
import sys
from browser_use import Browser
from browser_use.browser import ProxySettings
from . import proxy_manager

# Global browser instance
_browser_instance = None
_browser_lock = threading.Lock()


def _run_browser(proxy_port):
    """Run the browser in a separate thread with its own event loop"""
    global _browser_instance
    
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def start_browser():
        global _browser_instance
        try:
            # Configure browser to use mitmproxy
            proxy = ProxySettings(
                server=f"http://127.0.0.1:{proxy_port}",  # mitmproxy port
                bypass=""
            )
            
            browser = Browser(
                proxy=proxy,
                disable_security=True,  # Required to ignore SSL certificate errors from mitmproxy
                keep_alive=True,
                # user_data_dir="./browser/",
            )
            
            await browser.start()
            _browser_instance = browser
            print(f"✅ Browser started with proxy on port {proxy_port}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Error starting browser: {e}", file=sys.stderr)
            loop.stop()
    
    try:
        loop.run_until_complete(start_browser())
        # Keep the event loop running
        loop.run_forever()
    except Exception as e:
        print(f"❌ Browser thread error: {e}", file=sys.stderr)
    finally:
        loop.close()


async def get_or_create_browser():
    """Get existing browser instance or create a new one"""
    global _browser_instance
    
    with _browser_lock:
        if _browser_instance is not None:
            return _browser_instance
        
        # Check if proxy is running
        if not proxy_manager.is_proxy_running():
            print("⚠️  Proxy is not running. Starting proxy...", file=sys.stderr)
            if not proxy_manager.start_proxy():
                raise RuntimeError("Failed to start proxy")
            
            # Wait a bit for proxy to start
            import time
            time.sleep(2)
        
        proxy_port = proxy_manager.get_proxy_port()
        
        # Configure browser to use mitmproxy
        proxy = ProxySettings(
            server=f"http://127.0.0.1:{proxy_port}",
            bypass=""
        )
        
        browser = Browser(
            proxy=proxy,
            disable_security=True,
            keep_alive=True,
        )
        
        await browser.start()
        _browser_instance = browser
        print(f"✅ Browser session created with proxy on port {proxy_port}", file=sys.stderr)
        return browser


def start_browser():
    """Start a new browser instance with proxy settings (legacy function for UI)"""
    # Check if proxy is running
    if not proxy_manager.is_proxy_running():
        print("⚠️  Proxy is not running. Please start the proxy first.", file=sys.stderr)
        return False
    
    proxy_port = proxy_manager.get_proxy_port()
    
    try:
        # Start browser in a separate thread
        thread = threading.Thread(
            target=_run_browser,
            args=(proxy_port,),
            daemon=True
        )
        thread.start()
        
        # Wait a bit to let browser start
        import time
        time.sleep(2)
        
        return True
    except Exception as e:
        print(f"❌ Error starting browser: {e}", file=sys.stderr)
        return False


