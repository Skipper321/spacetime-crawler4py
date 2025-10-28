import re
import tokenizer
import logging
from urllib.parse import urlparse, urljoin, urldefrag
from collections import defaultdict

from bs4 import BeautifulSoup

logging.basicConfig(
    filename="crawler_log.txt",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

STOPWORDS = set(open("stopwords.txt").read().split())
word_frequencies = defaultdict(int)
unique_urls = set()

def scraper(url, resp):
    global unique_urls

    links = extract_next_links(url, resp)
    valid_links = []

    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]

    for link in valid_links:
        unique_urls.add(link)

    if len(unique_urls) % 100 == 0:
        logger.info(f"CRAWLED {len(unique_urls)} unique pages so far.")

    return valid_links

# Gets sitemap's URLs from the url response (Assumes that the response of the url is already an xml file)
def get_sitemap_urls(resp) -> list:
    sitemap_urls = []

    soup = BeautifulSoup(resp.text, 'xml')
    for item in soup.find_all("loc"):
        print(type(item))
        if '.xml' in item.text:
            # # Resolve the relative URLS to absolute/fragments?
            sitemap_urls.add(item)
    
    return [(sitemap_urls)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    links = []
    global word_frequencies

    # Handling bad error responses
    if resp.status != 200 or resp.raw_response is None: 
        # Log resp.error for debugging 
        logger.error(f"BAD RESPONSE {resp.status}: {url} | Error: {getattr(resp, 'error', None)}")
        return links 

    # Ensure that content is HTML / XML
    content_type = resp.raw_response.headers.get("Content-Type", "")

    if "xml" in content_type:
        try:
            sitemap_links = get_sitemap_urls(resp)
            links += sitemap_links
            return links
        except Exception as e: 
            print(f"[EXTRACTION ERROR] Problem while extracting links from sitemap url {url}: {e}")
            return links

    if "text/html" not in content_type: 
        # Log content error for debugging 
        logger.info(f"SKIPPED NON-HTML: {url} | Content-Type: {content_type}")
        return links

    # Parse through content 
    try: 
        html = resp.raw_response.content
        soup = BeautifulSoup(html, "lxml")            

        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        tokens = tokenizer.tokenize(text)
        for t in tokens:
            if t not in STOPWORDS:
                word_frequencies[t] += 1
    
    except Exception as e:
        print(f"Error parsing HTML at {url}: {e}")
        return links
    
    try: 
        # Extract all <a> tags with href attributes 
        for tag in soup.find_all("a", href = True):
            href = tag["href"].strip()
            if not href:
                continue

            # Resolve the relative URLS to absolute 
            abs_url = urljoin(url, href)

            # Remove fragments 
            abs_url, _ = urldefrag(abs_url)

            links.append(abs_url)

            # Use for Debugging 
            # print(f"[SUCCESS] Found {len(links)} links on {url}")
    except Exception as e: 
        print(f"[EXTRACTION ERROR] Problem while extracting links from {url}: {e}")

    # only return the URLS within the domains and paths mentioned in project description
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        # Only allowing http/https
        if parsed.scheme not in set(["http", "https"]):
            return False

        # We only want to allow subdomains of UCI ICS
        domain = parsed.netloc.lower()
        allowed_domains = {
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        }
        if not any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains):
            logger.info(f"BLOCKED (outside domain): {url}")
            return False

        # Trap blocking
        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()

        if "/events/tag/talks/" in path_lower:
            # logger.warning(f"TRAP BLOCKED (event talks archive): {url}")
            return False

        if "tribe-bar-date=" in query_lower or "eventdisplay=past" in query_lower:
            # logger.warning(f"TRAP BLOCKED (calendar pagination): {url}")
            return False

        if re.search(r"\d{4}-\d{2}(-\d{2})?", url):
            # logger.warning(f"DATE TRAP BLOCKED (calendar): {url}")
            return False
        

        # Ignoring doku action modes
        # https://www.dokuwiki.org/devel:action_modes

        if f"?do=edit" in url:
            logger.info(f"SKIPPED (markdown file detected): {url}")
            return False
        
        if f"?do=login" in url:
            logger.info(f"SKIPPED (login page detected): {url}")

        # backlink: Shows a list of pages that link to the current page.
        if f"?do=backlink" in url:
            logger.info(f"SKIPPED (backlink page detected): {url}")

        ignore_in_url = ["robots.txt", "&", f"%3A", f"?do=edit"]
        for item in ignore_in_url:
            if (url.count(item) > 1):
                logger.warning(f"TRAP BLOCKED (url with repeating pattern): {url}")
                return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
