# COVID-19 et scolarisation au Sénégal — Panel ménages 2021-2022

Analyse reproductible de l'impact de la pandémie de COVID-19 sur les trajectoires scolaires des enfants au Sénégal, à partir d'un panel de 969 ménages enquêtés en 2021 puis ré-interrogés en 2022.

## 🚧 Statut

Projet en construction. Phase de cadrage terminée — voir [`docs/01_framing.md`](docs/01_framing.md).

## Trois angles, mêmes données

| Outil | Dossier | Objectif |
|---|---|---|
| **Python** | `python/` | Exploration, nettoyage, modélisation |
| **R** | `r/` | Estimations économétriques, tableaux publication-ready |
| **Power BI** | `powerbi/` | Dashboard interactif pour bailleurs et ONG |

## Données

Les deux fichiers bruts proviennent d'enquêtes ménages conduites par le **Centre de Recherche sur le Développement Économique et Social (CRDES)**, Dakar. Ils contiennent des données personnelles (téléphones, noms) et **ne sont pas inclus dans ce dépôt**. Voir [`data/README.md`](data/README.md) pour les conditions d'accès.

## Structure du dépôt
covid-schooling-senegal-panel/
├── data/
│   ├── raw/          ← non commité (PII)
│   └── processed/    ← dérivés anonymisés (selectivement commités)
├── python/           ← notebooks Jupyter + scripts
├── r/                ← scripts R + rapports Rmd
├── powerbi/          ← dashboard .pbix + captures
└── docs/             ← documentation méthodologique

## Auteur

**Justin Chery** — Associate Researcher, CRDES, Dakar.
PhD candidate en Économie, Université Gaston Berger.

## Licence

Données : non redistribuées ; contacter le CRDES pour accès.