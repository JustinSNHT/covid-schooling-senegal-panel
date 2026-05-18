# COVID-19 et scolarisation au Sénégal — Panel ménages 2021-2022

Analyse reproductible de l'impact de la pandémie de COVID-19 sur les trajectoires scolaires des enfants au Sénégal, à partir d'un **panel de 969 ménages** enquêtés en 2021 puis ré-interrogés en 2022. Le projet décline la même analyse selon trois outils — **Python**, **R** et **Power BI** — à partir d'une source de données unique.

---

## Contexte et objectif

La fermeture prolongée des écoles sénégalaises entre mars et juin 2020, suivie d'une réouverture progressive sous contraintes sanitaires, a perturbé les parcours scolaires d'une cohorte entière d'enfants. Ce projet exploite un panel à deux vagues — contenant l'historique scolaire rétrospectif pré-COVID (2018-19) et le suivi prospectif (2021-22) — pour répondre à quatre questions :

1. La baisse de scolarisation observée entre 2021 et 2022 est-elle réelle une fois neutralisé le vieillissement de cohorte ?
2. Cette baisse est-elle équitable selon le genre, le milieu et la région ?
3. Quels enfants décrochent entre les deux vagues, et quels facteurs le prédisent ?
4. Comment évoluent les motifs déclarés de non-scolarisation ?

Le dashboard cible un public de **bailleurs et d'ONG du secteur éducatif**, avec un accent sur l'équité et le ciblage des interventions.

## Résultats clés

### 1. La baisse de scolarisation est réelle, et concentrée sur le primaire

Entre les vagues 2021 et 2022, la scolarisation des enfants suivis chute de **−8 points** en données brutes. Après contrôle de l'âge par effets fixes, l'effet net reste de **−6,5 points** (p < 0,001) : la baisse n'est donc pas un simple artefact du vieillissement de la cohorte. Elle est **concentrée sur les âges du primaire** (−11,7 points chez les 6-9 ans, −8,3 points chez les 10-12 ans), à rebours de l'intuition qui voudrait que les adolescents soient les plus exposés.

### 2. Une fracture territoriale marquée

