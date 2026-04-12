import google.genai as genai
from google.api_core import exceptions
from .schemes import *
from flask import current_app
from typing import TypeVar, Callable, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")

def gemini_call(func: Callable[P, R]) -> Callable[P, R | str]:
    def new_func(*args: P.args, **kwargs: P.kwargs) -> R | str:
        try:
            return func(*args, **kwargs)
        except exceptions.ServiceUnavailable:
            print("Erreur 503 : Gemini est surchargé.")
            return "SERVICE_BUSY"
        except Exception as e:
            # Autres erreurs (clé API, réseau, etc.)
            print(f"Erreur inattendue : {e}")
            return "ERROR"

    return new_func

@gemini_call
def generate_learning_graph(topic):
    prompt = f"""
    Agis en tant qu'expert pédagogue. Crée un graphe d'apprentissage pour: {topic}.
    Décompose le sujet en 6 à 10 étapes logiques.
    Pour chaque étape, identifie les 'prerequisites_ids' parmi les autres étapes créées.
    Exemple : L'étape 'Fonctions' (id: 2) peut avoir comme prérequis 'Variables' (id: 1).
    Assure-toi qu'il n'y a pas de cycles (A dépend de B qui dépend de A).
    """
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": Tree.model_json_schema()
        }
    )

    result = Tree.model_validate_json(response.text)
    return result

@gemini_call
def generate_youtube_search_query(subdomain, domain_name):
    """
    Demande à Gemini de générer une requête de recherche YouTube optimisée
    pour un sous-sujet, en considérant le contexte global.
    """

    # Construction du contexte
    prereqs = [pre.title for pre in subdomain.depends_on]
    context = f"Sujet global : {domain_name}. Prérequis déjà connus : {', '.join(prereqs) if prereqs else 'Aucun'}."

    prompt = f"""
    {context}
    Génère une requête de recherche YouTube courte et efficace (en français) pour apprendre le sous-sujet spécifique suivant : '{subdomain.title}'.
    La requête doit être conçue pour trouver des tutoriels pédagogiques adaptés à quelqu'un qui a le contexte ci-dessus.
    Réponds UNIQUEMENT avec la requête de recherche, sans ponctuation superflue ni explications.
    """

    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()


@gemini_call
def select_best_video(domain: str, subdomain: str, user_profile, candidate_videos) -> VideoResult | str:
    ranking_prompt = f"""
    Contexte d'apprentissage: {get_context(domain, subdomain)}
    Profil de l'élève: {user_profile}
    Vidéos disponibles: {candidate_videos}
    
    En tant qu'expert en pédagogie, sélectionne les 3 meilleures vidéos parmis les videos données afin qu'il choisisse parmi celles-ci.
    pour cet élève afin de combler ses lacunes sans répéter ce qu'il sait déjà. Essaie de prendre en compte la durée de la video et le fait que plus la video sera longue et moins l'élève sera attentif sur toute la durée
    Pour chacune des 3 videos, renvoie moi la clé du dictionnaire correspondant à la video, un court text expliquant ton choix et une liste de tags caracterisant la video.
    """

    # Appel à Gemini pour obtenir le classement final
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=ranking_prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": VideoResult.model_json_schema()
        }
    )
    result = VideoResult.model_validate_json(response.text)
    return result

@gemini_call
def generate_questions(video_id, user_profile) -> QuizScheme:
    prompt = """
    prompt pour generer les questions 
    """  # TODO
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": QuizScheme.model_json_schema()
        }
    )
    result = QuizScheme.model_validate_json(response.text)
    return result

def get_context(domain, subdomain):
    prereqs = [pre.title for pre in subdomain.depends_on]
    context = f"Sujet global: {domain.name}. Prérequis déjà connus: {', '.join(prereqs) if prereqs else 'Aucun'}."
    return context
