# fichier : utils/scrape_logic.py

import re
import time
from datetime import datetime
import requests
from urllib.parse import urlparse
from decimal import Decimal

from playwright.sync_api import sync_playwright

HEADLESS = True  # passer à False pour voir le navigateur

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

PAGINATION_MAX = 1  # Nombre de pages à scrapper

def parse_detail_features(detail_page):
    features = {}
    try:
        ad_features_blocks = detail_page.query_selector_all(".adFeatures")
        if len(ad_features_blocks) > 1:
            ad_feature_elements = ad_features_blocks[1].query_selector_all(".adFeature span")
            for el in ad_feature_elements:
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
    except Exception as e:
        print(f"[WARN] Erreur lors du parsing des features : {e}")
    return features

def parse_ad_main_features(detail_page):
    infos = {}
    ad_main_features = detail_page.query_selector_all(".adMainFeature")
    for feature in ad_main_features:
        label_el = feature.query_selector(".adMainFeatureContentLabel")
        value_el = feature.query_selector(".adMainFeatureContentValue")
        if label_el and value_el:
            label = label_el.inner_text().strip().lower()
            value = value_el.inner_text().strip()
            infos[label] = value
    return infos

def extract_card_images(card):
    image_urls = set()

    try:
        print("[INFO] Extraction des images des cartes...")
        
        imgs = card.query_selector_all(".photoBox .slick-track .slick-slide img")
        print(f"[INFO] Image trouvée : {len(imgs)}")

        if len(imgs)> 0:
            for img in imgs:
                src = img.get_attribute("src")
                data_lazy = img.get_attribute("data-lazy")
                if src and src.strip():
                    image_urls.add(src.strip())
                elif data_lazy and data_lazy.strip():
                    image_urls.add(data_lazy.strip())

        print(f"[INFO] {len(image_urls)} image(s) extraites après nettoyage.")
        return list(image_urls)


    except Exception as e:
        print(f"[WARN] Erreur lors de l'extraction des images : {e}")
        return []

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
        price_digits = re.sub(r"[^\d]", "", price_raw)
        if not price_digits:
            print(f"[WARN] Prix vide ou invalide : {price_raw}")
            return None
        price = int(price_digits)
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
        print(f"[INFO] Link OK")
        full_url = link if link.startswith("http") else f"https://www.mubawab.ma{link}"
        print(f"[INFO] full_url OK")
        source_input = card.query_selector("input.adId")
        print(f"[INFO] source_input OK")
        source_id = source_input.get_attribute("value") if source_input else ""
        print(f"[INFO] source_id OK")
        print(f"[INFO] id source pour cette annonce est : {source_id}")
        
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
                    # close_popup.click()
                    # print("[OK] Click sur bouton de fermeture envoyé")
                    # page.wait_for_selector("#phonePopup", state="hidden", timeout=2000)
                    # page.wait_for_selector("#phonePopupOverlay", state="hidden", timeout=2000) 
                    # print("[OK] Popup téléphone fermée")
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
                    
                except Exception as e:
                    print(f"[WARN] Erreur lors de la fermeture : {e}")
                  
            else:
                print("[INFO] Popup déjà fermée ou bouton introuvable")
        except Exception as e:
            print(f"[WARN] Clic échoué sur le bouton téléphone :{e}")

        if not re.match(r"^\+?[0-9\s\-]+$", _phone):
            print(f"[WARN] Numéro invalide, annonce ignorée : {full_url}")
            return None
        
        #Type de propriété, features supplémentaires et positionnement
        property_type = "appartement"
        features_data = {}
        latitude = longitude = None
        description = ""
        
        try:
            print(f"[INFO] Accès à la page de détails : {full_url}")
            detail_page = context.new_page()
            detail_page.goto(full_url, timeout=15000)
            
            infos_extraites = parse_ad_main_features(detail_page)
            print(f"[INFO] Informations extraites : {infos_extraites}")
            
            extracted_type = str(infos_extraites.get("type de bien", "appartement")).strip().lower()
            print(f"[INFO] Type de propriété extrait : {extracted_type}")
            
            ALLOWED_TYPES = ['appartement', 'maison', 'villa', 'studio', 'duplex', 'garage', 'terrain', 'local_commercial', 'bureau']
            property_type = extracted_type if extracted_type in ALLOWED_TYPES else "appartement"
            
            floor = None
            if property_type == "appartement" and "étage du bien" in infos_extraites : 
                match = re.search (r"\d+", infos_extraites["étage du bien"])
                if match:
                    floor = int(match.group())
                    print(f"[INFO] Étage extrait : {floor}")
            
            features_data = parse_detail_features(detail_page)
            print(f"[INFO] Caractéristiques extraites supplément: {features_data}")
            
            if floor is not None:
                features_data["étage"] = floor
                print(f"[INFO] Étage ajouté aux caractéristiques : {floor}")
                
            map_el = detail_page.query_selector("#mapOpen")
            if map_el:
                lat_attr = map_el.get_attribute("lat")
                lon_attr = map_el.get_attribute("lon")
                if lat_attr and lon_attr:
                    latitude = float(lat_attr)
                    longitude = float(lon_attr)
                    print(f"[INFO] Latitude et longitude extraites : {latitude}, {longitude}")
                else:
                    print("[WARN] Latitude ou longitude non trouvées dans l'élément de carte")
            else:
                print("[WARN] Élément de carte non trouvé dans la page de détails")
            
            # Récupération de la description
            description_el = detail_page.query_selector(".blockProp")
            description = description_el.inner_text().strip() if description_el else ""
            print(f"[INFO] Élément de description trouvé : {description or 'Aucun'}")
            detail_page.close()
            print(f"[INFO] CONTENU EXTRAIT : {property_type}")
        except Exception as e:
            print(f"[WARN] Erreur lors de la récupération du type de propriété : {e}")
        print ("[INFO] Fin de l'extraction des données de l'annonce......................")    
        # Construction de l'objet final    
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
            "price": float(price),
            "description": description if description else "",
            "features": features_data,
            "images_urls": extract_card_images(card) if card else [],
            "publication_date": datetime.now().date().isoformat(),
            "source": "Mubawab",
            "source_id": source_id,
            "url_source": full_url,
            "contact_info": {
                "name": "Mubawab",
                "email": "hasnaa.ouchitachen@hightech.edu",
                "phone": _phone
            },
            "is_available": True,
            "is_featured": False,
            "latitude": latitude,
            "longitude": longitude
        }

    except Exception as e:
        print(f"[ERREUR] Parsing carte : {e}")
        return None

def run_scraper(since_date):
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
                time.sleep(3) 
                cards = page.query_selector_all(".listingBox")
                print(f"[INFO] {len(cards)} annonces trouvées")

                for card in cards:
                    data = extract_annonce_data(context, card, page)
                    if data:
                        date_obj = datetime.fromisoformat(data["publication_date"]).date()
                        if date_obj >= since_date:
                            try:
                                res = requests.post("http://127.0.0.1:8000/api/announcements/", json=data)
                                print(f"✔ ({res.status_code}): {res.json()}")
                            except Exception as e:
                                print(f" Envoi échoué pour une annonce : {e}")
            except Exception as e:
                print(f"[WARN] Échec d'envoi de la carte : {e}")

        browser.close()