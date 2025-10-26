from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler

# THESE LINES ARE NEEDED IF NOT RUNNING ON LINUX
# import multiprocessing
# multiprocessing.set_start_method("fork")

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

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
