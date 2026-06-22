import requests
from concurrent.futures import ThreadPoolExecutor


BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"

def art_info(object_id):
    response = requests.get(f"{BASE_URL}/objects/{object_id}")
    data = response.json()
    return {
        "title": data.get("title"),
        "artist": data.get("artistDisplayName"),
        "image_url": data.get("primaryImage"),
        "date": data.get("objectDate"),
        "medium": data.get("medium"),
        "description": data.get("artistDisplayBio"),
        "culture": data.get("culture"),
        "dimensions": data.get("dimensions"),
        "credit": data.get("creditLine"),
        "department": data.get("department"),
        "id": data.get("objectID")
    }


def get_artworks(page=1):
    search_url = f"{BASE_URL}/search?q=painting&hasImages=true&isPublicDomain=true"
    object_ids = requests.get(search_url).json().get("objectIDs", [])
    start = (page - 1) * 12
    page_ids = object_ids[start:start + 12]
    def fetch(obj_id):
        try:
            artwork = art_info(obj_id)
            return artwork if artwork["image_url"] else None
        except:
            return None
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(fetch, page_ids))
    return [a for a in results if a]


def build_daily_pool():
    searches = [
        "impressionism", "portrait", "landscape",
        "renaissance", "baroque", "still life"
    ]
    all_ids = []
    for query in searches:
        url = f"{BASE_URL}/search?q={query}&hasImages=true&isPublicDomain=true&isHighlight=true"
        response = requests.get(url)
        ids = response.json().get("objectIDs", [])
        all_ids.extend(ids[:70])  # take 70 from each
    return list(set(all_ids))

_daily_pool = None

def get_daily_artwork():
    global _daily_pool
    if _daily_pool is None:
        _daily_pool = build_daily_pool()
    from datetime import datetime
    day = datetime.now().timetuple().tm_yday
    artwork_id = _daily_pool[day % len(_daily_pool)]
    return art_info(artwork_id)

