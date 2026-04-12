on fera les vrais prompts plus tard

profil utilisateur:
- but
- taux d'apprentissage par domaine
- questions repondues
- videos vues


## Taches à faire
- [ ] Systeme de question
  - [ ] question QCM
    - [ ] generation par gemini
    - [X] stockage en bdd
- [X] redirection video -> quiz
- [ ] analyse des resultats
- [ ] sauvegarde de progression
  - [ ] reprise de sauvegarde
    - [X] implementation
    - [ ] test
  - [X] ajout des etapes de sauvegarde
    - [X] apres selection
    - [X] apres video
    - [X] apres quiz
  - [ ] stockage des resultats API


## navigation
- quiz -> quiz_results: submit_quiz
- quiz_results -> video_select: go_select
- video_select -> video_display: show_video
- video_display -> quiz: 
