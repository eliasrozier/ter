import requests
from flask import current_app


def search_youtube_videos(query, max_results=3) -> list[dict]:
    api_key = current_app.config['YOUTUBE_API_KEY']
    base_url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        'part': 'snippet',
        'q': query,
        'key': api_key,
        'maxResults': max_results,
        'type': 'video',
        'relevanceLanguage': 'fr',  # Privilégier le français
        'safeSearch': 'strict'
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Lève une erreur si la requête échoue
        data = response.json()

        videos = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']

            videos.append({
                'id': video_id,
                'title': snippet['title'],
                'description': snippet['description'],
                'thumbnail_url': snippet['thumbnails']['high']['url'],  # Miniature haute qualité
                'channel_title': snippet['channelTitle'],
                'watch_url': f"https://www.youtube.com/watch?v={video_id}"
            })

        return videos

    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête YouTube : {e}")
        return []  # Retourne une liste vide en cas d'erreur