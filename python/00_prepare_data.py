"""
00_prepare_data.py
==================
Pipeline de préparation du panel COVID-Scolarisation Sénégal.

Étapes:
  1. Chargement des CSV bruts (2021, 2022)
  2. Chargement des XLSForm pour les labels (variables + modalités)
  3. Déduplication 2022 (keep earliest par `id`)
  4. Normalisation des numéros de téléphone
  5. Construction d'un identifiant ménage anonymisé (SHA-256 salé)
  6. Marquage du statut panel
  7. Reshape des enfants en format long (1 ligne = 1 enfant × 1 vague)
  8. Décodage des variables catégorielles (Oui/Non, Homme/Femme, etc.)
  9. Carry-forward des covariables ménage 2021 → 2022 panel
 10. Écriture des datasets traités en Parquet

Outputs:
  - data/processed/menages_panel.parquet
  - data/processed/enfants_panel.parquet
  - data/processed/dictionnaire_variables.csv

Usage:
  $ python python/00_prepare_data.py
"""
import os
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# ============================================================================
# Configuration
# ============================================================================
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

def _find_one(pattern: str) -> Path:
    """Trouve dans data/raw/ un fichier correspondant au motif glob (insensible aux
    différences d'encodage de noms de fichiers Windows/OneDrive)."""
    matches = sorted(RAW.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"Aucun fichier '{pattern}' dans {RAW}. "
            f"Fichiers présents: {[p.name for p in RAW.iterdir()]}"
        )
    if len(matches) > 1:
        print(f"[prep] ⚠ Plusieurs fichiers pour '{pattern}', utilise: {matches[0].name}")
    return matches[0]

FILE_CSV_21 = _find_one("*2021*.csv")
FILE_CSV_22 = _find_one("*2022*.csv")
FILE_XLS_21 = _find_one("*2021*.xlsx")
FILE_XLS_22 = _find_one("*2022*.xlsx")

load_dotenv(ROOT / ".env")
SALT = os.getenv("ANON_SALT", "")
if not SALT:
    raise RuntimeError("ANON_SALT introuvable dans .env — relance après avoir créé le fichier.")

# Maximum de slots enfants à scanner dans chaque vague (jusqu'à 27 en 2022)
MAX_SLOTS = 27

# Mois français → anglais pour parsing dates SurveyCTO
FR_MONTHS = {
    'janv.': 'Jan', 'févr.': 'Feb', 'mars': 'Mar', 'avr.': 'Apr',
    'mai': 'May', 'juin': 'Jun', 'juil.': 'Jul', 'août': 'Aug',
    'sept.': 'Sep', 'oct.': 'Oct', 'nov.': 'Nov', 'déc.': 'Dec',
}


# ============================================================================
# Helpers
# ============================================================================
def log(msg: str) -> None:
    print(f"[prep] {msg}")


def norm_phone(s) -> str | None:
    """Normalise un numéro: garde seulement les chiffres, retire l'indicatif 221."""
    if pd.isna(s):
        return None
    s = ''.join(ch for ch in str(s) if ch.isdigit())
    if len(s) == 12 and s.startswith('221'):
        s = s[3:]
    return s if len(s) >= 7 else None


def parse_fr_date(s):
    """Parse une date SurveyCTO en français (ex. '7 avr. 2021 15:53:49')."""
    if pd.isna(s):
        return pd.NaT
    s = str(s)
    for fr, en in FR_MONTHS.items():
        s = s.replace(fr, en)
    return pd.to_datetime(s, errors='coerce', dayfirst=True)


def hash_id(s) -> str | None:
    """Hash SHA-256 salé, tronqué à 12 caractères pour lisibilité."""
    if s is None or pd.isna(s):
        return None
    return hashlib.sha256(f"{SALT}|{s}".encode()).hexdigest()[:12]


