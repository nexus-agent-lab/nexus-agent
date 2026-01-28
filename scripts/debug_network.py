import logging
import os
import socket

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_network")

TARGET_URL = "https://api.telegram.org/bot{}/getMe"
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def check_dns():
    hostname = "api.telegram.org"
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"✅ DNS Resolution for {hostname}: {ip}")
    except Exception as e:
        logger.error(f"❌ DNS Resolution failed for {hostname}: {e}")


def check_requests(use_proxy=False):
    url = "https://api.telegram.org"
    proxies = {}
    if use_proxy and PROXY_URL:
        proxies = {"http": PROXY_URL, "https": PROXY_URL}
        logger.info(f"Testing with Proxy: {PROXY_URL}")
    else:
        logger.info("Testing Direct Connection (No Proxy)")

    try:
        resp = requests.get(url, proxies=proxies, timeout=10)
        logger.info(f"✅ Connection Successful! Status Code: {resp.status_code}")
        return True
    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        return False


if __name__ == "__main__":
    print("-" * 30)
    print("📡 Network Diagnostic Tool")
    print("-" * 30)

    check_dns()

    print("\n--- Test 1: Direct Connection ---")
    check_requests(use_proxy=False)

    if PROXY_URL:
        print("\n--- Test 2: Connection via Proxy ---")
        check_requests(use_proxy=True)
    else:
        print("\nℹ️ No TELEGRAM_PROXY_URL configured. Skipping proxy test.")

    print("-" * 30)
