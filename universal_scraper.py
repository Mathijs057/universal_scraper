import re
from datetime import datetime
from urllib.parse import unquote

import feedparser
import pytz
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
from fastapi import FastAPI, Query
from feedgen.feed import FeedGenerator
from requests import Response
from requests_html import HTMLSession


class RssItem:
    """
    Class to represent an RSS item.
    """

    def __init__(self, title: str = "", link: str = "", description: str = "", pubdate: datetime = None):
        """
        Initialize the RSS item.
        :param title: Optional. The title of the item.
        :param link: Optional. The link of the item.
        :param description: Optional. The description of the item.
        :param pubdate: Optional. The publication date of the item.
        """
        self.title = title
        self.link = link
        self.description = description
        self.pubDate = pubdate

    def is_valid(self) -> bool:
        """
        Check if the item is valid.
        :return: True if valid, False otherwise.
        """
        return self.title and self.link and self.description and self.pubDate


app = FastAPI()

"""
Thes functions scrape a webpage in an universal way and generates an RSS feed or a solution for annotation of the output (so it can be used to train a Neural Network Model).
"""


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
        # The site is build by javascripts, so the content is not available in the HTML and needs to be rendered first.
        session = HTMLSession()
        r = session.get(url)
        r.html.render(timeout=5, sleep=1.1)
        retn = BeautifulSoup(r.html.html, "html.parser")
    return retn


def get_list(url: str, container_attribute: str, index=0) -> list:
    """
    Get list of links from HTML.
    :param url: URL to get list from.
    :param container_attribute: the attribute with its value of the html element that holds the items to extract. You can specify an attribute with its value, like: attribute=value without using any quotes.
    :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
    :return: List of extracted items.
    """
    soup = get_soup(url)
    retn = []
    try:
        elements = soup.find_all(
            attrs={container_attribute.split("=")[0].strip(): container_attribute.split("=")[1].strip()})
    except IndexError:
        if str(soup).lower().startswith("<?xml"):
            # The page is an RSS feed.
            elements = feedparser.parse(url).entries
            for element in elements:
                retn.append(RssItem(title=clean_string(BeautifulSoup(element.title).text), link=element.link,
                                    description=clean_string(BeautifulSoup(element.description).text),
                                    pubdate=element.published))
            return retn
    for element in [x for x in elements[index].contents if str(x) != "\n"]:
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
                except AttributeError:
                    pass
        if i.description == "":
            # If no description is found, use the entire text of the element.
            i.description = clean_string(element.text)
        if i.pubDate is None:
            # No date is found. Search for any date in the text
            try:
                i.pubDate = parse(re.search(r'\d{2}-\d{2}-\d{4}', element.text).group())
                i.pubDate = i.pubDate.replace(tzinfo=pytz.UTC)
            except AttributeError:
                pass
            if i.pubDate is None:
                # Still no date is found. Use current date and time.
                i.pubDate = datetime.now(pytz.UTC)
        if i.title == "":
            # If no title is found, use the description as title.
            i.title = i.description
        if i.is_valid():
            retn.append(i)
    return retn


def clean_string(txt: str) -> str:
    """
    Cleans a string by removing all non-alphanumeric characters.
    :param txt: String to clean.
    :return: Cleaned string.
    """
    txt = re.sub(r"[^a-zA-Z0-9 ,.:;]", "", txt).replace(".", ". ").replace(":", ": ").replace(";", "; ").replace(",",
                                                                                                                 ", ")
    while txt.__contains__("\n\n"):
        txt = txt.replace("\n\n", "\n")
    while txt.__contains__("\r\r"):
        txt = txt.replace("\r\r", "\r")
    while txt.__contains__("\t\t"):
        txt = txt.replace("\t\t", "\t")
    while txt.__contains__("  "):
        txt = txt.replace("  ", " ")
    return txt.strip()


@app.get('/get_feed')
def get_feed(url: str =  Query(None, description="The url-encoded URL of the website that contains the information to extract."), container_attribute: str = Query(None, description="The html attribute of the HTML container that holds the list of information te be extract, like 'class=search_results' or 'id=newslist'. Don't use any quotes."), index=Query(0, description="The index of the container, in case the site contains more than one HTML-element with the same container_attributes.")) -> Response:
    """
    Returns RSS feed from webpage.
    """
    url = unquote(url)
    fg = FeedGenerator()
    fg.title('Universal RSS feed')
    fg.link(href=url, rel='alternate')
    fg.author({'name': 'Universal Scraper'})
    fg.subtitle('Generated from ' + url)
    fg.language('en')
    items = get_list(url, container_attribute, index)
    for item in items:
        fe = fg.add_entry()
        fe.title(item.title)
        fe.link(href=item.link)
        fe.description(item.description)
        fe.pubDate(item.pubDate)
    return fg.rss_str(pretty=True)

# print(get_feed("https%3A%2F%2Fwww.ncsc.gov.uk%2Fsection%2Fkeep-up-to-date%2Fncsc-news%3Fq%3D%26defaultTypes%3Dnews%2Cinformation%26sort%3Ddate%252Bdesc", "class=search-results"))