def load_choice_map(xlsx_path: Path) -> dict[str, dict]:
    """Lit la feuille `choices` d'un XLSForm et retourne {list_name: {value: label}}."""
    ch = pd.read_excel(xlsx_path, sheet_name='choices')
    ch = ch[['list_name', 'value', 'label']].dropna(subset=['list_name', 'value'])
    out = {}
    for ln, sub in ch.groupby('list_name'):
        # Les valeurs peuvent être numériques ou string — on garde les deux clés
        d = {}
        for _, r in sub.iterrows():
            v = r['value']
            lbl = r['label']
            d[v] = lbl
            try:
                d[int(v)] = lbl
                d[float(v)] = lbl
                d[str(int(v))] = lbl
            except (ValueError, TypeError):
                pass
        out[ln] = d
    return out


def load_var_labels(xlsx_path: Path) -> dict[str, str]:
    """Retourne {variable_name: label} depuis la feuille survey."""
    s = pd.read_excel(xlsx_path, sheet_name='survey')
    s = s[['name', 'label']].dropna(subset=['name'])
    return dict(zip(s['name'].astype(str), s['label'].astype(str)))


def decode_col(series: pd.Series, choice_map: dict) -> pd.Series:
    """Remplace les valeurs par leurs labels en gardant NaN inchangés.
    Harmonise aussi la casse (OUI/NON 2022 → Oui/Non 2021) pour cohérence inter-vague."""
    def _decode(v):
        if pd.isna(v):
            return v
        out = choice_map.get(v, v)
        if isinstance(out, str):
            # Harmonisation: 2022 utilise OUI/NON majuscules, 2021 Oui/Non titre
            if out == 'OUI':
                return 'Oui'
            if out == 'NON':
                return 'Non'
        return out
    return series.map(_decode)


# ============================================================================
# Étape 1: Chargement
# ============================================================================
def load_raw():
    log("Chargement des CSV bruts...")
    df21 = pd.read_csv(FILE_CSV_21, low_memory=False)
    df22 = pd.read_csv(FILE_CSV_22, low_memory=False)
    log(f"  2021: {df21.shape[0]} lignes × {df21.shape[1]} colonnes")
    log(f"  2022: {df22.shape[0]} lignes × {df22.shape[1]} colonnes")

    log("Chargement des XLSForm (choices + labels)...")
    choices_21 = load_choice_map(FILE_XLS_21)
    choices_22 = load_choice_map(FILE_XLS_22)
    labels_21 = load_var_labels(FILE_XLS_21)
    labels_22 = load_var_labels(FILE_XLS_22)
    log(f"  2021: {len(choices_21)} listes de choix, {len(labels_21)} labels variables")
    log(f"  2022: {len(choices_22)} listes de choix, {len(labels_22)} labels variables")

    return df21, df22, choices_21, choices_22, labels_21, labels_22


# ============================================================================
# Étape 2: Déduplication 2022
# ============================================================================
def dedup_2022(df22: pd.DataFrame) -> pd.DataFrame:
    log("Déduplication 2022 (keep earliest par 'id')...")
    n_before = len(df22)
    df22 = df22.copy()
    df22['_submit_dt'] = df22['SubmissionDate'].apply(parse_fr_date)
    df22 = (df22
            .sort_values('_submit_dt')
            .drop_duplicates(subset='id', keep='first')
            .reset_index(drop=True))
    log(f"  {n_before} → {len(df22)} lignes ({n_before - len(df22)} doublons retirés)")
    return df22


