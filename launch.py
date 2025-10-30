from configparser import ConfigParser
from argparse import ArgumentParser
from collections import defaultdict
from urllib.parse import urlparse, urljoin, urldefrag

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler

from scraper import unique_urls

# THESE LINES ARE NEEDED IF RUNNING ON MAC
import multiprocessing
multiprocessing.set_start_method("fork")

# THESE LINES ARE NEEDED IF RUNNING ON WINDOWS
# import multiprocessing
# multiprocessing.set_start_method("spawn", force=True)

def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)

    try:
        crawler.start()
    finally:
        from scraper import word_frequencies
        import json
        with open("word_frequencies_final.json", "w") as f:
            json.dump(word_frequencies, f)
        print("[SAVED] Final word frequencies saved.")
        # Save all unique URLs (ignoring fragments)
        with open("unique_urls.txt", "w") as f:
            f.write("\n".join(sorted(unique_urls)))
        print(f"[SUMMARY] Total unique pages found (by URL): {len(unique_urls)}")

        subdomain_counts = defaultdict(int)
        for url in unique_urls:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.endswith(".uci.edu") or netloc == "uci.edu":
                subdomain_counts[netloc] += 1

        # Save to file sorted alphabetically
        with open("subdomains.txt", "w") as f:
            for subdomain in sorted(subdomain_counts):
                f.write(f"{subdomain}, {subdomain_counts[subdomain]}\n")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)