L'érosion scolaire n'est pas uniforme. Elle frappe sévèrement les **régions rurales orientales** — Tambacounda, Diourbel et Fatick perdent de 10 à 19 points de scolarisation (effets ajustés pour l'âge, statistiquement significatifs) — tandis que les grands centres urbains (Dakar, Thiès, Saint-Louis) restent quasi stables. La pandémie a creusé une inégalité géographique préexistante.

### 3. Le décrochage tient au désintérêt et aux contraintes économiques, pas au COVID

Parmi les enfants scolarisés en 2021, **5,2 % décrochent** l'année suivante. Les motifs déclarés sont dominés par le **désintérêt scolaire** (≈50 % des cas) et les **difficultés financières** (≈14 %) ; le COVID n'est cité que dans moins de 1 % des cas. Le décrochage est par ailleurs faiblement prédit par les caractéristiques observables (âge, sexe, région) — il reste largement idiosyncratique.

> **Note d'honnêteté analytique** : la baisse apparaît légèrement plus forte chez les garçons (−7,6 pp) que chez les filles (−5,3 pp), mais cet écart n'est **pas statistiquement significatif** (p = 0,16) sur cet échantillon.

## Aperçu du dashboard

Le dashboard Power BI restitue ces résultats en trois pages interactives.

![Vue d'ensemble](powerbi/screenshots/page1_vue_ensemble.png)
![Équité et géographie](powerbi/screenshots/page2_equite.png)
![Décrochage et motifs](powerbi/screenshots/page3_decrochage.png)

## Données

Les données proviennent d'enquêtes ménages conduites par le **Centre de Recherche sur le Développement Économique et Social (CRDES)**, Dakar :

- **Vague 1** (avril 2021) : 1 005 ménages, 1 362 variables
- **Vague 2** (juin-juillet 2022) : 980 ménages uniques après déduplication, 789 variables
- **Clé d'appariement** : numéro de téléphone — taux de rétention du panel de **96,4 %**

Les fichiers bruts contiennent des données personnelles (téléphones, noms) et **ne sont pas inclus dans ce dépôt**. Voir [`data/README.md`](data/README.md) pour les conditions d'accès. Seuls les **agrégats anonymisés** nécessaires au dashboard sont versionnés.

## Méthodologie

- **Unité d'observation** : enfant × vague ; échantillon panel = enfants observés aux deux vagues.
- **Construction du panel** : appariement exact par téléphone, identifiant ménage anonymisé (hachage SHA-256 salé), reshape des données enfants du format large vers le format long.
- **Estimation** : modèle linéaire de probabilité (LPM) avec effets fixes d'âge pour les comparaisons inter-vagues ; écarts-types clusterisés au niveau du ménage.
- **Série temporelle 2018-2022** : reconstruite en combinant les questions rétrospectives de la vague 2021 et le suivi de la vague 2022.

**Limites** : analyses non pondérées (plan de sondage non appliqué en première approche) ; les points 2018-19 et 2019-20 reposent sur des questions rétrospectives sujettes à biais de rappel ; les caractéristiques démographiques de la vague 2022 sont reportées depuis 2021.

## Structure du dépôt

```
covid-schooling-senegal-panel/
├── data/
│   ├── raw/                      Données brutes (non versionnées — PII)
│   └── processed/                Agrégats anonymisés + dictionnaire
├── python/
│   ├── 00_prepare_data.py        Pipeline de préparation (panel, anonymisation)
│   ├── 01_eda.ipynb              Exploration des données
│   ├── 02_analysis.ipynb         Analyse économétrique + agrégats
│   ├── 03_export_dashboard_csv.py  Export des données pour Power BI
│   └── requirements.txt
├── r/
│   ├── install_packages.R        Installation des dépendances R
│   ├── 01_analysis.R             Réplication économétrique (fixest)
│   └── 02_figures.R              Figures ggplot2
├── powerbi/
│   ├── data/                     CSV alimentant le dashboard
│   ├── dashboard.pbix            Dashboard Power BI (3 pages)
│   ├── theme.json                Thème visuel
│   ├── GUIDE_CONSTRUCTION.md      Guide de construction du dashboard
│   └── screenshots/              Captures des pages
├── docs/
│   ├── 01_framing.md             Document de cadrage (Phase 0)
│   ├── figures/                  Figures exportées (Python + R)
│   └── tableau_regressions.md    Tableau de régression formaté
└── README.md
```

## Reproduire l'analyse

### Prérequis

- Python ≥ 3.10, R ≥ 4.2, Power BI Desktop (pour le dashboard)
- Accès autorisé aux données brutes du CRDES, déposées dans `data/raw/`

### Étapes

```bash
# 1. Environnement Python
python -m venv .venv
source .venv/Scripts/activate        # Windows ; sur Linux/macOS : .venv/bin/activate
pip install -r python/requirements.txt
echo 'ANON_SALT=votre-sel-stable' > .env

# 2. Préparation des données + analyse
python python/00_prepare_data.py     # produit data/processed/*.parquet
jupyter nbconvert --execute --to notebook --inplace python/02_analysis.ipynb

# 3. Réplication R
Rscript r/install_packages.R
Rscript r/01_analysis.R
Rscript r/02_figures.R

# 4. Données du dashboard
python python/03_export_dashboard_csv.py
```

Le dashboard se construit ensuite dans Power BI Desktop en suivant [`powerbi/GUIDE_CONSTRUCTION.md`](powerbi/GUIDE_CONSTRUCTION.md).

## Une source unique, trois restitutions

Le pipeline `00_prepare_data.py` est l'**unique source de vérité** : il produit des agrégats que Python, R et Power BI consomment tous les trois. Les trois livrables ne sont pas des analyses séparées susceptibles de diverger, mais trois lectures cohérentes d'une même donnée — les estimations R et Python coïncident à l'arrondi près, par construction.

## Stack technique

`pandas` · `statsmodels` · `matplotlib` · `seaborn` · `Jupyter` — `fixest` · `modelsummary` · `ggplot2` · `arrow` — `Power BI` · `DAX` · Parquet

## Auteur

**Justin Chery** — Associate Researcher & Evaluation Specialist, CRDES, Dakar.
Doctorant en Économie, Université Gaston Berger.

## Licence

Les données ne sont pas redistribuées ; contacter le CRDES pour les conditions d'accès.