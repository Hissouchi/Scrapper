# fichier : utils/scrape_logic.py

import re
import time
from datetime import datetime
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

HEADLESS = True  # passer à False pour voir le navigateur

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

PAGINATION_MAX = 1  # Nombre de pages à scrapper

def parse_detail_features(feature_elements):
    features = {}

    for el in feature_elements:
        text = el.inner_text().strip().lower()

        if "ascenseur" in text:
            features["ascenseur"] = True
        elif "balcon" in text:
            features["balcon"] = True
        elif "parking" in text or "garage" in text:
            features["parking"] = True
        elif "climatisation" in text:
            features["climatisation"] = "centralisée"
        elif "chauffage" in text:
            features["chauffage"] = "central"
        elif "jardin" in text:
            features["jardin"] = True
        elif "meublé" in text or "meuble" in text:
            features["meuble"] = True
        elif "piscine" in text:
            features["piscine"] = True
        elif "sécurité" in text or "gardien" in text or "concierge" in text:
            if "sécurité" not in features:
                features["sécurité"] = []
            if "gardien" in text or "concierge" in text:
                features["sécurité"].append("gardien")
            else:
                features["sécurité"].append(text)
        elif "étage" in text:
            match = re.search(r'\d+', text)
            if match:
                features["étage"] = int(match.group())
    
    return features

