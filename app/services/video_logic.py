from .gemini_service import select_best_video, analyse_quiz
from .schemes import TestResult
from .youtube_service import search_youtube_videos
from ..models import db, Video, Videoselection, Domain, SubDomain

def make_video_selection(domain: Domain, search_query: str, focus_subdomain: SubDomain, video_selection) -> int:
    """
    Return the id of the video_selection created
    returns -1 if it encounters an error
    """
    print(f"Requête générée par Gemini : {search_query}")  # Pour debug

    # we search for youtube videos
    videos = search_youtube_videos(search_query, max_results=10)
    if not videos:
        print("search_youtube_videos a crash")
        return "ERROR"

    print("videos youtube trouvées")

    candidate_videos = {}
    for v in videos:
        candidate_videos[v["id"]] = v

    # we select the bests videos
    recommandation = select_best_video(domain.id, focus_subdomain, candidate_videos)
    if recommandation == "ERROR":
        print("select_best_video a crash")
        return "ERROR"

    print("meilleures videos choisies")

    bests_videos = []
    for rec in recommandation.elements[:3]:
        tmp = candidate_videos[rec.id]
        vid = Video.query.get(rec.id)
        if not vid:
            vid = Video(
                id=rec.id,
                title=tmp["title"],
                thumbnail_url=tmp["thumbnail_url"],
                channel=tmp["channel_title"]
            )
            db.session.add(vid)
            db.session.flush()
        bests_videos.append({
            "id": vid.id,
            "reason": rec.reason
        })
    video_selection.video_1_id = bests_videos[0]["id"]
    video_selection.video_1_reason = bests_videos[0]["reason"]
    video_selection.video_2_id = bests_videos[1]["id"]
    video_selection.video_2_reason = bests_videos[1]["reason"]
    video_selection.video_3_id = bests_videos[2]["id"]
    video_selection.video_3_reason = bests_videos[2]["reason"]
    video_selection.status = "READY"
    db.session.commit()
    print("j'ai fini ma selection")
    return "SUCCESS"


def update_user_profile(domain_id: int, video_selection_id: int, app_instance):
    with app_instance.app_context():
        video_selection: Videoselection = Videoselection.query.get(video_selection_id)
        domain = Domain.query.get(domain_id)
        new_data: TestResult = analyse_quiz(domain_id)
        if new_data == "ERROR":
            video_selection.status = "CRASHED"
            db.session.commit()
            print("analyse quiz a crash")
            return
        print("analyse du quiz faite")

        all_subs = [s.title for s in SubDomain.query.filter_by(domain_id=domain_id).all()]

        focus_subdomain = SubDomain.query.filter_by(domain_id=domain_id, title=new_data.focus_subdomain).first()
        for d, v in new_data.progress.items():
            if d not in all_subs:
                raise IndexError("gemini a fait de la merde ce connard")
            sub: SubDomain = SubDomain.query.filter_by(domain_id=domain_id, title=d).first()
            sub.progression = v
        db.session.commit()
        result = make_video_selection(domain, new_data.youtube_search_query, focus_subdomain, video_selection)
        print("selection de video faite")
        if result == "ERROR":
            print("make_video_selection a crash")
            video_selection.status = "CRASHED"
            db.session.commit()
            return
        print("profil mis à jour")

        return
