import os
import requests
from bs4 import BeautifulSoup
import random
import string
import socket
import re
import signal
from urllib.parse import urljoin, urlparse
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import json

# Constants
CUSTOM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 pengasulCrawler/1.0",
    "X-Contact": "Discord: veryharam"
}
CRAWL_DELAY = 1  # delay in seconds between requests
NUM_THREADS = 5  # number of threads for multithreading
TLD_LIST = ['.com', '.net', '.org']  # list of TLDs to use (.gov, .mil, .edu, etc were removed for better results)

# Global variables
continue_crawling = True
lock = threading.Lock()

def signal_handler(signal, frame):
    global continue_crawling
    print("Ctrl+C pressed. Stopping crawling...")
    continue_crawling = False

signal.signal(signal.SIGINT, signal_handler)

def get_random_url():
    url_length = random.randint(6, 10)  # generated url length range
    letters = string.ascii_lowercase
    random_domain = ''.join(random.choice(letters) for _ in range(url_length))
    tld = random.choice(TLD_LIST)
    return f"http://{random_domain}{tld}"

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def log_findings(log_dir, data):
    filename = re.sub(r'[^\w]', '_', data['hostname']) + '.json'
    log_path = os.path.join(log_dir, filename)

    with open(log_path, 'a', encoding='utf-8') as log_file:
        json.dump(data, log_file, indent=4)
        log_file.write('\n')

def log_error(log_dir, error_data):
    log_path = os.path.join(log_dir, 'error_log.json')
    with open(log_path, 'a', encoding='utf-8') as log_file:
        json.dump(error_data, log_file, indent=4)
        log_file.write('\n')

def resolve_hostname(url):
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        ip_address = socket.gethostbyname(hostname)
        return ip_address, hostname
    except socket.gaierror:
        return None, None

def extract_emails(content):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, content)

def extract_subdirectories(url, soup):
    subdirectories = set()
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href.startswith('/'):
            full_url = urljoin(url, href)
            subdirectories.add(full_url)
    return list(subdirectories)

def keyword_analysis(content):
    words = re.findall(r'\b\w+\b', content)
    keyword_freq = {}
    for word in words:
        word = word.lower()
        keyword_freq[word] = keyword_freq.get(word, 0) + 1
    sorted_keywords = sorted(keyword_freq.items(), key=lambda item: item[1], reverse=True)
    return [{"keyword": k, "frequency": v} for k, v in sorted_keywords[:10]]  # top 10 keywords

def crawl(log_dir, url, max_depth, current_depth, visited, session):
    if not continue_crawling:
        return

    if current_depth < 0 or url in visited:
        return

    try:
        ip_address, hostname = resolve_hostname(url)
        if not ip_address or not hostname:
            error_data = {
                "timestamp": str(datetime.now()),
                "url": url,
                "error": "Could not resolve hostname."
            }
            print(f"Error: {error_data['error']} for URL: {url}")
            log_error(log_dir, error_data)
            return

        # attempt to fetch the URL using HTTPS
        try:
            response = session.get(f"https://{hostname}", headers=CUSTOM_HEADERS, timeout=3)
            protocol = "https"
        except requests.RequestException:
            # if HTTPS fails fall back to HTTP
            try:
                response = session.get(f"http://{hostname}", headers=CUSTOM_HEADERS, timeout=3)
                protocol = "http"
            except requests.RequestException:
                response = None

        if response is None or response.status_code != 200:
            error_data = {
                "timestamp": str(datetime.now()),
                "url": url,
                "status_code": response.status_code if response else "N/A",
                "error": "Failed to fetch URL."
            }
            print(f"Error: {error_data['error']} for URL: {url} with status code: {error_data['status_code']}")
            log_error(log_dir, error_data)
            return

        with lock:
            visited.add(url)
        page_content = response.text

        soup = BeautifulSoup(page_content, 'html.parser')
        subdirectories = extract_subdirectories(url, soup)
        emails = extract_emails(page_content)
        keywords = keyword_analysis(page_content)

        data = {
            "timestamp": str(datetime.now()),
            "url": url,
            "ip_address": ip_address,
            "hostname": hostname,
            "status_code": response.status_code,
            "content_preview": page_content[:100] + "...",
            "subdirectories": subdirectories,
            "emails": emails,
            "top_keywords": keywords
        }

        log_findings(log_dir, data)

        for subdir in subdirectories:
            if is_valid_url(subdir):
                next_depth = current_depth - 1
                time.sleep(CRAWL_DELAY)
                crawl(log_dir, subdir, max_depth, next_depth, visited, session)
    except (requests.RequestException, socket.gaierror) as e:
        error_data = {
            "timestamp": str(datetime.now()),
            "url": url,
            "error": str(e)
        }
        print(f"Error: {error_data['error']} for URL: {url}")
        log_error(log_dir, error_data)

def start_crawling(max_depth, url_pattern=None):
    today = datetime.now().strftime('%Y-%m-%d')
    log_dir = os.path.join(os.getcwd(), today)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    visited = set()
    global continue_crawling

    with requests.Session() as session, ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        while continue_crawling:
            start_url = get_random_url() if not url_pattern else url_pattern
            executor.submit(crawl, log_dir, start_url, max_depth, max_depth, visited, session)

def main():
    depth = int(input("Enter max depth for random URL crawling: ").strip())
    max_depth = depth
    url_pattern = input("Enter URL pattern (leave blank for random URLs): ").strip() or None
    start_crawling(max_depth, url_pattern)

if __name__ == "__main__":
    main()