def extract_annonce_data(context, card, page):
    try:
        #Titre
        title_el = card.query_selector("h2.listingTit a")
        if not title_el:
            return None
        title = title_el.inner_text().strip()
        print(f"[INFO] Titre extrait : {title}")
        
        #Prix
        price_el = card.query_selector("span.priceTag")
        if not price_el:
            return None
        price_raw = price_el.inner_text().strip()
        price = int(re.sub(r"[^\d]", "", price_raw))
        print(f"[INFO] Prix extrait : {price} MAD")
        if not price:
            return None
        
        #Ville et région
        city= card.query_selector(".contactBar span")
        if not city:
            print("[WARN] Ville non trouvée, annonce ignorée")
            return None
        city_name = city.inner_text().strip()
        print(f"[INFO] Ville extraite : {city_name}")
        
        link = card.get_attribute("linkref") or title_el.get_attribute("href")
        full_url = link if link.startswith("http") else f"https://www.mubawab.ma{link}"
        source_id = re.findall(r"/a/(\d+)", full_url)
        source_id = source_id[0] if source_id else ""
        
        #Surface, pièces, chambres, salles de bain
        surface = rooms = bedrooms = bathrooms = None
        for span in card.query_selector_all("div.adDetailFeature span"):
            text = span.inner_text().strip()
            if "m²" in text:
                surface = int(re.search(r'\d+', text).group())
                print(f"[INFO] Surface extraite : {surface} m²")
            elif "Pièces" in text or "Pièce" in text:
                rooms = int(re.search(r'\d+', text).group())
                print(f"[INFO] Nombre de pièces extrait : {rooms}")
            elif "Chambres" in text or "Chambre" in text:
                bedrooms = int(re.search(r'\d+', text).group())
                print(f"[INFO] Nombre de chambres extrait : {bedrooms}")
            elif "Salle de bain" in text or "Salles de bains" in text:
                bathrooms = int(re.search(r'\d+', text).group())
                print(f"[INFO] Nombre de salles de bain extrait : {bathrooms}")
                
        
        #images
        img_tag = card.query_selector("img.sliderImage")
        image_url = img_tag.get_attribute("src") if img_tag else None
        
        #Téléphone
        phone_btn = card.query_selector(".contactPhoneClick")
        if not phone_btn:
            print("[WARN] Bouton téléphone non trouvé")
            return None
        
        _phone = "" 
        try:
            
            print("[INFO] Click sur bouton : ", phone_btn.inner_text().strip())
            phone_btn.click()
            print("[OK] Click réussi sur le bouton téléphone")
            page.wait_for_selector("#phonePopup", state="attached", timeout=8000)
            phone_el = page.wait_for_selector("#phonePopup .phoneText", timeout=8000)
            _phone = phone_el.inner_text().strip() if phone_el else ""
            print(f"[INFO] Numéro de téléphone extrait : {_phone}")
            close_popup=page.query_selector(".fancybox-close")
            popup_visible = page.is_visible("#phonePopup")
            overlay_visible = page.is_visible("#phonePopupOverlay")
            if close_popup and (popup_visible or overlay_visible):
                print("[INFO] Fermeture de la popup téléphone")
                
                try :
                    close_popup.click()
                    print("[OK] Click sur bouton de fermeture envoyé")
                    page.wait_for_selector("#phonePopup", state="hidden", timeout=2000)
                    page.wait_for_selector("#phonePopupOverlay", state="hidden", timeout=2000) 
                    print("[OK] Popup téléphone fermée")
                    
                except Exception as e:
                    print(f"[WARN] Erreur lors de la fermeture : {e}")
                    print("[INFO] Forçage de la fermeture par JavaScript")
                    page.evaluate("""
                                () => {
                                    const popup = document.querySelector("#phonePopup");
                                    const overlay = document.querySelector("#phonePopupOverlay");
                                    if (popup) popup.style.display = "none";
                                    if (overlay) overlay.style.display = "none";
                                }
                            """)
                    print("[OK] Popup forcée à se fermer via JavaScript")
            else:
                print("[INFO] Popup déjà fermée ou bouton introuvable")
        except Exception as e:
            print(f"[WARN] Clic échoué sur le bouton téléphone :{e}")

        if not re.match(r"^\+?[0-9\s\-]+$", _phone):
            print(f"[WARN] Numéro invalide, annonce ignorée : {full_url}")
            return None
        
        #Type de propriété et features supplémentaires
        property_type = "appartement"
        try:
            print(f"[INFO] Accès à la page de détails : {full_url}")
            detail_page = context.new_page()
            detail_page.goto(full_url, timeout=15000)
            featured_block = detail_page.wait_for_selector(".adFeatures .adMainFeature ", timeout=5000)
            features_container = detail_page.query_selector_all(".adFeatures")[1] 
            
            if featured_block:
                value_element = featured_block.query_selector(".adMainFeatureContentValue")
                if value_element:
                    property_type = value_element.inner_text().strip()
                    print(f"[INFO] Type de propriété extrait : {property_type}")
                else:
                    print("[WARN] Element .adMainFeature non trouvé, type de propriété par défaut utilisé")
            else:
                print("[WARN] Bloc de caractéristiques non trouvé, type de propriété par défaut utilisé")
            detail_page.close()
            print(f"[INFO] CONTENU EXTRAIT : {property_type}")
        except Exception as e:
            print(f"[WARN] Erreur lors de la récupération du type de propriété : {e}")
            
        return {
            "title": title,
            "property_type": property_type,
            "city": city_name,
            "district": city_name,
            "region": city_name,
            "address": "",
            "surface_area": surface,
            "rooms_count": rooms,
            "bedrooms_count": bedrooms,
            "bathrooms_count": bathrooms,
            "price": price,
            "description": "",
            "features": "",
            "images_urls": [image_url] if image_url else [],
            "publication_date": datetime.now().date().isoformat(),
            "source": "Mubawab",
            "source_id": source_id,
            "url_source": full_url,
            "contact_info": {
                "name": "Mubawab",
                "email": "",
                "phone": _phone
            },
            "is_available": True,
            "is_featured": "feat" in card.get_attribute("class"),
            "latitude": None,
            "longitude": None
        }

    except Exception as e:
        print(f"[ERREUR] Parsing carte : {e}")
        return None

def run_scraper(since_date):
    data_collected = []
    base_url = "https://www.mubawab.ma/fr/cc/immobilier-a-vendre-all"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        for i in range(1, PAGINATION_MAX + 1):
            url = f"{base_url}:p:{i}"
            print(f"[INFO] Accès : {url}")
            try:
                page.goto(url, timeout=60000)
                page.wait_for_selector(".listingBox", timeout=10000)
                time.sleep(3)  # crawl delay simulé
                cards = page.query_selector_all(".listingBox")
                print(f"[INFO] {len(cards)} annonces trouvées")

                for card in cards:
                    data = extract_annonce_data(context, card, page)
                    if data:
                        date_obj = datetime.fromisoformat(data["publication_date"]).date()
                        if date_obj >= since_date:
                            data_collected.append(data)
            except Exception as e:
                print(f"[WARN] Page échouée : {e}")

        browser.close()

    return data_collected