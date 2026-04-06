from flask import render_template, request, current_app as app, redirect, url_for, flash
from . import db
from .models import Domain, SubDomain
from .services.gemini_service import generate_learning_graph, generate_youtube_search_query
from .services.youtube_service import search_youtube_videos

@app.route('/dashboard')
def dashboard():
    # Récupère tous les domaines créés par l'utilisateur
    domains = Domain.query.order_by(Domain.created_at.desc()).all()
    return render_template('dashboard.html', domains=domains)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        topic = request.form.get('topic')
        
        # 1. Appel à l'API Gemini
        data = generate_learning_graph(topic)
        
        # 2. Enregistrement du Domaine principal
        new_domain = Domain(name=data.main_subject)
        db.session.add(new_domain)
        db.session.flush() # On commit pour avoir l'ID du domaine
        
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

    return render_template('index.html')


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


@app.route('/roadmap/<int:domain_id>')
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


@app.route('/learn/<int:sub_id>')
def learn_subdomain(sub_id):
    sub = SubDomain.query.get_or_404(sub_id)
    domain = Domain.query.get(sub.domain_id)

    # 1. Sécurité : Vérifier si l'utilisateur PEUT apprendre ce sujet
    if not sub.can_be_learned() and not sub.is_learned:
        flash(f"Vous devez d'abord compléter les prérequis pour '{sub.title}'.", "warning")
        return redirect(url_for('view_roadmap', domain_id=sub.domain_id))

    # 2. Gemini génère la requête de recherche optimisée
    search_query = generate_youtube_search_query(sub, domain.name)
    print(f"Requête générée par Gemini : {search_query}")  # Pour debug

    # 3. YouTube cherche les vidéos
    videos = search_youtube_videos(search_query, max_results=3)

    if not videos:
        flash("Impossible de trouver des vidéos sur YouTube pour le moment. Réessayez plus tard.", "danger")
        return redirect(url_for('view_roadmap', domain_id=sub.domain_id))

    return render_template('select_video.html',
                           sub=sub,
                           domain=domain,
                           videos=videos,
                           search_query=search_query)


@app.route('/delete-domain/<int:domain_id>', methods=['POST'])
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