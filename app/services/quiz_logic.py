from .gemini_service import generate_questions
from .user_logic import get_user_profile
from ..models import db, Question, Quiz
import json

def generate_quiz(video_id: str, quiz_id: int, domain_id: int, app_instance) -> None:
    print("started quiz generation")
    with app_instance.app_context():  # Important pour toucher à la DB dans un thread
        context = get_user_profile(domain_id)
        context_json = json.dumps(context, indent=2, ensure_ascii=False)
        generated_questions = generate_questions(context_json, video_id)
        if generated_questions == "ERROR":
            print("il a pas generé les questions")
            return

        # On remplit le quiz existant
        for q in generated_questions.questions:
            new_q = Question(
                quiz_id=quiz_id,
                question_text=q.question_text,
                options=q.options,
                correct_answer=q.realAnswer,
                explanation=q.explanation
            )
            db.session.add(new_q)

        db.session.commit()
        return True
