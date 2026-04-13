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

    id1 = recommandation.video1.id
    vid1 = Video.query.get(id1)
    if not vid1:
        tmp = candidate_videos[id1]
        vid1 = Video(
                id=id1,
                title=tmp["title"],
                thumbnail_url=tmp["thumbnail_url"],
                channel=tmp["channel_title"]
            )
        db.session.add(vid1)
        db.session.flush()
    video_selection.video_1_id = id1
    video_selection.video_1_reason = recommandation.video1.reason

    id2 = recommandation.video2.id
    vid2 = Video.query.get(id2)
    if not vid2:
        tmp = candidate_videos[id2]
        vid2 = Video(
            id=id2,
            title=tmp["title"],
            thumbnail_url=tmp["thumbnail_url"],
            channel=tmp["channel_title"]
        )
        db.session.add(vid2)
        db.session.flush()
    video_selection.video_2_id = id2
    video_selection.video_2_reason = recommandation.video2.reason

    id3 = recommandation.video3.id
    vid3 = Video.query.get(id3)
    if not vid3:
        tmp = candidate_videos[id3]
        vid3 = Video(
            id=id3,
            title=tmp["title"],
            thumbnail_url=tmp["thumbnail_url"],
            channel=tmp["channel_title"]
        )
        db.session.add(vid3)
        db.session.flush()
    video_selection.video_3_id = id3
    video_selection.video_3_reason = recommandation.video3.reason

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
