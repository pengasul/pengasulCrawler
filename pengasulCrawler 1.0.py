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

continue_crawling = True
CUSTOM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 pengasulCrawler/1.0",
    "X-Contact": "Discord: veryharam"
}

def signal_handler(signal, frame):
    global continue_crawling
    print("Ctrl+C pressed. Stopping crawling...")
    continue_crawling = False
    
signal.signal(signal.SIGINT, signal_handler)

def get_random_url():
    url_length = random.randint(6, 10)  # generated url length range
    letters = string.ascii_lowercase
    random_domain = ''.join(random.choice(letters) for _ in range(url_length))
    return f"http://{random_domain}.com"


def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def log_findings(log_dir, url, content, ip_address, hostname, subdirectories, emails):
    filename = re.sub(r'[^\w]', '_', hostname) + '.txt'
    log_path = os.path.join(log_dir, filename)
    
    with open(log_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"URL: {url}\n")
        log_file.write(f"IP Address: {ip_address}\n")
        log_file.write(f"Hostname: {hostname}\n")
        log_file.write(f"Content Preview: {content[:100]}...\n\n")
        log_file.write(f"Subdirectories:\n")
        for subdir in subdirectories:
            log_file.write(f"  {subdir}\n")
        log_file.write(f"\nEmails:\n")
        for email in emails:
            log_file.write(f"  {email}\n")


def log_error(log_dir, error_message):
    log_path = os.path.join(log_dir, 'error_log.txt')
    with open(log_path, 'a') as log_file:
        log_file.write(f"{error_message}\n")

def resolve_hostname(url):
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        
        # resolving HTTPS
        try:
            ip_address = socket.gethostbyname(hostname)
            requests.get(f"https://{hostname}")  # Test HTTPS connection
            return ip_address, hostname, "https"
        except:
            pass

        # if HTTPS fails try resolving HTTP
        try:
            ip_address = socket.gethostbyname(hostname)
            requests.get(f"http://{hostname}")  # Test HTTP connection
            return ip_address, hostname, "http"
        except:
            pass
        
        return None, None, None  # return None if both fail
    except socket.gaierror:
        return None, None, None


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

def crawl(log_dir, url, max_depth, current_depth, visited):
    if not continue_crawling:
        return
    
    if current_depth < 0 or url in visited:
        return

    try:
        # resolve hostname and protocol
        ip_address, hostname, protocol = resolve_hostname(url)
        if not ip_address or not hostname:
            print(f"Failed to resolve {url}: Could not resolve hostname.")
            return

        # test the connection
        test_url = f"{protocol}://{hostname}"
        response = requests.get(test_url, headers=CUSTOM_HEADERS, timeout=3)

        if response.status_code != 200:
            print(f"Failed to fetch {url}: Status code {response.status_code}")
            return

        visited.add(url)
        page_content = response.text

        soup = BeautifulSoup(page_content, 'html.parser')
        subdirectories = extract_subdirectories(url, soup)
        emails = extract_emails(page_content)
        
        # log the findings
        log_findings(log_dir, url, page_content, ip_address, hostname, subdirectories, emails)

        # find all links on the page and continue crawling
        for subdir in subdirectories:
            if is_valid_url(subdir):
                # decrement the current depth for the next level of crawling
                next_depth = current_depth - 1
                crawl(log_dir, subdir, max_depth, next_depth, visited)
    except (requests.RequestException, socket.gaierror) as e:
        error_message = f"Failed to fetch {url}: {e}"
        print(error_message)
        log_error(log_dir, error_message)

def start_crawling(max_depth):
    # create a directory for today's date
    today = datetime.now().strftime('%Y-%m-%d')
    log_dir = os.path.join(os.getcwd(), today)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # variables for tracking visited URLs
    visited = set()
    
    global continue_crawling

    while continue_crawling:  # continue crawling until the user stops the program
        # generate a random URL
        start_url = get_random_url()

        # crawl the URL with the specified depth
        crawl(log_dir, start_url, max_depth, max_depth, visited)

def main():
    depth = int(input("Enter max depth for random URL crawling: ").strip())
    max_depth = depth
    start_crawling(depth)

if __name__ == "__main__":
    main()
