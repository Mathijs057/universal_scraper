import pyodbc
from universal_scraper import UniversalScraper

scraper = UniversalScraper()
conn = pyodbc.connect(
            'Driver={SQL Server Native Client 11.0};'
            'Server=server;'
            'Database=tagger;'
            'Trusted_Connection=yes;'
            'MARS_Connection=Yes;'
        )
cursor = conn.cursor()
rows = cursor.execute("SELECT * FROM tbl_sites WHERE container=''").fetchall()
for row in rows:
    url = row[1]
    container_attribute = row[2]
    feed = scraper.get_feed(url, container_attribute)
    print(feed)

