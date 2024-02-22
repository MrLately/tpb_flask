from flask import Flask, render_template, request, jsonify
import httpx
import asyncio
import config

app = Flask(__name__)
real_debrid_api_token = config.REAL_DEBRID_API_TOKEN
headers = {"Authorization": f"Bearer {real_debrid_api_token}"}
OMDB_API_KEY = config.OMDB_API_KEY
APIBAY_URL = config.APIBAY_URL
FLASK_HOST = config.FLASK_HOST
FLASK_PORT = config.FLASK_PORT
FLASK_DEBUG = config.FLASK_DEBUG
UNDESIRABLE_LIST = config.UNDESIRABLE_LIST
QUALITY_ORDER = config.QUALITY_ORDER

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        imdb_id = request.form.get('imdb_id')
        search_term = asyncio.run(fetch_title_details(imdb_id))
        torrents = asyncio.run(fetch_torrents(search_term))
        torrents_with_seeders = [torrent for torrent in torrents if int(torrent.get('seeders', 0)) > 0]
        
        for torrent in torrents_with_seeders:
            title = torrent.get('name').replace(' ', '+')
            magnet_link = f"magnet:?xt=urn:btih:{torrent.get('info_hash')}&dn={title}"
            file_size = torrent.get('size', 'Unknown Size')
            torrent['file_size'] = file_size
            torrent['magnet_link'] = magnet_link

        sorted_torrents = sort_torrents_by_quality(torrents_with_seeders)

        return render_template('index.html', torrents=sorted_torrents, search=True)
    return render_template('index.html', search=False)

@app.route('/unrestrict', methods=['POST'])
async def unrestrict():
    magnet_link = request.form.get('magnet_link')
    torrent_id = await add_magnet_to_realdebrid(magnet_link)
    video_selected = await select_files_and_start_download(torrent_id)
    if not video_selected:
        return jsonify({"error": "No video files found in torrent. Please try another."})
    
    download_link = await check_download_status_and_get_link(torrent_id)
    if not download_link:
        return jsonify({"error": "Download link not found. Please try another torrent."})
    
    unrestricted_link = await unrestrict_link(download_link)
    return jsonify({"unrestricted_link": unrestricted_link})

async def fetch_title_details(imdb_id: str) -> str:
    omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
    async with httpx.AsyncClient() as client:
        response = await client.get(omdb_url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("Type") == "episode":
            series_id = data.get("seriesID")
            series_response = await client.get(f"http://www.omdbapi.com/?i={series_id}&apikey={OMDB_API_KEY}")
            series_data = series_response.json()
            series_title = series_data.get("Title", "").replace(" ", "+")
            
            season = data.get("Season", "").zfill(2)
            episode = data.get("Episode", "").zfill(2)
            search_term = f"{series_title}+S{season}E{episode}"
        else:
            search_term = data.get("Title", "").replace(" ", "+")
        
        return search_term

async def fetch_torrents(search_term: str) -> list:
    params = {"q": search_term}
    async with httpx.AsyncClient() as client:
        response = await client.get(APIBAY_URL, params=params)
        response.raise_for_status()
        return response.json()

def sort_torrents_by_quality(torrents):
    quality_order = QUALITY_ORDER
    undesirable_keywords = UNDESIRABLE_LIST

    def get_quality_order(torrent):
        title_lower = torrent.get('name', '').lower()

        if any(keyword in title_lower for keyword in undesirable_keywords):
            return quality_order['bottom']

        for quality in quality_order:
            if quality in title_lower:
                return quality_order[quality]
        return quality_order['Other']

    return sorted(torrents, key=get_quality_order)

async def add_magnet_to_realdebrid(magnet):
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.real-debrid.com/rest/1.0/torrents/addMagnet", headers=headers, data={"magnet": magnet})
        response.raise_for_status()
        return response.json()['id']

async def select_files_and_start_download(torrent_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}", headers=headers)
        response.raise_for_status()
        files_info = response.json()['files']
        video_files = [file for file in files_info if file['path'].lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))]
        if video_files:
            largest_video_file = sorted(video_files, key=lambda x: x['bytes'], reverse=True)[0]['id']
            await client.post(f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{torrent_id}", headers=headers, data={"files": str(largest_video_file)})
            return True
        return False

async def check_download_status_and_get_link(torrent_id):
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(f"https://api.real-debrid.com/rest/1.0/torrents/info/{torrent_id}", headers=headers)
            response.raise_for_status()
            torrent_info = response.json()
            if torrent_info['status'] == 'downloaded':
                return torrent_info['links'][0]
            await asyncio.sleep(10)

async def unrestrict_link(download_link):
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.real-debrid.com/rest/1.0/unrestrict/link", headers=headers, data={"link": download_link})
        response.raise_for_status()
        return response.json()['download']

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)












