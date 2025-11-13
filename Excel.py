import os
import pandas as pd
import re

# Configuration
INPUT_FOLDER = "INPUT"
OUTPUT_FOLDER = "OUTPUT"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Noms des feuilles à analyser
DEVICE_INFO_SHEET = "Device Info"
USER_ACCOUNTS_SHEET = "User Accounts"

# Colonnes de sortie
OUTPUT_COLUMNS = ["MDC", "Types", "Numéro associé", "Name"]


def is_phone_number(text):
    """Détecte si le texte est un numéro de téléphone"""
    if pd.isna(text):
        return False
    text_str = str(text).strip()
    # Patterns pour détecter les téléphones
    phone_patterns = [
        r'^\+\d{1,3}[\s\.-]?\d{1,4}[\s\.-]?\d{1,4}[\s\.-]?\d{1,9}$',  # International
        r'^0[1-9]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}$',  # Français
        r'^\d{10,15}$',  # Simple numérique
    ]
    for pattern in phone_patterns:
        if re.match(pattern, text_str):
            return True
    return False


def process_device_info(df):
    """Extrait les données de la feuille Device Info"""
    results = []

    if df.empty:
        return results

    # Afficher les colonnes disponibles pour déboguer
    print(f"    Colonnes disponibles: {list(df.columns)}")

    # Mapping des types recherchés vers leur catégorie MDC
    device_mappings = {
        "IMEI": {"MDC": "Téléphone", "Types": "IMEI"},
        "IMSI": {"MDC": "Téléphone", "Types": "IMSI"},
        "Advertising ID": {"MDC": "Vecteur de com", "Types": "Advertising ID"},
        "Mac Address": {"MDC": "IOC", "Types": "Mac Address"},
        "MAC Address": {"MDC": "IOC", "Types": "Mac Address"},
        "Bluetooth": {"MDC": "IOC", "Types": "Bluetooth"},
        "Bluetooth Address": {"MDC": "IOC", "Types": "Bluetooth"},
    }

    # Trouver les colonnes de façon flexible (insensible à la casse)
    columns_lower = {col.lower() if isinstance(col, str) else str(col).lower(): col for col in df.columns}

    # Chercher les colonnes "nom" et "value" (ou similaires)
    nom_col = None
    value_col = None

    for key, col in columns_lower.items():
        if "name" in key or "nom" in key:
            nom_col = col
        if "value" in key or "valeur" in key:
            value_col = col

    # Si pas trouvé par nom, utiliser les 2 dernières colonnes
    if not nom_col or not value_col:
        if len(df.columns) >= 2:
            nom_col = df.columns[-2]
            value_col = df.columns[-1]
            print(f"    Utilisation des 2 dernières colonnes: {nom_col}, {value_col}")

    if not nom_col or not value_col:
        print("Warning: Colonnes 'nom' et 'value' non trouvées dans Device Info")
        return results

    # Parcourir toutes les lignes
    for idx, row in df.iterrows():
        nom = str(row[nom_col]).strip() if not pd.isna(row[nom_col]) else ""
        value = str(row[value_col]).strip() if not pd.isna(row[value_col]) else ""

        if not nom or not value or value == "nan":
            continue

        # Chercher si le nom correspond à un type recherché
        for key, mapping in device_mappings.items():
            if key.lower() in nom.lower():
                results.append({
                    "MDC": mapping["MDC"],
                    "Types": mapping["Types"],
                    "Numéro associé": value,
                    "Name": ""
                })
                break

    return results


