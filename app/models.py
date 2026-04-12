from sqlalchemy import func
from . import db

class Domain(db.Model):
    """Regroupe un domaine d'apprentissage (ex: Photographie, Python)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    # Relation vers les sous-domaines
    sub_domains = db.relationship('SubDomain', backref='parent_domain', lazy=True, cascade="all, delete-orphan")

    def get_progress(self):
        return int(sum(sub.progression for sub in self.sub_domains)/len(self.sub_domains))

class SubDomain(db.Model):
    """Représente une étape ou un sous-sujet spécifique."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    progression = db.Column(db.Integer, default=0)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)

class DomainStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id', ondelete='CASCADE'), nullable=False)

    # Le type de contenu pour savoir quel template charger
    # Ex: 'VIDEO_SELECT', 'VIDEO_WATCH', 'QUIZ', 'CONGRATS'
    step_type = db.Column(db.String(50), nullable=False)

    # L'ID de l'objet lié (l'ID de la vidéo ou du quiz en base)
    resource_id = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

class Video(db.Model):
    # On stocke l'ID unique de YouTube (ex: dQw4w9WgXcQ)
    id = db.Column(db.String(20), primary_key=True)
    title = db.Column(db.String(200), nullable=False)

    thumbnail_url = db.Column(db.String(150), nullable=False)
    channel = db.Column(db.String(30))

class Videoselection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(10), default="PENDING")

    video_1_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=True)
    video_2_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=True)
    video_3_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=True)

    video_1_reason = db.Column(db.Text)
    video_2_reason = db.Column(db.Text)
    video_3_reason = db.Column(db.Text)

    video_1 = db.relationship('Video', foreign_keys=[video_1_id])
    video_2 = db.relationship('Video', foreign_keys=[video_2_id])
    video_3 = db.relationship('Video', foreign_keys=[video_3_id])

class Seenvideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id', ondelete='CASCADE'), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id', ondelete='CASCADE'), nullable=False)
    seen_at = db.Column(db.DateTime, server_default=func.now())

    video = db.relationship('Video', foreign_keys=[video_id])


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id', ondelete='CASCADE'), nullable=False)
    questions = db.relationship('Question', backref='quiz', cascade="all, delete-orphan")
    selection_id = db.Column(db.Integer, db.ForeignKey('videoselection.id'), nullable=True)
    next_selection = db.relationship('Videoselection', foreign_keys=[selection_id])

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'), nullable=False)

    question_text = db.Column(db.Text, nullable=False)

    # Stockage flexible : JSON est idéal pour les options de réponses
    # Cela permet d'avoir 2, 3 ou 4 choix sans changer la structure
    options = db.Column(db.JSON, nullable=False)

    # La réponse correcte (peut être l'index de la liste 'options' ou le texte)
    correct_answer = db.Column(db.String(200), nullable=False)

    # Optionnel : Explication générée par Gemini pour le feedback
    explanation = db.Column(db.Text)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    answer = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    question = db.relationship('Question', foreign_keys=[question_id])

