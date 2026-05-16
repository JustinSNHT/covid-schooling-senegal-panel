# =============================================================================
# 02_figures.R
# =============================================================================
# Production des figures de l'analyse avec ggplot2.
#
# Ce script lit les mêmes données traitées que Python et que 01_analysis.R,
# et produit des figures publication-ready. L'objectif portfolio : montrer la
# qualité graphique supérieure de ggplot2 pour les livrables visuels.
#
# Entrées : data/processed/enfants_panel.parquet
#           data/processed/agg_effets_regionaux.parquet
#           data/processed/agg_serie_4ans.parquet
#           data/processed/agg_motifs.parquet
# Sorties : docs/figures/*_R.png
#
# Usage : Rscript r/02_figures.R
# =============================================================================

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(scales)
})

# ----- Chemins ---------------------------------------------------------------
here_root <- if (basename(getwd()) == "r") dirname(getwd()) else getwd()
proc_dir  <- file.path(here_root, "data", "processed")
figs_dir  <- file.path(here_root, "docs", "figures")
dir.create(figs_dir, showWarnings = FALSE, recursive = TRUE)

# ----- Thème graphique commun ------------------------------------------------
theme_covid <- function() {
  theme_minimal(base_size = 12) +
    theme(
      plot.title       = element_text(face = "bold", size = 13),
      plot.subtitle    = element_text(color = "grey40", size = 10),
      plot.caption     = element_text(color = "grey50", size = 8, hjust = 0),
      panel.grid.minor = element_blank(),
      legend.position  = "top",
      legend.title     = element_text(size = 10)
    )
}
col_vagues <- c("2021" = "#1f77b4", "2022" = "#d62728")

# ----- Chargement ------------------------------------------------------------
enfants <- read_parquet(file.path(proc_dir, "enfants_panel.parquet"))
panel <- enfants %>%
  filter(statut_enfant == "panel_present") %>%
  mutate(scolarise_bin = if_else(scolarise == "Oui", 1, 0, missing = NA_real_))

# =============================================================================
# Figure 1 — Taux de scolarisation par âge x vague (avec IC normal 95%)
# =============================================================================
fig1_data <- panel %>%
  filter(!is.na(scolarise_bin), !is.na(age_enfant)) %>%
  mutate(age = as.integer(age_enfant)) %>%
  filter(age >= 3, age <= 22) %>%
  group_by(age, wave) %>%
  summarise(
    n    = n(),
    taux = mean(scolarise_bin),
    .groups = "drop"
  ) %>%
  mutate(
    se = sqrt(taux * (1 - taux) / n),
    lo = pmax(0, taux - 1.96 * se),
    hi = pmin(1, taux + 1.96 * se),
    wave = factor(wave)
  )

fig1 <- ggplot(fig1_data, aes(age, taux, color = wave, fill = wave)) +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.15, color = NA) +
  geom_line(linewidth = 1) +
  geom_point(size = 2) +
  scale_y_continuous(labels = percent_format(accuracy = 1), limits = c(0, 1.02)) +
  scale_x_continuous(breaks = seq(3, 22, 2)) +
  scale_color_manual(values = col_vagues) +
  scale_fill_manual(values = col_vagues) +
  labs(
    title    = "Scolarisation par âge et par vague",
    subtitle = "Enfants suivis aux deux vagues — bandes : IC 95 %",
    x = "Âge de l'enfant", y = "Taux de scolarisation",
    color = "Vague", fill = "Vague",
    caption = "Source : panel ménages COVID-scolarisation Sénégal, 2021-2022."
  ) +
  theme_covid()

ggsave(file.path(figs_dir, "fig1_scolarisation_age_wave_R.png"),
       fig1, width = 8, height = 5, dpi = 200)
cat("Figure 1 sauvegardée\n")

# =============================================================================
# Figure 2 — Série temporelle 2018-2022 par sexe
# =============================================================================
serie <- read_parquet(file.path(proc_dir, "agg_serie_4ans.parquet")) %>%
  mutate(taux_p = taux / 100)

