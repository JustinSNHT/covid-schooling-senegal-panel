# =============================================================================
# 01_analysis.R
# =============================================================================
# Réplication R de l'analyse panel COVID-Scolarisation Sénégal.
#
# Ce script reproduit l'analyse de python/02_analysis.ipynb en exploitant les
# forces propres de R : estimation à effets fixes rapide (fixest) et tableaux
# de régression publication-ready (modelsummary).
#
# Les DONNÉES SONT IDENTIQUES à celles utilisées côté Python : on lit les mêmes
# fichiers parquet produits par python/00_prepare_data.py. Cela garantit que les
# deux analyses sont strictement comparables.
#
# Entrées : data/processed/enfants_panel.parquet
# Sorties : docs/tableau_regressions.md  (tableau de régression formaté)
#           console : estimations clés
#
# Usage : Rscript r/01_analysis.R   (ou source() depuis RStudio)
# =============================================================================

suppressPackageStartupMessages({
  library(arrow)         # lecture des fichiers parquet
  library(dplyr)
  library(tidyr)
  library(fixest)        # estimation à effets fixes (feols)
  library(modelsummary)  # tableaux de régression
})

# ----- Chemins ---------------------------------------------------------------
# Détecte la racine du projet, que le script soit lancé depuis la racine ou r/
here_root <- if (basename(getwd()) == "r") dirname(getwd()) else getwd()
proc_dir  <- file.path(here_root, "data", "processed")
docs_dir  <- file.path(here_root, "docs")
dir.create(docs_dir, showWarnings = FALSE, recursive = TRUE)

cat("Racine projet :", here_root, "\n")

# ----- Chargement et préparation ---------------------------------------------
enfants <- read_parquet(file.path(proc_dir, "enfants_panel.parquet"))

# Échantillon analytique : enfants observés aux deux vagues
panel <- enfants %>%
  filter(statut_enfant == "panel_present") %>%
  mutate(
    scolarise_bin = if_else(scolarise == "Oui", 1, 0, missing = NA_real_),
    femme         = if_else(sexe_enfant == "Femme", 1, 0, missing = NA_real_),
    wave_2022     = as.integer(wave == 2022)
  )

cat(sprintf("Échantillon panel : %d obs, %d ménages\n",
            nrow(panel), n_distinct(panel$hh_id)))

# =============================================================================
# Question 1 — La baisse 2021->2022 est-elle réelle, ajustée pour l'âge ?
# =============================================================================
ech1 <- panel %>%
  filter(!is.na(scolarise_bin), !is.na(age_enfant)) %>%
  mutate(age_int = as.integer(age_enfant)) %>%
  filter(age_int >= 3, age_int <= 22)

# Modèle 1a : brut (sans contrôle d'âge), SE clusterisés ménage
m1a <- feols(scolarise_bin ~ wave_2022, data = ech1, cluster = ~hh_id)

# Modèle 1b : effets fixes par année d'âge
m1b <- feols(scolarise_bin ~ wave_2022 | age_int, data = ech1, cluster = ~hh_id)

cat("\n=== Q1 — Effet de la vague 2022 ===\n")
cat(sprintf("  Brut          : %+.2f pp (SE %.2f)\n",
            coef(m1a)["wave_2022"] * 100, se(m1a)["wave_2022"] * 100))
cat(sprintf("  EF âge        : %+.2f pp (SE %.2f)\n",
            coef(m1b)["wave_2022"] * 100, se(m1b)["wave_2022"] * 100))

# =============================================================================
# Question 2 — Hétérogénéité par genre et région
# =============================================================================
ech2 <- ech1 %>% filter(!is.na(femme))

# Interaction genre x vague (avec effets fixes âge)
m2 <- feols(scolarise_bin ~ wave_2022 * femme | age_int,
            data = ech2, cluster = ~hh_id)

cat("\n=== Q2 — Interaction genre x vague ===\n")
cat(sprintf("  Effet wave 2022 (garçons)        : %+.2f pp\n",
            coef(m2)["wave_2022"] * 100))
cat(sprintf("  Terme interaction (wave x femme) : %+.2f pp (p = %.3f)\n",
            coef(m2)["wave_2022:femme"] * 100,
            pvalue(m2)["wave_2022:femme"]))

# Effet par région : feols séparé par région (régions avec >= 50 obs)
regions_ok <- ech1 %>%
  count(region) %>%
  filter(n >= 50, !is.na(region)) %>%
  pull(region)

