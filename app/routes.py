from flask import render_template, request, current_app, redirect, url_for
from . import db
from .models import Domain, SubDomain
from .services.gemini_service import generate_learning_graph



@current_app.route('/', methods=['GET', 'POST'])
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
                is_learned = False
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


@current_app.route('/roadmap/<int:domain_id>')
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

@current_app.route('/learn/<int:sub_id>')
def learn_subdomain(sub_id):
    sub = SubDomain.query.get_or_404(sub_id)
    domain = Domain.query.get(sub.domain_id)
    
    # Vérification des prérequis
    if not sub.can_be_learned() and not sub.is_learned:
        flash(f"Bloqué ! Complétez d'abord les prérequis de '{sub.title}'.", "warning")
        return redirect(url_for('view_roadmap', domain_id=sub.domain_id))
    
    # Génération de l'URL de recherche via Gemini
    target_url = get_youtube_search_url(sub, domain.name)
    
    # Redirection vers YouTube dans un nouvel onglet (via le template ou direct)
    return redirect(target_url)