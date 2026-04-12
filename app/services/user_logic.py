from ..models import db, DomainStep, Answer, Domain, SubDomain
from typing import List

def get_user_profile(domain_id):
    user_answers: List[Answer] = Answer.query.filter_by(domain_id=domain_id).all()
    domain: Domain = Domain.query.get(domain_id)
    progress: List[SubDomain] = Domain.sub_domains


    return {
        "global subject": domain.name,
        "progression": {
            p.title: p.percent for p in progress
        },
        "answers": [{
            "question": ans.question.question_text,
            "answer": ans.answer,
            "real answer": ans.question.correct_answer
        } for ans in user_answers]
    }

def add_step(domain_id: int, step_type, resource_id):
    new_step = DomainStep(
        domain_id=domain_id,
        step_type=step_type,
        resource_id=resource_id
    )
    db.session.add(new_step)
    db.session.commit()