# ============================================================================
# Étape 3: Construction des clés panel
# ============================================================================
def build_keys(df21: pd.DataFrame, df22: pd.DataFrame):
    log("Normalisation des téléphones et construction du hh_id...")
    df21 = df21.copy()
    df22 = df22.copy()

    df21['phone1'] = df21['LS11'].apply(norm_phone)
    df21['phone2'] = df21['LS12'].apply(norm_phone)
    df22['phone1'] = df22['phone1_ld'].apply(norm_phone)
    df22['phone2'] = df22['phone2_ld'].apply(norm_phone)

    # Clé panel: phone1 par défaut, fallback phone2 si manquant
    df21['phone_key'] = df21['phone1'].fillna(df21['phone2'])
    df22['phone_key'] = df22['phone1'].fillna(df22['phone2'])

    df21['hh_id'] = df21['phone_key'].apply(hash_id)
    df22['hh_id'] = df22['phone_key'].apply(hash_id)

    keys_21 = set(df21['hh_id'].dropna())
    keys_22 = set(df22['hh_id'].dropna())
    panel = keys_21 & keys_22

    df21['in_panel'] = df21['hh_id'].isin(panel)
    df22['in_panel'] = df22['hh_id'].isin(panel)

    log(f"  Ménages 2021 avec hh_id: {df21['hh_id'].notna().sum()} / {len(df21)}")
    log(f"  Ménages 2022 avec hh_id: {df22['hh_id'].notna().sum()} / {len(df22)}")
    log(f"  Ménages dans le panel (2021 ∩ 2022): {len(panel)}")

    # Doublons intra-vague sur hh_id (à signaler mais ne pas supprimer ici)
    d21 = df21['hh_id'].dropna().duplicated().sum()
    d22 = df22['hh_id'].dropna().duplicated().sum()
    if d21 or d22:
        log(f"  ⚠ Doublons hh_id intra-vague: {d21} en 2021, {d22} en 2022 — à inspecter en EDA")

    return df21, df22


# ============================================================================
# Étape 4: Panel ménage (1 ligne = 1 ménage × 1 vague)
# ============================================================================
def build_menages_panel(df21: pd.DataFrame, df22: pd.DataFrame, choices_21: dict):
    log("Construction du panel ménage (long)...")
    edu = choices_21.get('education', {})
    sex = choices_21.get('sexe', {})
    pro = choices_21.get('professions', {})
    reg = choices_21.get('regions', {})

    # Format ISO pour starttime (SurveyCTO standard) — évite l'inférence lente
    m21 = pd.DataFrame({
        'hh_id': df21['hh_id'].values,
        'wave': 2021,
        'in_panel': df21['in_panel'].values,
        'date_collecte': df21.get('starttime', pd.Series(index=df21.index)).apply(parse_fr_date),
        'region': decode_col(df21.get('ST04', pd.Series(index=df21.index)), reg),
        'commune': df21.get('ST05'),
        'sexe_cm': decode_col(df21.get('LS05', pd.Series(index=df21.index)), sex),
        'age_cm': pd.to_numeric(df21.get('LS06'), errors='coerce'),
        'niveau_educ_cm': decode_col(df21.get('LS08', pd.Series(index=df21.index)), edu),
        'profession_cm': decode_col(df21.get('LS09', pd.Series(index=df21.index)), pro),
    })

    # En 2022, les caractéristiques du chef de ménage ne sont pas re-saisies.
    # On construit une coque pour 2022, puis on carry-forward depuis 2021.
    m22 = pd.DataFrame({
        'hh_id': df22['hh_id'].values,
        'wave': 2022,
        'in_panel': df22['in_panel'].values,
        'date_collecte': df22.get('starttime', pd.Series(index=df22.index)).apply(parse_fr_date),
        'region': decode_col(df22.get('cm00_region', pd.Series(index=df22.index)), reg),
        'commune': df22.get('commune'),
        'sexe_cm': np.nan,
        'age_cm': np.nan,
        'niveau_educ_cm': np.nan,
        'profession_cm': np.nan,
    })

    # Table de carry-forward depuis 2021 (1 ligne par hh_id ; on dédoublonne
    # en gardant le premier enregistrement si jamais des doublons existent).
    cf = (m21[m21['in_panel']]
          .drop_duplicates(subset='hh_id', keep='first')
          [['hh_id', 'region', 'sexe_cm', 'age_cm', 'niveau_educ_cm', 'profession_cm']]
          .rename(columns={
              'region': '_region_21',
              'sexe_cm': '_sexe_21',
              'age_cm': '_age_21',
              'niveau_educ_cm': '_educ_21',
              'profession_cm': '_pro_21',
          }))

    m22 = m22.merge(cf, on='hh_id', how='left')
    m22['region'] = m22['region'].combine_first(m22['_region_21'])
    m22['sexe_cm'] = m22['sexe_cm'].combine_first(m22['_sexe_21'])
    m22['age_cm'] = m22['age_cm'].combine_first(m22['_age_21'] + 1)  # +1 an
    m22['niveau_educ_cm'] = m22['niveau_educ_cm'].combine_first(m22['_educ_21'])
    m22['profession_cm'] = m22['profession_cm'].combine_first(m22['_pro_21'])
    m22 = m22.drop(columns=['_region_21', '_sexe_21', '_age_21', '_educ_21', '_pro_21'])

    panel = pd.concat([m21, m22], ignore_index=True)
    log(f"  Panel ménage: {len(panel)} lignes ménage × vague")
    return panel


