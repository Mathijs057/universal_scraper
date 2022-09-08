import re
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from feedgen.feed import FeedGenerator
from requests_html import HTMLSession


class RssItem:
    def __init__(self, title: str = "", link: str = "", description: str = "", pubdate: datetime = None):
        self.title = title
        self.link = link
        self.description = description
        self.pubDate = pubdate

    def is_valid(self) -> bool:
        """
        Check if the item is valid
        :return: True if valid, False otherwise
        """
        return self.title and self.link and self.description and self.pubDate


def get_soup(url: str) -> BeautifulSoup:
    """
    Get HTML from URL.
    :param url: URL to get HTML from.
    :return: HTML from URL as string.
    """
    retn = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"})
    retn = BeautifulSoup(retn.text, "html.parser")
    if str(retn).lower().__contains__("you need to enable javascript to run this app"):
        session = HTMLSession()
        r = session.get(url)
        r.html.render(timeout=5, sleep=1.1)
        retn = BeautifulSoup(r.html.html, "html.parser")
    return retn


def get_list(url: str, container_class_or_id: str, index=0) -> list:
    """
    Get list of links from HTML.
    :param url: URL to get list from.
    :param container_class_or_id: Class or ID of the html element that holds the items to extract. You can also specify an attribute with its value, like: attribute=value without using any quotes.
    :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
    :return: List of extracted items.
    """
    soup = get_soup(url)
    retn = []
    if container_class_or_id.__contains__("="):
        elements = soup.find_all(attrs={container_class_or_id.split("=")[0]: container_class_or_id.split("=")[1]})
    else:
        elements = soup.find_all(class_=container_class_or_id)
    if len(elements) == 0:
        elements = soup.find_all(id=container_class_or_id)
    for element in elements[index].contents:
        rows = BeautifulSoup(str(element), "html.parser").find_all()
        i = RssItem()
        lnk = ""
        try:
            lnk = BeautifulSoup(str(element), "html.parser").find("a").get("href")
            if not i.link.startswith(url):
                i.link = "https://" + url.replace("https://", "").split("/")[0] + i.link
        except AttributeError:
            pass
        if lnk == "":
            i.link = str(url)
        for row in [x for x in rows if x.text != ""]:
            if str(row).lower().__contains__("title"):
                i.title = clean_string(row.text)
            if str(row).lower().__contains__("desc"):
                i.description = clean_string(row.text)
            if i.pubDate == "":
                try:
                    i.pubDate = parse(row.text)
                    i.pubDate = i.pubDate.replace(tzinfo=pytz.UTC)
                except Exception as ex:
                    err = ex
                    pass
        if i.description == "":
            i.description = clean_string(element.text)
        if i.pubDate is None:
            i.pubDate = datetime.now(pytz.UTC)
        if i.is_valid():
            retn.append(i)
    return retn


def clean_string(txt: str) -> str:
    """
    Cleans a string by removing all non-alphanumeric characters.
    :param txt: String to clean.
    :return: Cleaned string.
    """
    txt = re.sub(r"[^a-zA-Z0-9 ,.:;]", "", txt)
    while txt.__contains__("\n\n"):
        txt = txt.replace("\n\n", "\n")
    while txt.__contains__("\r\r"):
        txt = txt.replace("\r\r", "\r")
    while txt.__contains__("\t\t"):
        txt = txt.replace("\t\t", "\t")
    while txt.__contains__("  "):
        txt = txt.replace("  ", " ")
    return txt.strip()


def get_feed(url: str, container_class_or_id: str, index=0) -> str:
    """
    Returns RSS feed from webpage.
    :param url: URL of the webpage with the content.
    :param container_class_or_id: Class or ID of the html element that holds the items to extract.
    :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
    :return: RSS feed.
    """
    fg = FeedGenerator()
    fg.title('Universal RSS feed')
    fg.link(href=url, rel='alternate')
    fg.author({'name': 'NCSC SOB IFC', 'email': 'sob@ncsc.nl'})
    fg.subtitle('Generated from ' + url)
    fg.language('en')
    items = get_list(url, container_class_or_id, index)
    for item in items:
        fe = fg.add_entry()
        fe.title(item.title)
        fe.link(href=item.link)
        fe.description(item.description)
        fe.pubDate(item.pubDate)
    return fg.rss_str(pretty=True)


# print(get_feed('https://www.ncsc.gov.uk/section/keep-up-to-date/ncsc-news', 'search-results'))
# print(get_feed('https://www.zdnet.com/blog/security/', 'data-component=lazyloadImages'))
# print(get_feed('https://informationsecuritybuzz.com/', 'exad-row-wrapper'))
# print(get_feed('https://grahamcluley.com/', 'grid-row'))
print(get_feed('https://threatpost.com/', 'latest_news_container'))
