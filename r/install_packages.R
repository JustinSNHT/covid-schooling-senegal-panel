# =============================================================================
# install_packages.R
# =============================================================================
# Installe les paquets R nécessaires à l'analyse.
# À exécuter une seule fois après avoir cloné le projet.
#
# Usage : Rscript r/install_packages.R   (ou source() depuis RStudio)
# =============================================================================

# Paquets requis
pkgs <- c(
  "arrow",         # lecture des fichiers parquet
  "dplyr",         # manipulation de données
  "tidyr",         # reshape (pivot)
  "ggplot2",       # visualisation
  "scales",        # formatage des axes (pourcentages)
  "fixest",        # estimation à effets fixes (feols)
  "modelsummary"   # tableaux de régression publication-ready
)

# Installe uniquement ceux qui manquent
manquants <- pkgs[!(pkgs %in% rownames(installed.packages()))]

if (length(manquants) > 0) {
  cat("Installation des paquets manquants :", paste(manquants, collapse = ", "), "\n")
  install.packages(manquants, repos = "https://cloud.r-project.org")
} else {
  cat("Tous les paquets requis sont déjà installés.\n")
}

# Vérification finale
cat("\nVérification :\n")
for (p in pkgs) {
  ok <- requireNamespace(p, quietly = TRUE)
  cat(sprintf("  %-14s %s\n", p, if (ok) "OK" else "MANQUANT"))
}