# ============================================================================
# Étape 5: Panel enfant (1 ligne = 1 enfant × 1 vague)
# ============================================================================
def reshape_enfants_2021(df21: pd.DataFrame, choices: dict) -> pd.DataFrame:
    log("Reshape enfants 2021 (long)...")
    sex = choices.get('sexe', {})
    classe = choices.get('classe', {})
    type_ecole = choices.get('type_ecole', {})
    notes_appr = choices.get('note_appreciation', {})
    raison = choices.get('non_scolarise', {})
    yesno = choices.get('yesno', {})

    rows = []
    for _, hh in df21.iterrows():
        for slot in range(1, MAX_SLOTS + 1):
            # On retient un slot enfant s'il a soit un nom, soit un statut scolaire
            prenom_col = f'prenom_enfant_{slot}'
            sc_col = f'SC01_00_{slot}'
            if hh.get(prenom_col) is None or pd.isna(hh.get(prenom_col)):
                if pd.isna(hh.get(sc_col)):
                    continue

            rec = {
                'hh_id': hh.get('hh_id'),
                'enfant_slot': slot,
                'wave': 2021,
                'in_panel_hh': hh.get('in_panel', False),
                # Démographie enfant
                'age_enfant': pd.to_numeric(hh.get(f'age_enfant_{slot}'), errors='coerce'),
                'sexe_enfant': hh.get(f'sexe_enfant_{slot}'),
                # Scolarité — année courante (2020-21)
                'deja_scolarise_evr': hh.get(f'SC01_00_{slot}'),
                'scolarise': hh.get(f'SC01_01_{slot}'),
                'classe': hh.get(f'SC01_02_{slot}'),
                'type_ecole': hh.get(f'SC01_04_{slot}'),
                'notes': hh.get(f'SC01_05_{slot}'),
                'raison_non_scol': hh.get(f'SC01_06_{slot}'),
                'cours_particuliers': hh.get(f'SC01_07_{slot}'),
                # Rétrospectif (uniquement 2021)
                'classe_2019_20': hh.get(f'SC02_01_{slot}'),
                'type_ecole_2019_20': hh.get(f'SC02_03_{slot}'),
                'raison_non_scol_2019_20': hh.get(f'SC02_04_{slot}'),
                'classe_2018_19': hh.get(f'SC03_01_{slot}'),
                'type_ecole_2018_19': hh.get(f'SC03_03_{slot}'),
                'raison_non_scol_2018_19': hh.get(f'SC03_04_{slot}'),
                # Présence dans le ménage = forcément Oui en 2021
                'enfant_present_menage': 1,
            }
            rows.append(rec)
    df = pd.DataFrame(rows)

    # Décodage
    df['sexe_enfant'] = decode_col(df['sexe_enfant'], sex)
    df['deja_scolarise_evr'] = decode_col(df['deja_scolarise_evr'], yesno)
    df['scolarise'] = decode_col(df['scolarise'], yesno)
    df['classe'] = decode_col(df['classe'], classe)
    df['type_ecole'] = decode_col(df['type_ecole'], type_ecole)
    df['notes'] = decode_col(df['notes'], notes_appr)
    df['raison_non_scol'] = decode_col(df['raison_non_scol'], raison)
    df['cours_particuliers'] = decode_col(df['cours_particuliers'], yesno)
    df['classe_2019_20'] = decode_col(df['classe_2019_20'], classe)
    df['type_ecole_2019_20'] = decode_col(df['type_ecole_2019_20'], type_ecole)
    df['raison_non_scol_2019_20'] = decode_col(df['raison_non_scol_2019_20'], raison)
    df['classe_2018_19'] = decode_col(df['classe_2018_19'], classe)
    df['type_ecole_2018_19'] = decode_col(df['type_ecole_2018_19'], type_ecole)
    df['raison_non_scol_2018_19'] = decode_col(df['raison_non_scol_2018_19'], raison)

    log(f"  Enfants 2021: {len(df)}")
    return df