reg_effets <- lapply(regions_ok, function(r) {
  sub <- ech1 %>% filter(region == r)
  m <- feols(scolarise_bin ~ wave_2022 | age_int, data = sub, cluster = ~hh_id)
  data.frame(
    region   = r,
    n        = nobs(m),
    effet_pp = coef(m)["wave_2022"] * 100,
    se_pp    = se(m)["wave_2022"] * 100,
    p_value  = pvalue(m)["wave_2022"]
  )
}) %>% bind_rows() %>% arrange(effet_pp)

cat("\n=== Q2 — Effet par région (ajusté pour l'âge) ===\n")
print(reg_effets, row.names = FALSE, digits = 3)

# =============================================================================
# Question 3 — Modélisation du décrochage 2021->2022
# =============================================================================
# Construction : 1 ligne par enfant, pivot des deux vagues
wide <- panel %>%
  filter(!is.na(scolarise_bin)) %>%
  select(hh_id, enfant_slot, wave, scolarise_bin) %>%
  pivot_wider(names_from = wave, values_from = scolarise_bin,
              names_prefix = "scol_") %>%
  filter(!is.na(scol_2021), !is.na(scol_2022)) %>%
  mutate(decroche = as.integer(scol_2021 == 1 & scol_2022 == 0)) %>%
  filter(scol_2021 == 1)   # uniquement enfants scolarisés en 2021

# Covariables observées en 2021
covars <- panel %>%
  filter(wave == 2021) %>%
  select(hh_id, enfant_slot, age_enfant, femme, region,
         niveau_educ_cm, type_ecole)

ana <- wide %>%
  left_join(covars, by = c("hh_id", "enfant_slot")) %>%
  filter(!is.na(age_enfant), !is.na(femme), !is.na(region))

cat(sprintf("\n=== Q3 — Modèle de décrochage ===\n"))
cat(sprintf("  Enfants scolarisés en 2021 : %d\n", nrow(wide)))
cat(sprintf("  Taux de décrochage         : %.1f %%\n", mean(wide$decroche) * 100))

# LPM de décrochage : âge (quadratique) + sexe, FE région/éduc/type école
m3 <- feols(decroche ~ age_enfant + I(age_enfant^2) + femme |
              region + niveau_educ_cm + type_ecole,
            data = ana, cluster = ~hh_id)

cat("\n  Coefficients principaux :\n")
print(coeftable(m3), digits = 4)

# =============================================================================
# Question 4 — Évolution des motifs de non-scolarisation
# =============================================================================
motifs <- enfants %>%
  filter(!is.na(raison_non_scol)) %>%
  count(wave, raison_non_scol) %>%
  group_by(wave) %>%
  mutate(part = round(n / sum(n) * 100, 1)) %>%
  ungroup()

motifs_wide <- motifs %>%
  select(wave, raison_non_scol, part) %>%
  pivot_wider(names_from = wave, values_from = part, names_prefix = "an_") %>%
  mutate(delta_pp = round(an_2022 - an_2021, 1)) %>%
  arrange(desc(an_2021))

cat("\n=== Q4 — Composition des motifs (% du total) ===\n")
print(as.data.frame(motifs_wide), row.names = FALSE)

# Test du chi-deux d'indépendance vague x motif
tab <- enfants %>%
  filter(!is.na(raison_non_scol)) %>%
  count(wave, raison_non_scol) %>%
  pivot_wider(names_from = wave, values_from = n, values_fill = 0) %>%
  select(-raison_non_scol) %>%
  as.matrix()
chi <- chisq.test(tab)
cat(sprintf("\n  Test chi2 (vague x motif) : X2 = %.1f, df = %d, p = %.4f\n",
            chi$statistic, chi$parameter, chi$p.value))

# =============================================================================
# Export du tableau de régression formaté (modelsummary)
# =============================================================================
modeles <- list(
  "Q1 brut"        = m1a,
  "Q1 EF âge"      = m1b,
  "Q2 interaction" = m2,
  "Q3 décrochage"  = m3
)

# Tableau markdown (rendu directement sur GitHub)
modelsummary(
  modeles,
  output    = file.path(docs_dir, "tableau_regressions.md"),
  stars     = c('*' = .05, '**' = .01, '***' = .001),
  gof_omit  = "AIC|BIC|Log.Lik|RMSE",
  title     = "Régressions — COVID et scolarisation au Sénégal (panel 2021-2022)",
  notes     = "SE clusterisés au niveau du ménage entre parenthèses."
)
cat(sprintf("\nTableau de régression exporté : %s\n",
            file.path("docs", "tableau_regressions.md")))

cat("\n=== ANALYSE R TERMINÉE ===\n")
