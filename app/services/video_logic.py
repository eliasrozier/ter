from .gemini_service import generate_youtube_search_query, select_best_video
from .youtube_service import search_youtube_videos
from ..models import db, Video, VideoSelection, Domain, SubDomain

def make_video_selection(sub: SubDomain, domain: Domain) -> int:
    """
    Return the id of the video_selection created
    returns -1 if a service (gemini or youtube) was too busy
    returns -2 if it encounters another error
    """

    # we generate the youtube query
    search_query = generate_youtube_search_query(sub, domain.name)
    if search_query == "SERVICE_BUSY":
        return -1
    elif search_query == "ERROR":
        return -2

    print(f"Requête générée par Gemini : {search_query}")  # Pour debug

    # we search for youtube videos
    videos = search_youtube_videos(search_query, max_results=10)
    if not videos:
        return -2

    candidate_videos = {}
    for v in videos:
        candidate_videos[v["id"]] = v

    # we select the bests videos
    recommandation = select_best_video(domain, sub, None, candidate_videos)
    if recommandation == "SERVICE_BUSY":
        return -1
    elif recommandation == "ERROR":
        return -2

    bests_videos = []
    for rec in recommandation.elements[:3]:
        tmp = candidate_videos[rec.id]
        new_vid = Video(
            youtube_id=rec.id,
            title=tmp["title"],
            thumbnail_url=tmp["thumbnail_url"],
            channel=tmp["channel_title"]
        )
        db.session.add(new_vid)
        db.session.flush()
        bests_videos.append({
            "id": new_vid.id,
            "reason": rec.reason
        })
    new_selection = VideoSelection(
        domain_id=domain.id,
        video_1_id=bests_videos[0]["id"],
        video_1_reason=bests_videos[0]["reason"],
        video_2_id=bests_videos[1]["id"],
        video_2_reason=bests_videos[1]["reason"],
        video_3_id=bests_videos[2]["id"],
        video_3_reason=bests_videos[2]["reason"]
    )
    db.session.add(new_selection)
    db.session.commit()
    return new_selection.id