def reshape_enfants_2022(df22: pd.DataFrame, choices: dict) -> pd.DataFrame:
    log("Reshape enfants 2022 (long)...")
    classe = choices.get('classe', {})
    type_ecole = choices.get('type_ecole', {})
    notes_appr = choices.get('note_appreciat', {})  # nom de liste dif. en 2022
    if not notes_appr:
        notes_appr = choices.get('note_appreciation', {})
    raison = choices.get('non_scolarise', {})
    yesno = choices.get('yesno', {})

    rows = []
    for _, hh in df22.iterrows():
        for slot in range(1, MAX_SLOTS + 1):
            cfr00 = hh.get(f'cfr00_{slot}')
            # On retient un slot s'il y a au moins une réponse cfr
            if pd.isna(cfr00) and pd.isna(hh.get(f'cfr02_{slot}')):
                continue

            rec = {
                'hh_id': hh.get('hh_id'),
                'enfant_slot': slot,
                'wave': 2022,
                'in_panel_hh': hh.get('in_panel', False),
                # En 2022, age/sexe enfant pas re-collecté — sera carry-forward
                'age_enfant': np.nan,
                'sexe_enfant': np.nan,
                # Scolarité — année courante (2021-22)
                'deja_scolarise_evr': np.nan,
                'scolarise': hh.get(f'cfr02_{slot}'),
                'classe': hh.get(f'cfr03_{slot}'),
                'type_ecole': hh.get(f'cfr05_{slot}'),
                'notes': hh.get(f'cfr06_{slot}'),
                'raison_non_scol': hh.get(f'cfr07_{slot}'),
                'cours_particuliers': hh.get(f'cfr08_{slot}'),
                # Présence ménage (clé pour le suivi des sorties)
                'enfant_present_menage': cfr00,
            }
            rows.append(rec)
    df = pd.DataFrame(rows)

    # Décodage
    df['scolarise'] = decode_col(df['scolarise'], yesno)
    df['classe'] = decode_col(df['classe'], classe)
    df['type_ecole'] = decode_col(df['type_ecole'], type_ecole)
    df['notes'] = decode_col(df['notes'], notes_appr)
    df['raison_non_scol'] = decode_col(df['raison_non_scol'], raison)
    df['cours_particuliers'] = decode_col(df['cours_particuliers'], yesno)
    df['enfant_present_menage'] = decode_col(df['enfant_present_menage'], yesno)

    log(f"  Enfants 2022 (module cfr): {len(df)}")
    return df


