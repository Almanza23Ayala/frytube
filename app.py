from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import yt_dlp
import requests
import os

load_dotenv()

app = Flask(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_DETAILS_URL = "https://www.googleapis.com/youtube/v3/videos"

# 🔍 Buscar 50 videos con YouTube API (más rápido)
def buscar_videos(query):
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 50,
        "key": YOUTUBE_API_KEY
    }

    response = requests.get(YOUTUBE_SEARCH_URL, params=params)

    # Validar que la respuesta fue exitosa
    if response.status_code != 200:
        raise Exception(f"Error al llamar a la API: {response.status_code} - {response.text}")

    data = response.json()

    resultados = []
    for item in data.get("items", []):
        video_id = item["id"].get("videoId")
        if not video_id:
            continue
        snippet = item["snippet"]
        resultados.append({
            "video_id": video_id,
            "title": snippet["title"],
            "uploader": snippet["channelTitle"],
            "thumbnail": snippet["thumbnails"]["medium"]["url"]
        })
    return resultados


# 🎥 Obtener URL directa de reproducción con yt-dlp
def obtener_stream_url(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info.get('title'),
            'url': info.get('url'),
            'uploader': info.get('uploader'),
            'thumbnail': info.get('thumbnail')
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No se proporcionó búsqueda'}), 400
    try:
        resultados = buscar_videos(query)
        return jsonify({'results': resultados})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stream', methods=['POST'])
def api_stream():
    data = request.json
    video_id = data.get('video_id')
    if not video_id:
        return jsonify({'error': 'No se proporcionó ID del video'}), 400
    try:
        stream_info = obtener_stream_url(video_id)
        return jsonify(stream_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

