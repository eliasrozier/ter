from ..models import db, DomainStep

def get_user_profile():
    pass  # TODO

def add_step(domain_id: int, step_type, resource_id):
    new_step = DomainStep(
        domain_id=domain_id,
        step_type=step_type,
        resource_id=resource_id
    )
    db.session.add(new_step)
    db.session.commit()