def carry_forward_demos(enfants: pd.DataFrame) -> pd.DataFrame:
    """Pour les enfants du panel, hérite age (+1) et sexe de 2021 vers 2022."""
    log("Carry-forward démographie enfant 2021 → 2022...")
    base21 = enfants[enfants['wave'] == 2021][['hh_id', 'enfant_slot', 'age_enfant', 'sexe_enfant']]
    base21 = base21.rename(columns={'age_enfant': 'age_2021', 'sexe_enfant': 'sexe_2021'})
    enfants = enfants.merge(base21, on=['hh_id', 'enfant_slot'], how='left')

    is_22 = enfants['wave'] == 2022
    enfants.loc[is_22, 'age_enfant'] = enfants.loc[is_22, 'age_enfant'].fillna(enfants.loc[is_22, 'age_2021'] + 1)
    enfants.loc[is_22, 'sexe_enfant'] = enfants.loc[is_22, 'sexe_enfant'].fillna(enfants.loc[is_22, 'sexe_2021'])
    enfants = enfants.drop(columns=['age_2021', 'sexe_2021'])

    n_imputed = is_22.sum() - enfants.loc[is_22, 'age_enfant'].isna().sum()
    log(f"  Démographies 2022 complétées par carry-forward: {n_imputed}")
    return enfants


def add_status(enfants: pd.DataFrame) -> pd.DataFrame:
    """Statut de l'enfant: panel_present, panel_sortie, only_2021, only_2022."""
    keys_21 = set(zip(enfants.loc[enfants['wave'] == 2021, 'hh_id'],
                      enfants.loc[enfants['wave'] == 2021, 'enfant_slot']))
    keys_22 = set(zip(enfants.loc[enfants['wave'] == 2022, 'hh_id'],
                      enfants.loc[enfants['wave'] == 2022, 'enfant_slot']))

    def _stat(row):
        k = (row['hh_id'], row['enfant_slot'])
        if k in keys_21 and k in keys_22:
            return 'panel_present'
        elif k in keys_21:
            return 'only_2021'
        else:
            return 'only_2022'

    enfants['statut_enfant'] = enfants.apply(_stat, axis=1)
    log("  Statut enfant ajouté.")
    log(f"  Distribution: \n{enfants['statut_enfant'].value_counts().to_string()}")
    return enfants


def merge_with_menage(enfants: pd.DataFrame, menages: pd.DataFrame) -> pd.DataFrame:
    """Joint les covariables ménage à chaque ligne enfant-vague.

    Important: on dédoublonne menages sur (hh_id, wave) avant le merge pour
    éviter une explosion de lignes côté enfants. Les doublons résiduels
    proviennent d'erreurs de saisie (même téléphone, géographie incohérente
    sur deux soumissions différentes) — on garde la première occurrence.
    """
    log("Jointure enfants ← ménages...")
    keep = ['hh_id', 'wave', 'region', 'commune', 'sexe_cm', 'age_cm',
            'niveau_educ_cm', 'profession_cm']
    n_dup = menages.duplicated(subset=['hh_id', 'wave']).sum()
    if n_dup:
        log(f"  Dédoublonnage menages: {n_dup} lignes en doublon (hh_id, wave) retirées")
    m_clean = (menages[keep]
               .dropna(subset=['hh_id'])
               .drop_duplicates(subset=['hh_id', 'wave'], keep='first'))
    n_before = len(enfants)
    enfants = enfants.merge(m_clean, on=['hh_id', 'wave'], how='left')
    log(f"  Enfants: {n_before} → {len(enfants)} lignes après merge")
    return enfants


