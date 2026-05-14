# Données — accès et confidentialité

Les fichiers bruts contiennent des **données personnelles identifiantes** (numéros de téléphone, noms et prénoms) et ne sont pas redistribués dans ce dépôt.


| Fichier | Vague | Description |
|---|---|---|
| `Impact_COVID_en_milieu_scolaire___Questionnaire_Ménage_2021.csv` | 2021 | 1 005 ménages |
| `Impact_COVID_en_milieu_scolaire___Questionnaire_Ménage_2022.csv` | 2022 | 1 099 lignes (980 ménages uniques après déduplication) |
| `Impact_COVID_en_milieu_scolaire___Questionnaire_Ménage_2021.xlsx` | 2021 | XLSForm (dictionnaire des variables) |
| `Impact_COVID_en_milieu_scolaire___Questionnaire_Ménage_2022.xlsx` | 2022 | XLSForm |

## Accès

Contacter le **Centre de Recherche sur le Développement Économique et Social (CRDES)**, Dakar.
Personne référente : Justin Chery — *cheryjustin@gmail.com*.

## Reproduction

Une fois les quatre fichiers déposés dans `data/raw/`, lancer le pipeline (à venir : `python/00_prepare_data.py`) qui produit les dérivés anonymisés dans `data/processed/`.