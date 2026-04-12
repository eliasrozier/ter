from .gemini_service import generate_questions
from ..models import db, Question, Quiz
from .user_logic import get_user_profile

def generate_quiz(video_id, quiz_id, app_instance, _nb_try=0) -> bool:
    with app_instance.app_context():  # Important pour toucher à la DB dans un thread
        # Simulation appel Gemini...
        user_profile = get_user_profile()
        generated_questions = generate_questions(video_id, user_profile)
        if isinstance(generated_questions, str):
            if generated_questions == "SERVICE_BUSY":
                if _nb_try < 3:
                    generate_quiz(video_id, quiz_id, app_instance, _nb_try+1)
                else:
                    return False
            elif generated_questions == "ERROR":
                return False

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
