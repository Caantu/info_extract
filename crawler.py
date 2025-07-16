import requests
from bs4 import BeautifulSoup
import csv
import os
import time
from datetime import datetime
import re


class ArticleCrawler:
    def __init__(self, output_dir='crawled_data'):
        self.output_dir = output_dir
        self.articles_dir = os.path.join(output_dir, 'articles')
        self.metadata_file = os.path.join(output_dir, 'metadata.csv')

        # Create directories
        os.makedirs(self.articles_dir, exist_ok=True)

        # Initialize metadata CSV
        self.init_metadata_csv()

    def init_metadata_csv(self):
        """Initialize the metadata CSV file with headers"""
        with open(self.metadata_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['doc_id', 'title', 'url', 'date', 'filename'])

    def clean_text(self, text):
        """Clean the extracted text"""
        # Remove extra whitespaces and newlines
        text = ' '.join(text.split())
        # Remove non-ASCII characters if needed
        text = text.encode('ascii', 'ignore').decode('ascii')
        return text

    def crawl_bbc_news(self, num_articles=150):
        """Crawl articles from BBC News (Technology section)"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        doc_id = 1
        article_links = set()

        # Try multiple BBC sections
        sections = [
            "https://www.bbc.com/news/technology",
            "https://www.bbc.com/news/science-environment",
            "https://www.bbc.com/news/business",
            "https://www.bbc.com/news/health"
        ]

        for section_url in sections:
            try:
                print(f"Crawling section: {section_url}")
                response = requests.get(section_url, headers=headers)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find article links - updated selectors
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # More flexible pattern matching
                    if ('/news/articles/' in href or
                            '/news/technology-' in href or
                            '/news/science-' in href or
                            '/news/business-' in href or
                            '/news/health-' in href):
                        if href.startswith('/'):
                            href = 'https://www.bbc.com' + href
                        article_links.add(href)

                # Also try to find links in specific containers
                for container in soup.find_all(['div', 'section'], class_=['gel-layout', 'gs-c-promo', 'media']):
                    for link in container.find_all('a', href=True):
                        href = link['href']
                        if '/news/' in href and 'live' not in href:
                            if href.startswith('/'):
                                href = 'https://www.bbc.com' + href
                            article_links.add(href)

            except Exception as e:
                print(f"Error accessing {section_url}: {e}")

        article_links = list(article_links)
        print(f"Found {len(article_links)} unique BBC article links")

        # Crawl articles
        for url in article_links:
            if doc_id > num_articles:
                break

            try:
                print(f"Crawling article {doc_id}: {url}")
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract title - try multiple selectors
                title = None
                for selector in ['h1', 'h1.story-body__h1', 'h1#main-heading']:
                    title_tag = soup.find(selector)
                    if title_tag:
                        title = title_tag.text.strip()
                        break

                if not title:
                    continue

                # Extract content - try multiple approaches
                content = ""

                # Method 1: Look for article tag
                article = soup.find('article')
                if article:
                    paragraphs = article.find_all('p')
                    content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])

                # Method 2: Look for specific divs
                if not content:
                    for div_class in ['story-body__inner', 'story-body', 'article__body']:
                        body_div = soup.find('div', class_=div_class)
                        if body_div:
                            paragraphs = body_div.find_all('p')
                            content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])
                            break

                # Method 3: Find all p tags with substantial text
                if not content:
                    all_paragraphs = soup.find_all('p')
                    paragraphs_text = []
                    for p in all_paragraphs:
                        text = p.text.strip()
                        if len(text) > 50:  # Only substantial paragraphs
                            paragraphs_text.append(text)
                    content = ' '.join(paragraphs_text)

                content = self.clean_text(content)

                if len(content) > 200:  # Only save articles with substantial content
                    # Extract date
                    date = None
                    date_tag = soup.find('time')
                    if date_tag:
                        date = date_tag.get('datetime', '')
                    if not date:
                        date = datetime.now().strftime('%Y-%m-%d')

                    # Save article
                    filename = f"article_{doc_id}.txt"
                    filepath = os.path.join(self.articles_dir, filename)

                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)

                    # Save metadata
                    with open(self.metadata_file, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([doc_id, title, url, date, filename])

                    doc_id += 1
                    time.sleep(0.5)  # Be polite

            except Exception as e:
                print(f"Error crawling {url}: {e}")
                continue

        # Return the next doc_id for other sources
        return doc_id

    def crawl_guardian_news(self, num_articles=50, starting_id=1):
        """Crawl articles from The Guardian (Technology section)"""
        base_url = "https://www.theguardian.com/technology"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        doc_id = starting_id

        try:
            response = requests.get(base_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'theguardian.com' in href and '/technology/' in href:
                    if href not in article_links and href.count('/') > 4:
                        article_links.append(href)

            print(f"Found {len(article_links)} Guardian article links")

            # Crawl each article
            for url in article_links[:num_articles]:
                try:
                    print(f"Crawling article {doc_id}: {url}")
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extract title
                    title_tag = soup.find('h1')
                    title = title_tag.text.strip() if title_tag else "No Title"

                    # Extract article content
                    article_body = soup.find('div', {'class': 'article-body-commercial-selector'})
                    if not article_body:
                        article_body = soup.find('div', {'id': 'maincontent'})

                    if article_body:
                        paragraphs = article_body.find_all('p')
                        content = ' '.join([p.text.strip() for p in paragraphs])
                        content = self.clean_text(content)

                        if len(content) > 100:
                            # Extract date
                            date_tag = soup.find('time')
                            date = date_tag.get('datetime', '') if date_tag else datetime.now().strftime('%Y-%m-%d')

                            # Save article
                            filename = f"article_{doc_id}.txt"
                            filepath = os.path.join(self.articles_dir, filename)

                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(content)

                            # Save metadata
                            with open(self.metadata_file, 'a', newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                writer.writerow([doc_id, title, url, date, filename])

                            doc_id += 1
                            time.sleep(0.5)

                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    continue

                if doc_id >= starting_id + num_articles:
                    break

        except Exception as e:
            print(f"Error accessing The Guardian: {e}")

        return doc_id

    def crawl_reuters_tech(self, num_articles=50, starting_id=1):
        """Crawl articles from Reuters Technology section"""
        base_url = "https://www.reuters.com/technology/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        doc_id = starting_id
        article_links = set()

        try:
            print(f"Crawling Reuters Technology...")
            response = requests.get(base_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/technology/' in href and href.startswith('/'):
                    full_url = 'https://www.reuters.com' + href
                    article_links.add(full_url)
                elif 'reuters.com' in href and '/technology/' in href:
                    article_links.add(href)

            article_links = list(article_links)
            print(f"Found {len(article_links)} Reuters article links")

            for url in article_links[:num_articles]:
                try:
                    print(f"Crawling article {doc_id}: {url}")
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extract title
                    title_tag = soup.find('h1')
                    title = title_tag.text.strip() if title_tag else "No Title"

                    # Extract content
                    content = ""
                    # Try to find article body
                    article_body = soup.find('div', class_=['article-body', 'paywall-article'])
                    if article_body:
                        paragraphs = article_body.find_all('p')
                        content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])

                    if not content:
                        # Alternative method
                        all_paragraphs = soup.find_all('p', class_='text__text__1FZLe')
                        content = ' '.join([p.text.strip() for p in all_paragraphs if len(p.text.strip()) > 30])

                    content = self.clean_text(content)

                    if len(content) > 200:
                        # Extract date
                        date_tag = soup.find('time')
                        date = date_tag.get('datetime', '') if date_tag else datetime.now().strftime('%Y-%m-%d')

                        # Save article
                        filename = f"article_{doc_id}.txt"
                        filepath = os.path.join(self.articles_dir, filename)

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)

                        # Save metadata
                        with open(self.metadata_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([doc_id, title, url, date, filename])

                        doc_id += 1
                        time.sleep(0.5)

                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error accessing Reuters: {e}")

        return doc_id

    def crawl_techcrunch(self, num_articles=50, starting_id=1):
        """Crawl articles from TechCrunch"""
        base_url = "https://techcrunch.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        doc_id = starting_id

        try:
            print(f"Crawling TechCrunch...")
            response = requests.get(base_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            article_links = []
            # Find article links
            for article in soup.find_all('article'):
                link_tag = article.find('a', href=True)
                if link_tag:
                    href = link_tag['href']
                    if 'techcrunch.com/20' in href:  # Articles have year in URL
                        article_links.append(href)

            # Also check for more links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'techcrunch.com/20' in href and href not in article_links:
                    article_links.append(href)

            print(f"Found {len(article_links)} TechCrunch article links")

            for url in article_links[:num_articles]:
                try:
                    print(f"Crawling article {doc_id}: {url}")
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extract title
                    title_tag = soup.find('h1')
                    title = title_tag.text.strip() if title_tag else "No Title"

                    # Extract content
                    content = ""
                    article_body = soup.find('div', class_='article-content')
                    if not article_body:
                        article_body = soup.find('div', class_='content')

                    if article_body:
                        paragraphs = article_body.find_all('p')
                        content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])

                    content = self.clean_text(content)

                    if len(content) > 200:
                        # Extract date
                        date_tag = soup.find('time')
                        date = date_tag.get('datetime', '') if date_tag else datetime.now().strftime('%Y-%m-%d')

                        # Save article
                        filename = f"article_{doc_id}.txt"
                        filepath = os.path.join(self.articles_dir, filename)

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)

                        # Save metadata
                        with open(self.metadata_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([doc_id, title, url, date, filename])

                        doc_id += 1
                        time.sleep(0.5)

                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error accessing TechCrunch: {e}")

        return doc_id

    def crawl_arxiv_cs(self, num_articles=50, starting_id=1):
        """Crawl computer science papers from arXiv"""
        import urllib.parse

        base_url = "http://export.arxiv.org/api/query?"
        doc_id = starting_id

        # Search for recent CS papers
        search_query = 'cat:cs.AI OR cat:cs.LG OR cat:cs.CL'  # AI, Machine Learning, Computation & Language
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': num_articles,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        try:
            print(f"Crawling arXiv Computer Science papers...")
            url = base_url + urllib.parse.urlencode(params)
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'xml')

            entries = soup.find_all('entry')
            print(f"Found {len(entries)} arXiv papers")

            for entry in entries:
                try:
                    # Extract title
                    title = entry.find('title').text.strip()
                    title = ' '.join(title.split())  # Clean whitespace

                    # Extract abstract as content
                    abstract = entry.find('summary').text.strip()
                    abstract = ' '.join(abstract.split())

                    # Get URL
                    url = entry.find('id').text.strip()

                    # Get date
                    published = entry.find('published').text.strip()
                    date = published.split('T')[0]  # Get just the date part

                    # Create content with title and abstract
                    content = f"Title: {title}. Abstract: {abstract}"
                    content = self.clean_text(content)

                    if len(content) > 100:
                        # Save article
                        filename = f"article_{doc_id}.txt"
                        filepath = os.path.join(self.articles_dir, filename)

                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)

                        # Save metadata
                        with open(self.metadata_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([doc_id, title, url, date, filename])

                        doc_id += 1

                except Exception as e:
                    print(f"Error processing arXiv entry: {e}")
                    continue

        except Exception as e:
            print(f"Error accessing arXiv: {e}")

        return doc_id


def main():
    print("Starting web crawler...")
    crawler = ArticleCrawler()

    print("Crawling multiple news sources...")

    # Start with BBC News (multiple sections)
    doc_id = crawler.crawl_bbc_news(num_articles=50)
    print(f"BBC crawling completed. Total articles so far: {doc_id - 1}")

    # Continue with Reuters
    if doc_id <= 150:
        doc_id = crawler.crawl_reuters_tech(num_articles=50, starting_id=doc_id)
        print(f"Reuters crawling completed. Total articles so far: {doc_id - 1}")

    # Continue with TechCrunch
    if doc_id <= 150:
        doc_id = crawler.crawl_techcrunch(num_articles=50, starting_id=doc_id)
        print(f"TechCrunch crawling completed. Total articles so far: {doc_id - 1}")

    # Finally, get some arXiv papers
    if doc_id <= 150:
        doc_id = crawler.crawl_arxiv_cs(num_articles=50, starting_id=doc_id)
        print(f"arXiv crawling completed. Total articles so far: {doc_id - 1}")

    print("\nCrawling completed!")
    print(f"Articles saved in: {crawler.articles_dir}")
    print(f"Metadata saved in: {crawler.metadata_file}")

    # Count articles
    article_count = len([f for f in os.listdir(crawler.articles_dir) if f.endswith('.txt')])
    print(f"Total articles crawled: {article_count}")

    if article_count < 150:
        print(f"\nNote: Only {article_count} articles were successfully crawled.")
        print("This may be due to website changes or network issues.")
        print("The system will still work with the available articles.")


if __name__ == "__main__":
    main()