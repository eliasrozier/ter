import threading
from flask import render_template, request, current_app as app, redirect, url_for, flash
from . import db
from .models import Domain, SubDomain, Quiz, DomainStep, VideoSelection, Video
from .services.gemini_service import generate_learning_graph, generate_youtube_search_query, select_best_video
from .services.quiz_logic import generate_quiz
from .services.user_logic import add_step
from .services.video_logic import make_video_selection

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


@app.route('/domain?<int:domain_id>/roadmap')
def view_roadmap(domain_id):
    domain = Domain.query.get_or_404(domain_id)
    memo = {}
    
    # On crée un dictionnaire : { niveau: [liste_de_sous_domaines] }
    levels = {}
    for sub in domain.sub_domains:
        d = get_node_depth(sub, memo)
        if d not in levels:
            levels[d] = []
        levels[d].append(sub)
    
    # On trie les niveaux pour l'affichage (0, 1, 2...)
    sorted_levels = sorted(levels.items())
    return render_template('roadmap.html', domain=domain, sorted_levels=sorted_levels)


@app.route('/domain?<int:domain_id>/learn/<int:sub_id>')
def learn_subdomain(domain_id, sub_id):
    sub = SubDomain.query.get_or_404(sub_id)
    domain = Domain.query.get(domain_id)
    selection_id = make_video_selection(sub, domain)
    return redirect(url_for('select_video', domain_id=domain_id, selection_id=selection_id))

@app.route("/domain?<int:domain_id>/video/selection/<int:selection_id>")
def select_video(domain_id, selection_id):
    selection: VideoSelection = VideoSelection.query.get_or_404(selection_id)
    domain = Domain.query.get_or_404(domain_id)
    add_step(domain_id, "VIDEO_SELECT", selection_id)
    return render_template('select_video.html', selection=selection, domain=domain)


@app.route('/generate', methods=['POST'])
def handle_generation():
    topic = request.form.get('topic')

    # 1. Appel à Gemini pour créer l'arbre
    data = generate_learning_graph(topic)

    if data == "SERVICE_BUSY":
        flash("Les serveurs de l'IA sont actuellement saturés. Réessayez dans quelques secondes !", "warning")
        return redirect(url_for('index'))

    if data == "ERROR":
        flash("Une erreur est survenue lors de la génération. Vérifiez votre connexion.", "danger")
        return redirect(url_for('index'))

    # 2. Logique d'insertion SQL (qu'on a vue ensemble)
    new_domain = Domain(name=data.main_subject)
    db.session.add(new_domain)
    db.session.flush()
    mapping = {}

    # 3. Enregistrement des sous-domaines (marqués non appris par défaut)
    for item in data.items:
        sub = SubDomain(
            title=item.name,
            domain_id=new_domain.id,
            is_learned=False
        )
        db.session.add(sub)
        mapping[item.id] = sub

    db.session.flush()

    for item in data.items:
        current = mapping[item.id]
        for prereq in item.prerequisites:
            prereq_obj = mapping.get(prereq)
            if prereq_obj:
                current.depends_on.append(prereq_obj)

    db.session.commit()

    return redirect(url_for('view_roadmap', domain_id=new_domain.id))


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
        db.session.flush()
        app_instance = app.app_context().app

        thread = threading.Thread(
            target=generate_quiz,
            args=(video_id, quiz.id, app_instance)
        )
        thread.start()
    add_step(domain_id, "VIDEO_WATCH", video_id)

    return render_template('video_display.html', video_id=video.youtube_id, quiz_id=quiz.id, domain_id=domain_id)

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


@app.route("/domain?<int:domain_id>")
@app.route("/domain?<int:domain_id>/resume")
def resume(domain_id):
    step = DomainStep.query.filter_by(domain_id=domain_id) \
        .order_by(DomainStep.step_number.desc()).first()
    if not step:
        return redirect(url_for('dashboard'))

    match step.step_type:
        case 'VIDEO_WATCH':
            redirect(url_for('show_video', video_id=step.resource_id, domain_id=domain_id))
        case 'VIDEO_SELECT':
            redirect(url_for('select_video', selection_id=step.resource_id, domain_id=domain_id))
        case 'CONGRATS':
            pass  # TODO
        case 'QUIZ':
            redirect(url_for('view_quiz', quiz_id=step.resource_id, domain_id=domain_id))
        case _:
            flash(f"Soucis dans la base de donnée. l'etape {step.step_type} n'est pas definie", "danger")
            redirect(url_for("dashboard"))
