from ..models import db, DomainStep, Answer, Domain, SubDomain, Video, Seenvideo
from typing import List

def get_user_profile(domain_id: int):
    print("get_user_profile appelé")
    print("type de domaine_id: ", type(domain_id))
    try:
        user_answers: List[Answer] = Answer.query.filter_by(domain_id=domain_id).all()
        videos_seen: List[Seenvideo] = Seenvideo.query.filter_by(domain_id=domain_id).all()
        domain: Domain = Domain.query.get(domain_id)
        progress: List[SubDomain] = [e for e in domain.sub_domains]
        print("progress: ", len(progress))
        print("get_user_profile pas de soucis")
        return {
            "global subject": domain.name,
            "progression": {
                p.title: p.progression for p in progress
            },
            "youtube seen videos": [v.video.id for v in videos_seen],
            "answers": [{
                'quiz number': ans.quiz_id,
                "question": ans.question.question_text,
                "answer": ans.answer,
                "real answer": ans.question.correct_answer
            } for ans in user_answers]
        }
    except Exception as e:
        print("l'erreur vient de get_user_profile sweg non?")
        raise e


def add_step(domain_id: int, step_type, resource_id):
    new_step = DomainStep(
        domain_id=domain_id,
        step_type=step_type,
        resource_id=resource_id
    )
    db.session.add(new_step)
    db.session.commit()

