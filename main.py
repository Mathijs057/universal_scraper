import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from dateutil.parser import parse

class RssItem:
    def __init__(self, title: str = "", link: str = "", description: str = "", pubDate: str = ""):
        self.title = title
        self.link = link
        self.description = description
        self.pubDate = pubDate

def get_soup(url: str) -> BeautifulSoup:
    """
    Get HTML from URL.
    :param url: URL to get HTML from.
    :return: HTML from URL as string.
    """
    retn = requests.get(url)
    retn = BeautifulSoup(retn.text, "html.parser")
    if str(retn).lower().__contains__("you need to enable javascript to run this app"):
        session = HTMLSession()
        r = session.get(url)
        r.html.render(timeout=3, sleep=1.1)
        retn = BeautifulSoup(r.html.html, "html.parser")
    return retn

def get_list(url: str, container_class_or_id: str, index=0) -> list:
    """
    Get list of links from HTML.
    :param url: URL to get list from.
    :param container_class_or_id: Class or ID of the html element that holds the items to extract.
    :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
    :return: List of extracted items.
    """
    soup = get_soup(url)
    retn = []
    elements = soup.find_all(class_=container_class_or_id)
    if len(elements) == 0:
        elements = soup.find_all(id=container_class_or_id)
    for element in elements[index].contents:
        rows = BeautifulSoup(str(element), "html.parser").find_all()
        i = RssItem()
        i.link = BeautifulSoup(str(element), "html.parser").find("a").get("href")
        if not i.link.startswith(url):
            i.link = "https://" + url.replace("https://", "").split("/")[0] + i.link
        for row in [x for x in rows if x.text!=""]:
            if str(row).lower().__contains__("title"):
                i.title = row.text
            if str(row).lower().__contains__("desc"):
                i.description = row.text
            if i.pubDate == "":
                try:
                    i.pubDate = parse(row.text).strftime("%a, %d %b %Y %H:%M:%S %z")
                except Exception as ex:
                    err = ex
                    pass
        if i.pubDate == "":
            i.pubDate = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        retn.append(i)
    return retn

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.
    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False

print(get_list("https://www.ncsc.gov.uk/section/keep-up-to-date/ncsc-news", "search-results"))
