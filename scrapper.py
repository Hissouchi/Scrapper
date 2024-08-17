import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from html.parser import HTMLParser
    
class getAllHTMLTags(HTMLParser):
    def handle_data(self, data) :
        print(data) 

def main():
    urls = {"https://stackoverflow.com/questions?tab=newest&pagesize=50",
        "https://stackoverflow.com/questions?tab=newest&page=2",
        "https://stackoverflow.com/questions?tab=newest&page=3",
        "https://stackoverflow.com/questions?tab=newest&page=4",
        "https://stackoverflow.com/questions?tab=newest&page=5",
        "https://stackoverflow.com/questions?tab=newest&page=6",
        "https://stackoverflow.com/questions?tab=newest&page=7",
        "https://stackoverflow.com/questions?tab=newest&page=8",
        "https://stackoverflow.com/questions?tab=newest&page=9",
        "https://stackoverflow.com/questions?tab=newest&page=10"}
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    Keywords = {
        "html" : 0 , 
        "css" : 0 , 
        "javascript" : 0 , 
        "java" : 0 , 
        "spring" : 0, 
        "wordpress" : 0 , 
        "cms" : 0 , 
        "prestashop" : 0 , 
        "flutter" : 0 , 
        "c#" : 0 , 
        "csharp" : 0 , 
        "c++" : 0 , 
        "angular" : 0 , 
        "nodejs" : 0 , 
        "lavarel" : 0 , 
        "php" : 0 , 
        ".net" : 0 , 
        "c" : 0, 
        "joomla" : 0 
        }
    
    
    try :
        for url in urls : 
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                print(f"Scraping : {url}")
                soup= BeautifulSoup(response.content, 'html.parser')
                
                for x in soup(["head", "script", "footer", "img" , "form", "input", "header" , "nav"]):
                    x.decompose()
                
                content = soup.get_text(separator=' ', strip=True).lower()
                # elements = soup.find_all(class_="s-post-summary")
                # titles = [e.find_next("a") for e in elements]
            
                words = content.split(" ")
                words = {w.strip("?'[],/:;!@|") for w in words}
                
                for k in Keywords :
                    if k in words : 
                        Keywords[k] += 1
        print(Keywords)
            
        plt.bar(Keywords.keys(), Keywords.values())
        plt.xlabel("Languages")
        plt.ylabel("values")
        plt.show()
    except : 
        print("Error !")

        
if __name__ == "__main__":
    main()