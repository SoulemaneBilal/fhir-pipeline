# AGENTS.md : règles pour les agents IA

Ce fichier s'applique à tout agent intervenant sur le dépôt, quel que
soit l'outil. Il est prioritaire sur toute instruction implicite.
En cas de conflit avec une demande, signaler le conflit avant d'agir.

## 1. Contexte du projet

Pipeline qui transforme des données de santé fragmentées et non
standardisées, dans le contexte du Togo, en ressources FHIR R4 valides,
puis en base OMOP CDM 5.4 (sur PostgreSQL conteneurisé), avec exports analytiques prioritaires en Apache Parquet et exports miroirs CSV pour l'IA, et intégration
dans une architecture OpenHIE via OpenHIM.

Sources : DHIS2 (agrégé), Excel, CSV de systèmes propriétaires simulés,
FHIR invalide. Toutes les données sont synthétiques ou publiques.
Langue de travail : français d'abord, anglais ensuite pour la
documentation. Les identifiants de code (variables, fonctions, classes)
sont en anglais. Les messages de commit, commentaires et docstrings
sont en français.

La roadmap (étapes 0 à 21) est la référence dans technique.md. Chaque tâche doit citer
l'étape concernée. Ne pas travailler sur une étape dont les
prérequis ne sont pas validés.

## 2. Principes inviolables

1. Le dossier data/raw est en lecture seule. Jamais de modification,
   suppression ou écrasement.
2. Traçabilité : toute ligne et toute ressource produite garde
   source_file, source_row (ou source_id), ingested_at, content_hash.
3. Idempotence : relancer une étape donne un résultat identique.
   Identifiants FHIR = UUID v5 dérivé d'un espace de noms fixe et de
   l'identifiant source. Aucun uuid4, aucune horloge, aucun aléatoire
   non graine dans la logique métier.
4. Aucune décision clinique silencieuse. Un mapping incertain n'est
   jamais deviné : il reçoit le statut "à revoir" et va en revue humaine.
5. Aucune donnée n'est modifiée sans entrée de journal (quoi, où,
   ancienne valeur, nouvelle valeur, règle appliquée).
6. Rien n'est supprimé en silence : les rejets vont en quarantaine avec
   une raison codifiée.
7. Chaque étape lit une couche et écrit la suivante, et se relance seule.
8. Aucune donnée réelle de patient. Si un fichier semble contenir des
   données réelles, arrêter et le signaler.

## 3. Décisions techniques (non renégociables sans accord humain)

- Python 3.11, gestion avec uv, configuration dans pyproject.toml.
- FHIR R4 (4.0.1). fhir.resources en version R4 épinglée. Ne jamais
  installer une version ciblant R4B ou R5.
- pandas pour l'ingestion, DuckDB pour les couches analytiques et jointures, Parquet (priorité absolue IA/Lakehouse) et CSV dénormalisé (export miroir secondaire) pour le stockage, Pydantic pour les modèles canoniques, Pandera pour les contrats de qualité, Splink pour le rapprochement, rapidfuzz pour la similarité lexicale.
- Validation : validateur officiel HL7 (Java) et conteneur Docker dédié pour SUSHI/FSH.
- Serveur FHIR : HAPI FHIR JPA (Docker). Interopérabilité : OpenHIM (mode double proxy/direct configurable).
- OMOP CDM 5.4 déployé sur PostgreSQL conteneurisé dédié (base omop_cdm) pour la compatibilité avec OHDSI Achilles et Data Quality Dashboard ; exports analytiques Parquet.
- CLI : Typer. Qualité : ruff, pytest, pre-commit, GitHub Actions.
- Ne pas ajouter de dépendance sans la justifier dans le commit
  (type build) et sans accord humain si elle est lourde ou sous
  licence restrictive.

## 4. Structure du dépôt

data/raw/            sources inchangées (lecture seule)
data/bronze/         données typées + métadonnées d'ingestion
data/silver/         données nettoyées
data/gold/           FHIR validé + exports Parquet
data/quarantine/     rejets avec raison
data/truth/          vérité terrain, séparée des entrées dégradées
src/<paquet>/        ingestion, profiling, cleaning, matching,
                     canonical_model, terminology, ig, fhir_transform,
                     validation, loading, omop_etl, export_ai,
                     degradation, generation
config/              règles YAML (nettoyage, mapping, seuils)
terminology/         mock synthétique minimaliste (< 1 Mo) dans Git, ConceptMaps, ValueSets, script de téléchargement Athena
ig/                  sources FSH du guide d'implémentation Togo
tests/               miroir de src/
docs/fr, docs/en     documentation bilingue

Ne pas créer de nouveau dossier de premier niveau sans accord humain.

## 5. Conventions de code

- Annotations de types partout. Fonctions courtes, une responsabilité.
- Chaque règle de nettoyage ou de mapping est un module indépendant,
  déclaré dans la configuration YAML, qui journalise ses modifications.
- Les seuils, listes de valeurs sentinelles et chemins sont dans la
  configuration, jamais en dur.
