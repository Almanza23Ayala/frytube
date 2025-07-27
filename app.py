from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv
import yt_dlp
import requests
import os
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecret")

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Autenticación Google
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

# Rutas login
@app.route("/login")
def login():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    session["user"] = resp.json()
    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# Variables de entorno y URLs
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# Buscar videos
def buscar_videos(query):
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 50,
        "key": YOUTUBE_API_KEY
    }
    response = requests.get(YOUTUBE_SEARCH_URL, params=params)
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

# Obtener stream URL
def obtener_stream_url(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'noplaylist': True,
        'cookiefile': 'cookies.txt'  # opcional si usas cookies
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
@login_required
def index():
    user = session.get("user")
    return render_template('index.html', user=user)

@app.route('/api/search', methods=['POST'])
@login_required
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
@login_required
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