def process_user_accounts(df):
    """Extrait les données de la feuille User Accounts"""
    results = []

    if df.empty:
        return results

    # Afficher les colonnes disponibles pour déboguer
    print(f"    Colonnes disponibles: {list(df.columns)}")

    # Trouver les colonnes de façon flexible (insensible à la casse et strip des espaces)
    columns_lower = {str(col).strip().lower(): col for col in df.columns}

    print(f"    Clés créées: {list(columns_lower.keys())}")

    entries_col = columns_lower.get("entries")
    source_col = columns_lower.get("source")
    account_name_col = columns_lower.get("account name")

    print(f"    entries_col trouvée: {entries_col}")
    print(f"    source_col trouvée: {source_col}")
    print(f"    account_name_col trouvée: {account_name_col}")

    if not entries_col or not source_col:
        print("Warning: Colonnes 'entries' ou 'source' non trouvées dans User Accounts")
        return results

    # Parcourir toutes les lignes
    for idx, row in df.iterrows():
        entries = str(row[entries_col]).strip() if not pd.isna(row[entries_col]) else ""
        source = str(row[source_col]).strip() if not pd.isna(row[source_col]) else ""
        account_name = str(row[account_name_col]).strip() if account_name_col and not pd.isna(row[account_name_col]) else ""

        # Remplacer les sauts de ligne par des espaces dans entries
        entries = entries.replace('\n', ' ').replace('\r', ' ')
        # Supprimer les espaces multiples
        entries = ' '.join(entries.split())

        if not entries or entries == "nan":
            continue

        # Déterminer le MDC selon le type de données
        mdc = "Vecteur de com"  # Par défaut

        # Si c'est un numéro de téléphone
        if is_phone_number(entries):
            mdc = "Téléphone"

        results.append({
            "MDC": mdc,
            "Types": source if source and source != "nan" else "Unknown",
            "Numéro associé": entries,
            "Name": account_name if account_name and account_name != "nan" else ""
        })

    return results


def process_excel_file(file_path):
    """Traite un fichier Excel et extrait les informations"""
    print(f"Processing {os.path.basename(file_path)}...")

    all_results = []

    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return all_results

    # Traiter Device Info
    if DEVICE_INFO_SHEET in xls.sheet_names:
        try:
            df_device = pd.read_excel(xls, sheet_name=DEVICE_INFO_SHEET, header=1)  # header=1 car colonnes sur ligne 2
            device_results = process_device_info(df_device)
            all_results.extend(device_results)
            print(f"  - {len(device_results)} entrées trouvées dans {DEVICE_INFO_SHEET}")
        except Exception as e:
            print(f"Error processing {DEVICE_INFO_SHEET}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  - Sheet '{DEVICE_INFO_SHEET}' non trouvée")

    # Traiter User Accounts
    if USER_ACCOUNTS_SHEET in xls.sheet_names:
        try:
            df_accounts = pd.read_excel(xls, sheet_name=USER_ACCOUNTS_SHEET, header=1)  # header=1 car colonnes sur ligne 2
            accounts_results = process_user_accounts(df_accounts)
            all_results.extend(accounts_results)
            print(f"  - {len(accounts_results)} entrées trouvées dans {USER_ACCOUNTS_SHEET}")
        except Exception as e:
            print(f"Error processing {USER_ACCOUNTS_SHEET}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  - Sheet '{USER_ACCOUNTS_SHEET}' non trouvée")

    return all_results


if __name__ == "__main__":
    print("=" * 60)
    print("EXTRACTION DES INFORMATIONS PERSONNELLES")
    print("=" * 60)

    # Vérifier que le dossier INPUT existe
    if not os.path.exists(INPUT_FOLDER):
        print(f"ERROR: Le dossier '{INPUT_FOLDER}' n'existe pas!")
        exit(1)

    # Lister les fichiers Excel
    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.xlsx')]

    if not files:
        print(f"ERROR: Aucun fichier .xlsx trouvé dans '{INPUT_FOLDER}'")
        exit(1)

    print(f"\n{len(files)} fichier(s) trouvé(s)\n")

    all_data = []

    # Traiter chaque fichier
    for file_name in files:
        file_path = os.path.join(INPUT_FOLDER, file_name)
        results = process_excel_file(file_path)
        all_data.extend(results)

    # Créer le DataFrame final
    df_output = pd.DataFrame(all_data, columns=OUTPUT_COLUMNS)

    # Supprimer les doublons
    nb_avant = len(df_output)
    df_output = df_output.drop_duplicates()
    nb_apres = len(df_output)
    nb_doublons = nb_avant - nb_apres

    # Créer le fichier de sortie
    output_file = os.path.join(OUTPUT_FOLDER, "Info_Perso.xlsx")

    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_output.to_excel(writer, sheet_name="Info_Perso", index=False)

    print("\n" + "=" * 60)
    print(f"TERMINÉ ! {nb_apres} entrées extraites ({nb_doublons} doublons supprimés)")
    print(f"Fichier créé : {output_file}")
    print("=" * 60)
