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
        r.html.render(timeout=5, sleep=1.1)
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
        for row in [x for x in rows if x.text != ""]:
            if str(row).lower().__contains__("title"):
                i.title = row.text
            if str(row).lower().__contains__("desc"):
                i.description = row.text
            if i.pubDate == "":
                try:
                    i.pubDate = parse(row.text)  # .strftime("%a, %d %b %Y %H:%M:%S %z")
                    i.pubDate = i.pubDate.replace(tzinfo=pytz.UTC)
                except Exception as ex:
                    err = ex
                    pass
        if i.pubDate == "":
            i.pubDate = datetime.now(pytz.UTC)
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


print(get_feed("https://www.ncsc.gov.uk/section/keep-up-to-date/ncsc-news", "search-results"))