- Pas de logique métier dans la CLI : elle appelle des fonctions.
- Pas d'effet de bord à l'import. Pas de chemin absolu.
- Gestion d'erreur explicite : un enregistrement invalide est mis en
  quarantaine, il ne fait pas planter le lot.
- Pas de print : utiliser le journal structuré.
- ruff doit passer sans avertissement.

## 6. Zones à validation humaine obligatoire

L'agent peut proposer, jamais valider. Toute modification touchant
ces points exige le trailer "Validé-par" et ne se fusionne pas sans
relecture humaine :

1. Correspondances terminologiques cliniques (CIM-10, SNOMED CT,
   LOINC, ATC) et leur statut "validé".
2. Seuils de rapprochement de patients (fusion automatique, revue,
   distinct) et règles de blocage.
3. Règles de pseudonymisation et de généralisation des données.
4. Interprétation des dates ambiguës et des âges approximatifs.
5. Conversions d'unités cliniques.
6. Référentiel des formations sanitaires et hiérarchie administrative.
7. Profils FHIR du guide d'implémentation (cardinalités, liaisons).
8. Toute note de conformité légale.

Si l'agent n'est pas sûr d'une correspondance ou d'une règle clinique,
il écrit "à revoir" et explique pourquoi. Il n'invente jamais un code.

## 7. Tests

- Tests d'abord quand c'est possible : écrire le test qui échoue,
  puis le code.
- Chaque règle de nettoyage a au moins un test nominal, un test de cas
  limite et un test d'idempotence.
- Tests de déterminisme : deux exécutions avec la même graine donnent
  des sorties identiques.
- Aucun test ne dépend du réseau ni de données hors dépôt.
  Utiliser de petits jeux de test versionnés (moins de 1 Mo).
- Une tâche n'est pas terminée tant que pytest et ruff ne passent pas.
  L'agent exécute les tests et rapporte le résultat réel, sans
  l'inventer ni l'estimer.

## 8. Données et sécurité

- Aucun secret, jeton ou mot de passe dans le dépôt. Variables
  d'environnement et fichier .env.example sans valeurs réelles.
- Ne jamais committer de données générées volumineuses. Seuls les
  scripts, graines et petits jeux de test sont versionnés.
- Toute donnée de sortie destinée à l'IA est pseudonymisée. Un test
  doit prouver qu'aucun identifiant direct ne sort.
- Séparer variables cibles et variables explicatives dans les exports
  pour éviter la fuite de données.
- Les URL, schémas et licences externes ne sont pas supposés : si
  l'agent ne peut pas vérifier une information (version, licence,
  nom officiel d'une structure sanitaire), il l'écrit explicitement
  comme "non vérifié".

## 9. Méthode de travail pour chaque tâche

1. Relire l'étape de la roadmap et ses critères de validation.
2. Annoncer en quelques lignes ce qui sera fait et les fichiers touchés.
3. Si la demande est ambiguë, poser une question précise avant de coder.
4. Faire le plus petit changement qui satisfait le critère.
5. Écrire ou mettre à jour les tests.
6. Exécuter tests et lint, rapporter les résultats réels.
7. Proposer le message de commit selon la convention.
8. Lister ce qui reste à valider par un humain.

Rester dans le périmètre de la tâche : pas de refactoring opportuniste,
pas de changement de dépendance ou de structure non demandé.

## 10. Interdits

- Modifier data/raw ou data/truth sans demande explicite.
- Utiliser des données ou des noms de patients réels.
- Contourner un test, une validation ou un hook en les désactivant.
- Marquer une correspondance clinique comme "validée".
- Réécrire l'historique de main, pousser en force.
- Ajouter du code mort, des TODO sans issue associée, ou des
  commentaires qui paraphrasent le code.
- Affirmer qu'une validation FHIR ou un test a réussi sans l'avoir
  exécuté.

## 11. Définition de "terminé"

