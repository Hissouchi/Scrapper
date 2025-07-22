import requests
from bs4 import BeautifulSoup
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import re
import time
import random

class Scrapper(APIView):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Priority': 'u=4',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    
    def fetch_proxies(self):
        proxy_url = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text"
        response = requests.get(proxy_url)
        if response.status_code == 200:
            proxies = response.text.split('\n')
            return [proxy.strip() for proxy in proxies if proxy.strip()]
        else:
            print("Failed to fetch proxies")
            return []
        
    def get_random_proxy(self):
        if not hasattr(self, 'proxies') or not self.proxies:
            self.proxies = self.fetch_proxies()
        if not self.proxies:
            return None
        proxy = random.choice(self.proxies)
        if proxy.startswith('http://') or proxy.startswith('https://'):
            return {
                'http': proxy,
                'https': proxy,
            }
        elif proxy.startswith('socks4://'):
            return {
                'http': proxy,
                'https': proxy,
            }
        else:
            return None

    def fetch_sitemap_urls(self, website_url):
        try:
            self.proxies = self.fetch_proxies()
            parsed_url = urlparse(website_url)
            origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = f"{origin}/robots.txt"
            # response = requests.get(robots_url, headers=self.headers, proxies=self.get_random_proxy())
            sitemap_urls = set()
            urls =[]
            
            fallback_sitemaps = [
                    f"{origin}/sitemap_index.xml",
                    f"{origin}/sitemap.xml",
                    f"{origin}/post-sitemap.xml",
                    f"{origin}/author-sitemap.xml",
                    f"{origin}/category-sitemap.xml",
                    f"{origin}/page-sitemap.xml",
                    f"{origin}/post-sitemap.xml",
                    f"{origin}/post_tag-sitemap.xml"
                ]      
            
            # if response.status_code == 200:
            #     for line in response.text.split("\n"):
            #         line = line.strip()
            #         if line.lower().startswith("sitemap:") :
            #             sitemap_url = line.split(" ")[1].strip()
            #             sitemap_urls.add(sitemap_url)
            #         elif line.startswith("http") :
            #             sitemap_urls.add(line)
                
                
            for fallback_sitemap in fallback_sitemaps :
                response = self.make_request_with_retries(fallback_sitemap)
                print(f"Testing {fallback_sitemap}: {response.status_code}")
                if response.status_code == 200 :
                    try:
                        root = ET.fromstring(response.content)
                        sitemap_urls.add(fallback_sitemap)
                    except ET.ParseError:
                        print("Contenu non-XML détecté.")
                        
            for sitemap_url in sitemap_urls:
                response_url = self.make_request_with_retries(sitemap_url)
                if response_url.status_code == 200:
                    content_type = response_url.headers.get('Content-Type', '')
                    if 'xml' in content_type :
                        try:
                            root =  ET.fromstring(response_url.content)
                            loc_elements = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                            for elem in loc_elements:
                                urls.append(elem.text)
                                
                        except ET.ParseError:
                            print(f"Échec de parsing XML pour le sitemap: {sitemap_url}")
                    elif 'html' in content_type :
                        soup = BeautifulSoup(response_url.content, 'html.parser')
                        sitemap_table = soup.find('table',{'id' : 'sitemap'})
                        if sitemap_table : 
                            for link in sitemap_table.find_all('a', href=True) :
                                urls.append(link['href'])

            return urls
        except Exception as e:
            print(f"Échec de la récupération des URLs du site: {e}")
            return []

    def make_request_with_retries(self, url, retries=2, delay=5):
        for i in range(retries):
            proxy = self.get_random_proxy()
            if proxy:
                try:
                    response = requests.get(url, headers=self.headers, proxies=proxy, timeout=10)
                except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as e:
                    print(f"Proxy error: {e}")
                    continue
            else:
                response = requests.get(url, headers=self.headers, proxies=self.get_random_proxy())
            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                print(f"403 Forbidden for {url}, retrying in {delay} seconds...")
                time.sleep(delay)
        return response
    
    def get_pagination_links(self, url):
        try:
            paginated_urls = []
            if re.search(r'(page=|/page/)', url):
                for i in range(1, 51):  # Limit to 50 pages maximum
                    paginated_url = re.sub(r'(page=|/page/)(\d+)', rf'\g<1>{i}', url)
                    paginated_urls.append(paginated_url)
            else :
                paginated_urls.append(url)                 
            return paginated_urls
        except Exception as e:
            print(f"Echec de détection de la paginantion : {e}")
            return []

    def extract_content(self, url, content_types) :
        try:
            datas_extracted = []
            proxy = self.get_random_proxy()
            if proxy:
                try:
                    response = requests.get(url, headers=self.headers, proxies=proxy, timeout=10)
                except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as e:
                    print(f"Proxy error: {e}")
                    return []
            else:
                response = requests.get(url, headers=self.headers)
            if response.status_code == 200 :
                soup = BeautifulSoup(response.text, 'html.parser')
                for content_type in content_types :
                    if content_type == "titles":
                        datas_extracted.extend(["titles",url])
                        datas_extracted.append([tag.text for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]) 
                    elif content_type == "links":
                        datas_extracted.extend(["links",url])
                        datas_extracted.append([a['href'] for a in soup.find_all('a', href=True)])
                    elif content_type == "paragraphs":
                        datas_extracted.extend(["paragraphs",url])
                        datas_extracted.append([p.text for p in soup.find_all('p')])
                    elif content_type == "tables":
                        datas_extracted.extend(["tables",url])
                        datas_extracted.append([str(table) for table in soup.find_all('table')])
            return datas_extracted
        except Exception as e:
            print(f"Echec d'extraction des données depuis {url}: {e}")
            return []
        
    def post(self, request):
        urls = request.data.get("urls", [])
        content_type = request.data.get("content_type")
        is_full_website = request.data.get("full_website", True)
        
        extracted_data = []
        try:
            if is_full_website and len(urls) == 1:
                website_url = urls[0]
                sitemap_urls = self.fetch_sitemap_urls(website_url)
                for sitemap_url in sitemap_urls:
                    data = self.extract_content(sitemap_url, content_type)
                    extracted_data.extend(data)
            else:
                for url in urls:
                    paginated_urls = self.get_pagination_links(url)
                    for paginated_url in paginated_urls:
                        data = self.extract_content(paginated_url, content_type)
                        extracted_data.extend(data)
            
            return Response({"data": extracted_data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in processing request: {e}")
            return Response({"error": "Failed to process request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
