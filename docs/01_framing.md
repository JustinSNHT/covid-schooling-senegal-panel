# Phase 0 — Cadrage du projet

## Titre
*Trajectoires de scolarisation post-COVID au Sénégal : panel de ménages 2021-2022*

## Problématique

La fermeture prolongée des écoles sénégalaises entre mars et juin 2020, suivie d'une reprise progressive marquée par des conditions sanitaires contraignantes, a perturbé les parcours scolaires d'une cohorte entière d'enfants. Ce projet exploite un panel de 969 ménages enquêtés en 2021 puis ré-interrogés en 2022, contenant l'historique scolaire rétrospectif pré-COVID (2018-19) et le suivi prospectif (2021-22), pour caractériser **(i)** l'ampleur de la disruption, **(ii)** le rythme de la reprise, et **(iii)** l'hétérogénéité de cette reprise selon le sexe de l'enfant, le milieu et les caractéristiques du ménage.

## Données

- **Source** : Centre de Recherche sur le Développement Économique et Social (CRDES), Dakar.
- **Design** : enquête CAPI (SurveyCTO), deux vagues sur les mêmes ménages.
- **Vague 1** : avril 2021 — 1 005 ménages, 1 362 variables.
- **Vague 2** : juin-juillet 2022 — 980 ménages uniques après déduplication (sur 1 099 soumissions brutes), 789 variables.
- **Clé panel** : numéro de téléphone (`LS11`/`LS12` en 2021 ↔ `phone1_ld`/`phone2_ld` en 2022).
- **Taux de rétention** : 96,4 % (969 ménages appariés exactement).
- **Unité d'observation analytique** : enfant-vague.

## Modules principaux

| 2021 | 2022 | Contenu |
|---|---|---|
| LS01-LS12 | ls_*, phone*_ld | Caractéristiques chef de ménage |
| ST04, ST05 | commune | Localisation (région, commune) |
| SC01_* | cfr01-cfr13 | Scolarité année courante |
| SC02_* | — | Scolarité 2019-20 (rétrospectif) |
| SC03_* | — | Scolarité 2018-19 (rétrospectif, référence pré-COVID) |
| SC04_* | cfr (intégré) | École coranique |
| — | nec_* | Nouveaux enfants en 2022 |
| — | prec_* | Préscolaire |
| EM, EMP | em, emp | Emploi du chef de ménage |
| VACC | — | Vaccination COVID |
| CM | cm | Composition du ménage (50 slots) |

## Questions analytiques

1. **Trajectoire agrégée 2018-19 → 2021-22.** Comment ont évolué les taux de scolarisation, de fréquentation coranique et de recours aux cours particuliers sur quatre années scolaires consécutives, dont l'année pivot 2019-20 ?
2. **Hétérogénéité par genre et milieu.** Filles vs garçons, urbain vs rural, régions : la dégradation 2019-20 et la reprise 2020-22 sont-elles symétriques entre groupes ? Y a-t-il creusement d'inégalités ?
3. **Suivi intra-ménage 2021→2022.** Conditionnellement au ménage, quels enfants sont sortis du système entre les deux vagues ? Quelles caractéristiques observées en 2021 (âge, sexe, classe, type d'école, motifs de non-scolarisation) prédisent le décrochage en 2022 ?
4. **Motifs déclarés de non-scolarisation.** Distribution des raisons invoquées par les ménages pour les enfants non scolarisés, et évolution entre 2021 et 2022 (effet COVID résiduel vs. raisons structurelles).

## Public cible du dashboard

Bailleurs et ONG intervenant dans l'éducation en Afrique de l'Ouest (Jacobs Foundation, J-PAL, GPE, AFD, partenaires de SOS ÉCOLE). Focus : **équité et ciblage des interventions**.

## Périmètre méthodologique

- Échantillon panel = 969 ménages × enfants confirmés (module `cfr`).
- Analyses initiales **non pondérées** (plan de sondage à intégrer en seconde phase si pertinent).
- Statistiques : descriptives + tests, régressions linéaires/logit avec effets fixes ménage pour les questions intra-ménage.
- Traitement des doublons 2022 : conservation de la soumission la plus ancienne par `id`.
- Traitement des doublons de téléphone intra-vague (1 en 2021, 7 en 2022) : à instruire au cas par cas dans le notebook de préparation.

## Trois insights cibles pour le dashboard

À confirmer après l'EDA, mais hypothèse de travail :
1. **Recovery rate inégal selon le genre** : filles vs garçons.
2. **Concentration géographique du décrochage** : cartographie par région/commune.
3. **Profil-type du ménage à risque** : caractéristiques observables en 2021 qui prédisent un décrochage en 2022.