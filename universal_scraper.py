import os
import re
from datetime import datetime

import feedparser
import pytz
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse
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


class UniversalScraper:
    """
    A class that scrapes a webpage in an universal way and generates an RSS feed or a solution for annotation of the output (so it can be used to train a Neural Network Model).
    """

    def __int__(self):
        pass

    def get_soup(self, url: str) -> BeautifulSoup:
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

    def get_list(self, url: str, container_attribute: str, index=0) -> list:
        """
        Get list of links from HTML.
        :param url: URL to get list from.
        :param container_attribute: the attribute with its value of the html element that holds the items to extract. You can specify an attribute with its value, like: attribute=value without using any quotes.
        :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
        :return: List of extracted items.
        """
        soup = self.get_soup(url)
        retn = []
        try:
            elements = soup.find_all(
                attrs={container_attribute.split("=")[0].strip(): container_attribute.split("=")[1].strip()})
        except IndexError:
            if str(soup).lower().startswith("<?xml"):
                # The page is an RSS feed.
                elements = feedparser.parse(url).entries
                for element in elements:
                    retn.append(RssItem(title=self.clean_string(BeautifulSoup(element.title).text), link=element.link,
                                        description=self.clean_string(BeautifulSoup(element.description).text),
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
                    i.title = self.clean_string(row.text)
                if str(row).lower().__contains__("desc"):
                    i.description = self.clean_string(row.text)
                if i.pubDate == "":
                    try:
                        i.pubDate = parse(row.text)
                        i.pubDate = i.pubDate.replace(tzinfo=pytz.UTC)
                    except AttributeError:
                        pass
            if i.description == "":
                # If no description is found, use the entire text of the element.
                i.description = self.clean_string(element.text)
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

    def clean_string(self, txt: str) -> str:
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

    def get_feed(self, url: str, container_attribute: str, index=0) -> Response:
        """
        Returns RSS feed from webpage.
        :param url: URL of the webpage with the content.
        :param container_attribute: the attribute with its value of the html element that holds the items to extract. You can specify an attribute with its value, like: attribute=value without using any quotes.
        :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
        :return: RSS feed.
        """

        fg = FeedGenerator()
        fg.title('Universal RSS feed')
        fg.link(href=url, rel='alternate')
        fg.author({'name': 'NCSC SOB IFC', 'email': 'sob@ncsc.nl'})
        fg.subtitle('Generated from ' + url)
        fg.language('en')
        items = self.get_list(url, container_attribute, index)
        for item in items:
            fe = fg.add_entry()
            fe.title(item.title)
            fe.link(href=item.link)
            fe.description(item.description)
            fe.pubDate(item.pubDate)
        return fg.rss_str(pretty=True)

    def to_single_line(self, txt: str) -> str:
        """
        Converts a string to a single line.
        :param txt: String to convert.
        :return: Single line string.
        """
        return txt.replace("\n", "").replace("\r", "").replace("\t", "").replace("  ", " ").strip()

    def get_jsonl(self, url: str, container_attribute: str, index=0) -> str:
        """
        Returns JSONL output from webpage, which can be read by the Prodigy tool (https://prodi.gy/docs).
        :param url: URL of the webpage with the content.
        :param container_attribute: the attribute with its value of the html element that holds the items to extract. You can specify an attribute with its value, like: attribute=value without using any quotes.
        :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
        :return: RSS feed.
        """
        items = self.get_list(url, container_attribute, index)
        retn = ""
        for item in items:
            retn += self.to_single_line(item.description) + "\n"
        return retn

    def start_prodigy(self, url: str, container_attribute: str, index=0):
        """
        Starts Prodigy for annotation.
        :param url: URL of the webpage with the content.
        :param container_attribute: the attribute with its value of the html element that holds the items to extract. You can specify an attribute with its value, like: attribute=value without using any quotes (only surrounding quotes as a whole).
        :param index: Index of the container with the defined class or id to return (needed when there are more elements in the page with the same class or id).
        :return: RSS feed.
        """
        location = r"c:\temp"
        txt = self.get_jsonl(url=url, container_attribute='id=latest_news_container', index=index)
        open(rf"{location}\data.txt", "w").write(txt)
        os.system(
            r"python -m prodigy textcat.manual newsfeeds c:\temp\data.txt --exclusive --label 'Very high',high,medium,low")
