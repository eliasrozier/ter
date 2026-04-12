import json

import google.genai as genai
from google.api_core import exceptions
from .schemes import *
from flask import current_app
from typing import TypeVar, Callable, ParamSpec
from .user_logic import get_user_profile
from ..models import SubDomain, Domain

P = ParamSpec("P")
R = TypeVar("R")


def gemini_call(func: Callable[P, R]) -> Callable[P, R | str]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | str:
        for attempt in range(4):  # 0 à 3
            try:
                return func(*args, **kwargs)
            except exceptions.ServiceUnavailable:
                if attempt == 3:
                    break
                print(f"Retry {attempt + 1}...")
            except Exception as e:
                print(f"Erreur: {repr(e)}")
                raise e
        return "ERROR"

    return wrapper


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
    context = f"Subject : {domain_name}. Progression : {', '.join(prereqs) if prereqs else 'Aucun'}."

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
def select_best_video(domain_id: int, focus_subdomain: SubDomain, candidate_videos) -> VideoResult | str:
    context = get_user_profile(domain_id)
    json_context = json.dumps(context, indent=2, ensure_ascii=False)

    ranking_prompt = f"""
    En tant qu'expert en pédagogie, sélectionne les 3 meilleures vidéos parmis les videos données afin que l'éleve choisisse parmi celles-ci.
    selectionne les videos afin de combler ses lacunes dans le domaine {focus_subdomain.title} sans répéter ce qu'il sait déjà.
    
    voici le contexte de l'apprentissage
    ---
    Profil de l'élève: {json_context}
    ---
    
    voici les videos disponibles
    ---
    Vidéos disponibles: {candidate_videos}
    ---
    
    Essaie de prendre en compte la durée de la video et le fait que plus la video sera longue et moins l'élève sera attentif sur toute la durée
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
def generate_questions(context: str, video_id: int) -> QuizScheme:
    prompt = f"""
    Tu es un agent superviseur de l'apprentissage d'un utilisateur.
    Voici les informations de l'utilisateur au format JSON:
    -----
    {context}
    -----
    Genere entre 5 et 15 questions de type qcm
    les questions doivent etre en rapport direct avec la video youtube trouvable avec cet id: {video_id}
    utilise la transcription de la video pour trouver les questions
    les questions doivent etre adaptées au niveau de l'éleve
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


@gemini_call
def analyse_quiz(domain_id: int) -> TestResult | str:
    context = get_user_profile(domain_id)
    json_context = json.dumps(context, indent=2, ensure_ascii=False)
    prompt = f"""
    Tu es un agent superviseur de l'apprentissage d'un utilisateur.
    Voici les informations de l'utilisateur au format JSON:
    
    ---
    
    {json_context}
    
    ---
    
    considere chacun des quizz auquel l'utilisateur a repondu pour analyser sa progression
    les id de quiz sont dans l'ordre chronologique (il a repondu aux questions du quiz 1 avant celles du quiz 2)
    
    renvoie moi:
    - la progression mise à jour pour chaque domaine si c'est pertinent
    - le sous-sujet principal sur lequel l'utilisateur devrait s'ameliorer parmi les sous-sujet en cours de progression
    - une query youtube pour trouver les meilleures videos par rapport au sous sujet principal.
    - n'invente PAS de nouveaux sous-domaines, ne renvoie que des informations à propos de ceux existants.
    
    """
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": TestResult.model_json_schema()
        }
    )
    result = TestResult.model_validate_json(response.text)
    return result