fig2 <- ggplot(serie, aes(annee, taux_p, color = sexe_enfant, group = sexe_enfant)) +
  geom_line(linewidth = 1) +
  geom_point(size = 3) +
  scale_y_continuous(labels = percent_format(accuracy = 1), limits = c(0.5, 1)) +
  scale_color_manual(values = c("Femme" = "#9467bd", "Homme" = "#2ca02c")) +
  labs(
    title    = "Trajectoire de scolarisation 2018-2022",
    subtitle = "Reconstruite à partir des questions rétrospectives (vague 2021) et du suivi (vague 2022)",
    x = NULL, y = "Taux de scolarisation", color = "Sexe",
    caption = "Note : 2018-19 et 2019-20 issus de questions rétrospectives, sujettes à biais de rappel."
  ) +
  theme_covid()

ggsave(file.path(figs_dir, "fig2_serie_4ans_R.png"),
       fig2, width = 8, height = 5, dpi = 200)
cat("Figure 2 sauvegardée\n")

# =============================================================================
# Figure 3 — Hétérogénéité régionale de la baisse 2021->2022
# =============================================================================
reg <- read_parquet(file.path(proc_dir, "agg_effets_regionaux.parquet")) %>%
  mutate(
    region = reorder(region, effet_pp),
    signif = if_else(p_value < 0.05, "p < 0,05", "non significatif"),
    lo = effet_pp - 1.96 * se_pp,
    hi = effet_pp + 1.96 * se_pp
  )

fig3 <- ggplot(reg, aes(effet_pp, region)) +
  geom_vline(xintercept = 0, color = "grey40", linewidth = 0.5) +
  geom_errorbarh(aes(xmin = lo, xmax = hi), height = 0.3, color = "grey55") +
  geom_point(aes(color = signif), size = 3.5) +
  scale_color_manual(values = c("p < 0,05" = "#d62728",
                                 "non significatif" = "grey65")) +
  labs(
    title    = "Baisse de scolarisation 2021-2022 par région",
    subtitle = "Effet ajusté pour l'âge (modèle linéaire de probabilité, EF âge)",
    x = "Effet sur la probabilité de scolarisation (points de %)",
    y = NULL, color = NULL,
    caption = "Barres : IC 95 %, SE clusterisés au niveau du ménage."
  ) +
  theme_covid()

ggsave(file.path(figs_dir, "fig3_heterogeneite_region_R.png"),
       fig3, width = 8, height = 5, dpi = 200)
cat("Figure 3 sauvegardée\n")

# =============================================================================
# Figure 4 — Évolution des motifs de non-scolarisation
# =============================================================================
motifs <- read_parquet(file.path(proc_dir, "agg_motifs.parquet"))

# Top 7 motifs par effectif cumulé
top7 <- motifs %>%
  group_by(raison_non_scol) %>%
  summarise(tot = sum(n), .groups = "drop") %>%
  slice_max(tot, n = 7) %>%
  pull(raison_non_scol)

motifs_plot <- motifs %>%
  filter(raison_non_scol %in% top7) %>%
  mutate(
    raison_non_scol = reorder(raison_non_scol, part),
    wave = factor(wave),
    part_p = part / 100
  )

fig4 <- ggplot(motifs_plot, aes(part_p, raison_non_scol, fill = wave)) +
  geom_col(position = position_dodge(width = 0.75), width = 0.7) +
  scale_x_continuous(labels = percent_format(accuracy = 1)) +
  scale_fill_manual(values = col_vagues) +
  labs(
    title    = "Motifs de non-scolarisation : 2021 vs 2022",
    subtitle = "Part dans l'ensemble des cas d'enfants non scolarisés",
    x = "Part des motifs déclarés", y = NULL, fill = "Vague",
    caption = "Source : panel ménages COVID-scolarisation Sénégal."
  ) +
  theme_covid()

ggsave(file.path(figs_dir, "fig4_motifs_comparaison_R.png"),
       fig4, width = 8, height = 5, dpi = 200)
cat("Figure 4 sauvegardée\n")

cat("\n=== FIGURES R TERMINÉES ===\n")
cat(sprintf("4 figures écrites dans %s\n", file.path("docs", "figures")))
