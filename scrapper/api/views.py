import requests
from bs4 import BeautifulSoup
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import re

class Scrapper(APIView):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    def fetch_sitemap_urls(self, website_url):
        try:
            robots_url = f"{website_url}/robots.txt"
            print(robots_url)
            response = requests.get(robots_url, headers=self.headers)
            sitemap_urls = []
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if line.startswith("Sitemap:"):
                        sitemap_url = line.split(":")[1].strip()
                        sitemap_urls.append(sitemap_url)
            return sitemap_urls
        except Exception as e:
            print(f"Failed to fetch sitemap URLs: {e}")
            return []

    def get_pagination_links(self, url):
        try:
            # Check common pagination patterns and limit to a maximum of 50 pages
            paginated_urls = []
            if re.search(r'(page=|/page/)', url):
                for i in range(1, 51):  # Limit to 50 pages maximum
                    paginated_url = re.sub(r'(page=|/page/)(\d+)', rf'\g<1>{i}', url)
                    print(paginated_url)
                    paginated_urls.append(paginated_url)
            else :
                paginated_urls.append(url) 
                print(paginated_urls)
                
            return paginated_urls
        except Exception as e:
            print(f"Failed to detect pagination: {e}")
            return []

    def extract_content(self, url, content_types):
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200 :
                soup = BeautifulSoup(response.text, 'html.parser')
                datas_extracted = []
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
            print(f"Failed to extract content from {url}: {e}")
            return []

    def post(self, request):
        urls = request.data.get("urls", [])
        content_type = request.data.get("content_type")
        is_full_website = request.data.get("full_website", True)
        
        extracted_data = []
        try:
            #print('Is_full'+len(urls))
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
