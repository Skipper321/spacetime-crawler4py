import re
import tokenizer
import logging
from simhash import Simhash
from urllib.parse import urlparse, urljoin, urldefrag
from collections import defaultdict
from bs4 import BeautifulSoup

# ---------------- LOGGING SETUP ---------------- #
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

# ---------------- GLOBALS ---------------- #
STOPWORDS = set(open("stopwords.txt").read().split())
word_frequencies = defaultdict(int)
unique_urls = set()
unique_pages = set()
longest_page = {"url": None, "words": 0}

# ---------------- MAIN SCRAPER ---------------- #
def scraper(url, resp):
    global unique_urls

    links = extract_next_links(url, resp)
    valid_links = [link for link in links if is_valid(link)]

    for link in valid_links:
        unique_urls.add(link)

    if len(unique_urls) % 100 == 0:
        logger.info(f"CRAWLED {len(unique_urls)} unique pages so far.")

    return valid_links


# ---------------- XML SITEMAP PARSER ---------------- #
def get_sitemap_urls(resp) -> list:
    soup = BeautifulSoup(resp.text, 'xml')
    sitemap_urls = []

    for item in soup.find_all("loc"):
        url = item.text.strip()
        sitemap_urls.append(url)

    return sitemap_urls


# ---------------- SIMHASH FEATURE EXTRACTOR ---------------- #
def get_features(text, width=3):
    text = text.lower()
    text = re.sub(r'[^\w\s]+', '', text)
    words = text.split()

    if len(words) == 0:
        return []

    return [' '.join(words[i:i + width]) for i in range(max(len(words) - width + 1, 1))]


# ---------------- LINK EXTRACTION ---------------- #
def extract_next_links(url, resp):
    links = []
    global word_frequencies

    # Handle bad responses
    if resp.status != 200 or resp.raw_response is None:
        if resp.status in {403, 404, 500, 502, 503, 504, 601}:
            logger.debug(f"[SKIP STATUS] {resp.status} at {url}")
            return links

        logger.error(f"BAD RESPONSE {resp.status}: {url} | Error: {getattr(resp, 'error', None)}")
        return links

    # Check content type
    content_type = resp.raw_response.headers.get("Content-Type", "")
    if "xml" in content_type.lower():
        try:
            sitemap_links = get_sitemap_urls(resp)
            return sitemap_links
        except Exception as e:
            print(f"[EXTRACTION ERROR] Problem while extracting links from sitemap url {url}: {e}")
            return []

    if "text/html" not in content_type:
        logger.debug(f"SKIPPED NON-HTML: {url} | Content-Type: {content_type}")
        return links

    # Parse HTML content
    try:
        html = resp.raw_response.content
        soup = BeautifulSoup(html, "lxml")

        # Remove non-textual elements before counting words
        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        tokens = tokenizer.tokenize(text)
        useful_tokens = [t for t in tokens if t not in STOPWORDS]

        # Update global word frequency
        for t in useful_tokens:
            word_frequencies[t] += 1

        # Track longest page
        global longest_page
        page_word_count = len(useful_tokens)
        if page_word_count > longest_page["words"]:
            longest_page = {"url": url, "words": page_word_count}

        # Simhash duplicate detection
        global unique_pages
        curr_hash = Simhash(get_features(text))
        curr_value = curr_hash.value

        for prev_value, prev_url in unique_pages:
            prev_hash = Simhash(prev_value)
            if curr_hash.distance(prev_hash) < 3:
                logger.info(f"[DUPLICATE] Skipping near-duplicate page: {url} similar to {prev_url}")
                return []

        unique_pages.add((curr_value, url))

    except Exception as e:
        print(f"Error parsing HTML at {url}: {e}")
        return links

    # Extract links
    try:
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href:
                continue

            abs_url = urljoin(url, href)
            abs_url, _ = urldefrag(abs_url)
            links.append(abs_url)

        # Trap detection
        domain_url_counts = defaultdict(int)
        for link in links:
            domain = urlparse(link).netloc
            domain_url_counts[domain] += 1

        for domain, count in domain_url_counts.items():
            if count > 100:
                logger.warning(f"[POSSIBLE TRAP] {domain} produced {count} links on one page ({url})")
                return []

    except Exception as e:
        print(f"[EXTRACTION ERROR] Problem while extracting links from {url}: {e}")

    return links


# ---------------- VALIDATION FUNCTION ---------------- #
def is_valid(url):
    try:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        domain = parsed.netloc.lower()
        allowed_domains = {
            "ics.uci.edu",
            "cs.uci.edu",
            "informatics.uci.edu",
            "stat.uci.edu"
        }

        if not any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains):
            return False

        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()

        if "/events/tag/talks/" in path_lower:
            return False

        if re.search(r"/event/[-\w]+-\d+$", url):
            return False

        if "ical=" in url or "outlook-ical=" in url:
            return False

        if "tribe-bar-date=" in query_lower or "eventdisplay=past" in query_lower:
            return False

        if re.search(r"\d{4}-\d{2}(-\d{2})?", url):
            return False

        # Gitlab repositories
        if "gitlab" in url:
            if "merge_request" in path_lower:
                return False
            if "?view=parallel" in url:
                return False
            if "commit" in url:
                return False
            if "/tree/" in url:
                return False
            if "forks" in path_lower:
                return False
            if "branches" in path_lower and "all" not in path_lower:
                return False

        # DokuWiki modes
        if "?do=edit" in url or "?do=login" in url:
            return False
        if "?do=backlink" in url or "?do=revisions" in url or "?do=diff" in url:
            return False
        if "%3" in url:
            return False

        if "doku.php" in url:
            if any(param in url for param in ["?do=", "&do=", "?idx=", "&idx=", "?id=", "&id="]):
                logger.debug(f"[TRAP] DokuWiki internal action blocked: {url}")
                return False

        if re.search(r"/wiki/public/wiki/.+-\d{4}", url):
            return False

        # Dead or restricted hosts
        dead_hosts = {
            "jujube.ics.uci.edu",
            "flamingo.ics.uci.edu",
            "asterixdb.ics.uci.edu",
            "dblp.ics.uci.edu",
        }

        if any(dead in parsed.netloc.lower() for dead in dead_hosts):
            logger.debug(f"[TRAP] Dead or restricted host blocked: {url}")
            return False

        # Old personal project pages (~username)
        if re.search(r"/~[a-zA-Z0-9_-]+", url):
            logger.debug(f"[TRAP] Old personal site blocked: {url}")
            return False

        ignore_in_url = ["robots.txt", "&", "%3A", "?do=edit"]
        for item in ignore_in_url:
            if url.count(item) > 1:
                return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            parsed.path.lower()
        )

    except TypeError:
        print("TypeError for ", parsed)
        raise