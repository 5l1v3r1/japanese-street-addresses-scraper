import json
import logging
from time import sleep

import requests
from bs4 import BeautifulSoup
from expressvpn import wrapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)15s - %(levelname)s - %(message)s')

YELLOW_PAGE_URL = 'https://itp.ne.jp'
BIG_ADDRESS_FILENAME = '/tmp/addresses.txt'

W_FP = open(BIG_ADDRESS_FILENAME, 'wb')


class PaginationEndException(Exception):
    pass


def forge_url(prefix, iteration):
    # http://itp.ne.jp/46201/genre_dir/
    # https://itp.ne.jp/aomori/02201/genre_dir/pg/150/?num=20
    return prefix + 'pg/{}/?num=20'.format(iteration)


def process_one_url(url):
    logging.info('-> {}'.format(url))
    response = requests.get(url)
    sleep(0.1)
    assert response.status_code == 200
    content = response.content
    soup = BeautifulSoup(content, 'html.parser')
    if len(soup.find_all('p', {'class': 'townkunMessageContent'})) > 0:
        raise PaginationEndException()
    results = soup.find_all('div', {'class': 'normalResultsBox'})
    for result in results:
        if '〒' in str(result):
            cons = result.contents[1].contents
            for con in cons:
                if '〒' in str(con):
                    for c in con:
                        if '〒' in str(c):
                            address = str(c.contents[1])
                            logging.info(address)
                            address += '\n'
                            W_FP.write(address.encode('utf8'))
                            break


def main():
    change_ip()
    with open('regions.json', 'rb') as r:
        regions = json.load(r)
    for region, sub_regions in regions.items():
        logging.info('REGION: {}'.format(region))
        for sub_region, prefix_urls in sub_regions['sub_region'].items():
            logging.info('SUB_REGION: {}'.format(sub_region))
            logging.info(prefix_urls)
            if isinstance(prefix_urls, str):
                prefix_urls = [prefix_urls]
            for prefix_url in prefix_urls:
                try:
                    for iteration in range(1000000):
                        request_url = forge_url(prefix_url, iteration)
                        try:
                            process_one_url(request_url)
                        except requests.exceptions.ConnectionError:
                            logging.info('Received a ConnectionError. Will wait 10 seconds, then resume.')
                            change_ip()
                            sleep(10)
                except PaginationEndException:
                    logging.info('PaginationEndException!')
                except Exception as e:
                    W_FP.close()
                    raise e
            logging.info('SUB_REGION DONE: {}'.format(sub_region))
        logging.info('REGION DONE: {}'.format(region))


def change_ip():
    max_attempts = 10
    attempts = 0
    while True:
        attempts += 1
        try:
            logging.info('GETTING NEW IP')
            wrapper.random_connect()
            logging.info('SUCCESS')
            return
        except Exception as e:
            if attempts > max_attempts:
                logging.info('Max attempts reached for VPN. Check its configuration.')
                logging.info('Browse https://github.com/philipperemy/expressvpn-python.')
                logging.info('Program will exit.')
                exit(1)
            logging.info(e)
            logging.info('Skipping exception.')


if __name__ == '__main__':
    main()