Une tâche est terminée quand :
- le critère de validation de l'étape est atteint et mesuré ;
- les tests et le lint passent ;
- la traçabilité et l'idempotence sont préservées ;
- les points à validation humaine sont listés ;
- la documentation FR est mise à jour (EN si l'étape est publiée) ;
- le message de commit respecte la convention.

## 12. Format des rapports de l'agent

À la fin de chaque tâche, répondre avec :
- Résumé de ce qui a été fait (3 à 5 lignes).
- Fichiers modifiés.
- Résultats réels des tests et du lint.
- Hypothèses faites et informations non vérifiées.
- Points à valider par un humain.
- Message de commit proposé.

## 13. Travail en équipe multi-agents (/teamwork)

### 13.1 Principe

Plusieurs agents peuvent travailler en parallèle, mais :
- un seul agent est propriétaire d'un fichier ou d'un module à un
  instant donné ;
- aucun agent ne valide son propre travail ;
- l'humain reste le seul décideur sur les zones de la section 6.

### 13.2 Rôles

COORDINATEUR
- Lit la roadmap, découpe l'étape en tâches étroites et vérifiables,
  chacune avec : étape, fichiers autorisés, critère de validation,
  dépendances.
- Assigne les tâches, tient le journal de bord, arbitre les conflits.
- N'écrit pas de code métier.

IMPLÉMENTEUR
- Écrit le code d'une tâche, dans les fichiers qui lui sont assignés
  uniquement.
- Travaille sur sa propre branche (etape-<N>-<sujet>-<agent>).
- Ne touche ni aux tests écrits par le TESTEUR, ni aux fichiers
  d'un autre implémenteur.

TESTEUR
- Écrit les tests avant l'implémentation : nominal, cas limite,
  idempotence, déterminisme.
- Ne modifie jamais le code source qu'il teste.
- Si un test semble faux, il le signale au COORDINATEUR au lieu de
  l'affaiblir.

RELECTEUR
- Revue indépendante : respect des principes de la section 2, des
  conventions, de la traçabilité, de la sécurité.
- Exécute lui-même les tests et le lint, et ne se fie pas au rapport
  de l'implémenteur.
- Peut refuser une tâche. Ne corrige pas : il renvoie avec motifs.

SPÉCIALISTE DOMAINE (appelé à la demande)
- FHIR/IG : profils FSH, validation HL7.
- Terminologie : ConceptMaps, tables de correspondance (propose
  seulement, statut "à revoir").
- OMOP : ETL, DQD.
- Données/Qualité : dégradation, profilage, rapprochement.
Il intervient en conseil ou en implémentation, selon l'assignation.

### 13.3 Cycle d'une tâche

1. Le COORDINATEUR rédige la fiche de tâche.
2. Le TESTEUR écrit les tests (ils échouent).
3. L'IMPLÉMENTEUR code jusqu'au vert.
4. Le RELECTEUR vérifie de façon indépendante.
5. Si zone sensible (section 6) : arrêt, demande de validation humaine.
6. Le COORDINATEUR consigne le résultat et propose la fusion.
Une tâche refusée retourne à l'étape 3 avec les motifs du RELECTEUR.

### 13.4 Fiche de tâche (format obligatoire)

- Identifiant : T-<étape>-<numéro>
- Étape de la roadmap et critère de validation visé
- Fichiers autorisés en écriture (liste fermée)
- Fichiers en lecture seule utiles
- Dépendances (tâches à terminer avant)
- Zone sensible : oui/non (et laquelle)
- Définition de terminé (section 11)

### 13.5 Parallélisme : règles de sécurité

- Deux tâches en parallèle ne peuvent pas avoir de fichiers autorisés
  en commun.
- Les fichiers partagés (pyproject.toml, config YAML globale,
  modèle canonique, CLI, docker-compose) ont un seul propriétaire :
  le COORDINATEUR désigne qui, tâche par tâche.
- Les schémas (modèle canonique, URI, formats de couches) sont
  figés avant que plusieurs agents en dépendent. Toute modification
  de schéma est une tâche à part, séquentielle, avec BREAKING CHANGE
  si besoin.
- Les étapes de la roadmap restent séquentielles. Le parallélisme
  se fait à l'intérieur d'une étape, entre règles ou modules
  indépendants (par ex. une règle de nettoyage par agent).

### 13.6 Mémoire et continuité (travaux de plusieurs jours)

Les agents ne se souviennent pas d'une session à l'autre. L'état vit
dans le dépôt :
Frontière stricte des répertoires de gouvernance :
- `.agents/teamwork/` : Répertoire interne et transitoire réservé à l'orchestration multi-agents (briefings, plans d'exécution, handoffs éphémères). N'est pas committé dans le dépôt git pérenne.
- `docs/journal/` : Registre officiel et immuable de gouvernance du projet, versionné dans Git :
  * `docs/journal/JOURNAL.md` : journal chronologique append-only des travaux réalisés.
  * `docs/journal/DECISIONS.md` : registre des décisions d'architecture formalisées (D-01 à D-09).
  * `docs/journal/A_VALIDER.md` : registre d'arbitrage pour les cas cliniques et administratifs nécessitant une revue humaine.
Tout agent lit ces trois fichiers au démarrage et met à jour le
journal en fin de tâche.

### 13.7 Interdits spécifiques à l'équipe

- Un agent ne valide pas, ne fusionne pas et ne marque pas "terminé"
  son propre travail.
- Un agent ne réécrit pas le travail d'un autre sans passer par le
  COORDINATEUR.
- Un RELECTEUR et un IMPLÉMENTEUR ne sont jamais le même agent
  sur la même tâche.
- Aucun agent ne déclare un résultat de test, de validation FHIR ou
  de DQD sans l'avoir exécuté dans cette session et en joindre la
  sortie.
- Aucun refactoring transversal (dizaines de fichiers) sans tâche
  dédiée, plan écrit et accord humain.
- Les chiffres de métriques (taux de récupération, % de concept 0)
  sont produits par du code reproductible, jamais écrits à la main
  ni estimés par un agent.

### 13.8 Escalade vers l'humain

Arrêt et demande de décision si : conflit entre agents, critère de
validation inatteignable, information non vérifiable (licence,
nom officiel, version), zone sensible, ou tâche qui dépasse les
fichiers autorisés.