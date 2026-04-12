import threading
from flask import render_template, request, current_app as app, redirect, url_for, flash
from . import db
from .models import Domain, SubDomain, Quiz, DomainStep, Videoselection, Video, Answer, Seenvideo
from .services.gemini_service import generate_learning_graph
from .services.quiz_logic import generate_quiz
from .services.user_logic import add_step
from .services.video_logic import update_user_profile

@app.route('/dashboard')
def dashboard():
    # Récupère tous les domaines créés par l'utilisateur
    domains = Domain.query.order_by(Domain.created_at.desc()).all()
    return render_template('dashboard.html', domains=domains)

@app.route('/', methods=['GET', 'POST'])
def index():
    # On récupère tous les parcours, du plus récent au plus ancien
    domains = Domain.query.order_by(Domain.created_at.desc()).all()
    return render_template('hub.html', domains=domains)

def get_node_depth(subdomain, memo):
    if subdomain.id in memo:
        return memo[subdomain.id]
    
    if not subdomain.depends_on:
        memo[subdomain.id] = 0
        return 0
    
    # La profondeur est 1 + la profondeur maximale de ses prérequis
    depth = 1 + max(get_node_depth(pre, memo) for pre in subdomain.depends_on)
    memo[subdomain.id] = depth
    return depth

@app.route("/domain?<int:domain_id>/video/selection/<int:selection_id>")
def select_video(domain_id, selection_id):
    print("bonjour")
    selection: Videoselection = Videoselection.query.get(selection_id)
    domain = Domain.query.get_or_404(domain_id)
    add_step(domain_id, "VIDEO_SELECT", selection_id)
    return render_template('select_video.html', selection=selection, domain=domain)

@app.route('/api/selection_status/<int:selection_id>')
def check_selection_status(selection_id):
    selection = Videoselection.query.get_or_404(selection_id)
    # On renvoie le statut au format JSON
    return {"status": selection.status}


@app.route('/generate', methods=['POST'])
def handle_generation():
    topic = request.form.get('topic')

    # 1. Appel à Gemini pour créer l'arbre
    data = generate_learning_graph(topic)

    if data == "ERROR":
        flash("Une erreur est survenue lors de la génération. Vérifiez votre connexion.", "danger")
        return redirect(url_for('index'))

    # 2. Logique d'insertion SQL (qu'on a vue ensemble)
    new_domain = Domain(name=data.main_subject)
    db.session.add(new_domain)
    db.session.flush()

    # 3. Enregistrement des sous-domaines (marqués non appris par défaut)
    for item in data.items:
        sub = SubDomain(
            title=item.name,
            domain_id=new_domain.id
        )
        db.session.add(sub)

    db.session.flush()

    db.session.commit()

    new_selection = Videoselection(
        domain_id=new_domain.id
    )
    db.session.add(new_selection)
    db.session.commit()

    app_instance = app.app_context().app
    thread = threading.Thread(
        target=update_user_profile,
        args=(new_domain.id, new_selection.id, app_instance)
    )
    thread.start()

    return redirect(url_for('select_video', domain_id=new_domain.id, selection_id=new_selection.id))


@app.route('/domain?<int:domain_id>/delete-domain', methods=['POST'])
def delete_domain(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    name = domain.name

    try:
        db.session.delete(domain)
        db.session.commit()
        flash(f"Le parcours '{name}' a été supprimé avec succès.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Une erreur est survenue lors de la suppression.", "danger")

    return redirect(url_for('dashboard'))

@app.route('/domain?<int:domain_id>/video/<video_id>')
def show_video(domain_id, video_id):
    video = Video.query.get(video_id)
    quiz = Quiz.query.filter_by(video_id=video_id).first()

    if not quiz:
        quiz = Quiz(video_id=video_id, domain_id=domain_id)
        db.session.add(quiz)
        db.session.commit()
        app_instance = app.app_context().app

        thread = threading.Thread(
            target=generate_quiz,
            args=(video_id, quiz.id, domain_id, app_instance)
        )
        thread.start()
    add_step(domain_id, "VIDEO_WATCH", video_id)

    return render_template('video_display.html', video_id=video.id, quiz_id=quiz.id, domain_id=domain_id)

@app.route("/api/domain/<int:domain_id>/video_seen/<int:video_id>")
def video_seen(domain_id: int, video_id: int) -> None:
    video_seen = Seenvideo(
        video_id=video_id,
        domain_id=domain_id
    )
    db.session.add(video_seen)
    db.session.commit()

@app.route("/domain?<int:domain_id>/quiz/<int:quiz_id>")
def view_quiz(domain_id, quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    # On passe l'ID et la liste des questions séparément au template
    add_step(domain_id, "QUIZ", quiz_id)
    return render_template(
        'quiz.html',
        quiz=quiz,
        domain_id=domain_id
    )

@app.route("/domain?<int:domain_id>/quiz/<int:quiz_id>/submit", methods=["POST"])
def submit_quiz(domain_id, quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions
    for question in questions:
        user_answer = request.form.get(f'question_{question.id}')
        is_correct = user_answer == question.correct_answer
        new_answer = Answer(
            domain_id=domain_id,
            quiz_id=quiz.id,
            question_id=question.id,
            answer=user_answer or "No answer",
            success=is_correct
        )
        db.session.add(new_answer)
    add_step(domain_id, 'QUIZ_RESULTS', quiz_id)

    new_selection = Videoselection(domain_id=domain_id)
    db.session.add(new_selection)
    db.session.flush()
    quiz.selection_id = new_selection.id
    db.session.commit()
    app_instance = app.app_context().app
    thread = threading.Thread(
        target=update_user_profile,
        args=(domain_id, new_selection.id, app_instance)
    )
    thread.start()
    return redirect(url_for(
        'view_quiz_results',
        domain_id=domain_id,
        quiz_id=quiz_id
    ))

@app.route("/domain?<int:domain_id>/quiz/<int:quiz_id>/results")
def view_quiz_results(domain_id, quiz_id):
    quiz: Quiz = Quiz.query.get(quiz_id)
    user_answers = Answer.query.filter_by(
        quiz_id=quiz_id,
        domain_id=domain_id
    ).all()
    if not user_answers:
        return "No results found", 404

    total = len(user_answers)
    correct = sum(1 for a in user_answers if a.success)
    score_percent = round((correct/total)*100)
    return render_template('quiz_results.html',
                           answers=user_answers,
                           score=score_percent,
                           correct=correct,
                           total=total,
                           domain_id=domain_id,
                           selection_id=quiz.next_selection.id)


@app.route("/domain?<int:domain_id>")
@app.route("/domain?<int:domain_id>/resume")
def resume(domain_id):
    step = DomainStep.query.filter_by(domain_id=domain_id) \
        .order_by(DomainStep.created_at.desc()).first()
    if not step:
        return redirect(url_for('dashboard'))

    match step.step_type:
        case 'VIDEO_WATCH':
            return redirect(url_for('show_video', video_id=step.resource_id, domain_id=domain_id))
        case 'VIDEO_SELECT':
            return redirect(url_for('select_video', selection_id=step.resource_id, domain_id=domain_id))
        case 'CONGRATS':
            pass  # TODO
        case 'QUIZ':
            return redirect(url_for('view_quiz', quiz_id=step.resource_id, domain_id=domain_id))
        case 'QUIZ_RESULTS':
            return redirect(url_for('view_quiz_results', quiz_id=step.resource_id, domain_id=domain_id))
        case _:
            flash(f"Soucis dans la base de donnée. l'etape {step.step_type} n'est pas definie", "danger")
            return redirect(url_for("dashboard"))
