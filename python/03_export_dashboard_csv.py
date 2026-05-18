"""
03_export_dashboard_csv.py
==========================
Exporte les agrégats analytiques + des tables de dimensions au format CSV,
dans powerbi/data/, pour alimenter le dashboard Power BI.

Pourquoi CSV et pas parquet : Power BI lit le CSV de façon parfaitement
robuste, sans configuration. L'encodage utf-8-sig (avec BOM) garantit que
les accents français s'affichent correctement.

Les fichiers produits sont des agrégats anonymisés — aucun risque PII.

Entrées : data/processed/agg_*.parquet
Sorties : powerbi/data/*.csv

Usage : python python/03_export_dashboard_csv.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "powerbi" / "data"
OUT.mkdir(parents=True, exist_ok=True)

ENC = "utf-8-sig"  # BOM -> accents corrects dans Power BI


def main():
    print("[export] Export des agrégats vers CSV...")

    # --- Tables de faits : les agrégats ---
    agg_files = sorted(PROC.glob("agg_*.parquet"))
    if not agg_files:
        raise FileNotFoundError(
            f"Aucun fichier agg_*.parquet dans {PROC}. "
            "Lance d'abord python/02_analysis.ipynb."
        )
    for f in agg_files:
        df = pd.read_parquet(f)
        df.to_csv(OUT / f"{f.stem}.csv", index=False, encoding=ENC)
        print(f"  {f.stem}.csv : {df.shape[0]} lignes")

    # --- Tables de dimensions (pour les slicers transverses) ---
    pd.DataFrame({"sexe_enfant": ["Femme", "Homme"]}).to_csv(
        OUT / "dim_sexe.csv", index=False, encoding=ENC)

    regions = set()
    for name in ["agg_scolarisation_par_groupe", "agg_effets_regionaux"]:
        p = PROC / f"{name}.parquet"
        if p.exists():
            regions |= set(pd.read_parquet(p)["region"].dropna())
    pd.DataFrame({"region": sorted(regions)}).to_csv(
        OUT / "dim_region.csv", index=False, encoding=ENC)

    pd.DataFrame({
        "wave": [2021, 2022],
        "annee_scolaire": ["2020-2021", "2021-2022"],
    }).to_csv(OUT / "dim_wave.csv", index=False, encoding=ENC)

    print(f"  dim_sexe.csv, dim_region.csv ({len(regions)} régions), dim_wave.csv")
    print(f"[export] Terminé — fichiers dans {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
