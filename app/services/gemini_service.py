import google.genai as genai
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from flask import current_app


class Item(BaseModel):
    id: int = Field(description="id of the subsubject")
    name: str = Field(description="name of the subsubject")
    prerequisites: List[int] = Field(description="ids of the prerequisites subsubdomains")


class Tree(BaseModel):
    main_subject: str = Field(description="name of the subject")
    items: List[Item] = Field("subsubjects of the subject")


def generate_learning_graph(topic):
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])

    prompt = f"""
    Agis en tant qu'expert pédagogue. Crée un graphe d'apprentissage pour : {topic}.
    Décompose le sujet en 6 à 10 étapes logiques.
    Pour chaque étape, identifie les 'prerequisites_ids' parmi les autres étapes créées.
    Exemple : L'étape 'Fonctions' (id: 2) peut avoir comme prérequis 'Variables' (id: 1).
    Assure-toi qu'il n'y a pas de cycles (A dépend de B qui dépend de A).
    """

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


def get_youtube_search_url(subdomain, domain_name):
    """
    Demande à Gemini de générer les mots-clés de recherche,
    puis construit l'URL de recherche YouTube.
    """
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])

    # On précise bien à Gemini de générer des mots-clés de recherche
    prompt = f"""
    Sujet global : {domain_name}. 
    Sous-sujet spécifique à apprendre : {subdomain.title}.
    Génère une chaîne de recherche YouTube (3-5 mots) pour trouver le meilleur tutoriel.
    Réponds uniquement avec les mots-clés, rien d'autre.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    search_query = response.text.strip().replace(" ", "+")  # Formate pour l'URL

    # Construction de l'URL de recherche YouTube standard
    return f"https://www.youtube.com/results?search_query={search_query}"


def generate_youtube_search_query(subdomain, domain_name):
    """
    Demande à Gemini de générer une requête de recherche YouTube optimisée
    pour un sous-sujet, en considérant le contexte global.
    """
    client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])

    # Construction du contexte
    prereqs = [pre.title for pre in subdomain.depends_on]
    context = f"Sujet global : {domain_name}. Prérequis déjà connus : {', '.join(prereqs) if prereqs else 'Aucun'}."

    prompt = f"""
    {context}
    Génère une requête de recherche YouTube courte et efficace (en français) pour apprendre le sous-sujet spécifique suivant : '{subdomain.title}'.
    La requête doit être conçue pour trouver des tutoriels pédagogiques adaptés à quelqu'un qui a le contexte ci-dessus.
    Réponds UNIQUEMENT avec la requête de recherche, sans ponctuation superflue ni explications.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()