# ============================================================================
# Étape 6: Dictionnaire des variables clés
# ============================================================================
def build_dictionary(labels_21: dict, labels_22: dict) -> pd.DataFrame:
    log("Construction du dictionnaire des variables...")
    rows = []
    # Variables principales du panel final
    mapping = [
        ('hh_id', 'Identifiant ménage anonymisé (SHA-256 salé du téléphone)', ''),
        ('wave', 'Vague d\'enquête (2021 ou 2022)', ''),
        ('enfant_slot', 'Position de l\'enfant dans le roster ménage (1-27)', ''),
        ('in_panel_hh', 'Ménage présent dans les deux vagues', ''),
        ('statut_enfant', 'panel_present / only_2021 / only_2022', ''),
        ('enfant_present_menage', 'Enfant toujours dans le ménage en 2022 (cfr00)', ''),
        ('region', 'Région d\'enquête', 'ST04 / cm00_region'),
        ('commune', 'Commune d\'enquête', 'ST05 / commune'),
        ('sexe_cm', 'Sexe du chef de ménage', 'LS05'),
        ('age_cm', 'Âge du chef de ménage', 'LS06'),
        ('niveau_educ_cm', 'Niveau d\'éducation du chef de ménage', 'LS08'),
        ('profession_cm', 'Profession du chef de ménage', 'LS09'),
        ('age_enfant', 'Âge de l\'enfant en années révolues', 'age_enfant_N'),
        ('sexe_enfant', 'Sexe de l\'enfant', 'sexe_enfant_N'),
        ('scolarise', 'Enfant scolarisé l\'année scolaire courante', 'SC01_01_N / cfr02_N'),
        ('classe', 'Classe actuelle de l\'enfant', 'SC01_02_N / cfr03_N'),
        ('type_ecole', 'Type d\'école', 'SC01_04_N / cfr05_N'),
        ('notes', 'Appréciation des notes', 'SC01_05_N / cfr06_N'),
        ('raison_non_scol', 'Raison de non-scolarisation', 'SC01_06_N / cfr07_N'),
        ('cours_particuliers', 'Suit des cours particuliers', 'SC01_07_N / cfr08_N'),
        ('classe_2019_20', 'Classe en 2019-2020 (rétrospectif, 2021 seulement)', 'SC02_01_N'),
        ('classe_2018_19', 'Classe en 2018-2019 (rétrospectif, 2021 seulement)', 'SC03_01_N'),
    ]
    for var, lbl, src in mapping:
        rows.append({'variable': var, 'label': lbl, 'source_brut': src})
    return pd.DataFrame(rows)


# ============================================================================
# Main
# ============================================================================
def main():
    log("=== DÉBUT PIPELINE PRÉPARATION ===")
    df21, df22, choices_21, choices_22, labels_21, labels_22 = load_raw()

    df22 = dedup_2022(df22)
    df21, df22 = build_keys(df21, df22)

    menages = build_menages_panel(df21, df22, choices_21)
    enfants_21 = reshape_enfants_2021(df21, choices_21)
    enfants_22 = reshape_enfants_2022(df22, choices_22)
    enfants = pd.concat([enfants_21, enfants_22], ignore_index=True)

    enfants = carry_forward_demos(enfants)
    enfants = add_status(enfants)
    enfants = merge_with_menage(enfants, menages)

    dico = build_dictionary(labels_21, labels_22)

    # Écriture
    log("Écriture des fichiers parquet...")

    def _safe_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
        """Force les colonnes object hétérogènes en string pour PyArrow."""
        df = df.copy()
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype('string')
        return df

    out_men = OUT / "menages_panel.parquet"
    out_enf = OUT / "enfants_panel.parquet"
    out_dico = OUT / "dictionnaire_variables.csv"
    _safe_for_parquet(menages).to_parquet(out_men, index=False)
    _safe_for_parquet(enfants).to_parquet(out_enf, index=False)
    dico.to_csv(out_dico, index=False, encoding='utf-8')

    log(f"  ✓ {out_men.relative_to(ROOT)}: {len(menages)} lignes")
    log(f"  ✓ {out_enf.relative_to(ROOT)}: {len(enfants)} lignes")
    log(f"  ✓ {out_dico.relative_to(ROOT)}: {len(dico)} variables documentées")

    log("=== FIN PIPELINE ===")
    log(f"Synthèse: {menages['hh_id'].nunique()} ménages uniques, "
        f"{enfants[['hh_id','enfant_slot']].drop_duplicates().shape[0]} enfants uniques.")


if __name__ == "__main__":
    main()