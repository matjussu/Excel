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
CONTACTS_SHEET = "Contacts"

# Colonnes de sortie
OUTPUT_COLUMNS = ["MDC", "Types", "Numéro associé", "Name"]
CONTACTS_COLUMNS = ["Name", "Entries", "Num1", "Type1", "relation", "Num2", "Type2", "commentaire"]

# Mapping MCC (Mobile Country Code) vers indicatif téléphonique
MCC_TO_COUNTRY_CODE = {
    "208": "33",   # France
    "262": "49",   # Allemagne
    "234": "44",   # Royaume-Uni
    "222": "39",   # Italie
    "214": "34",   # Espagne
    "206": "32",   # Belgique
    "228": "41",   # Suisse
    "621": "234",  # Nigéria
    "655": "27",   # Afrique du Sud
    "310": "1",    # États-Unis
    "311": "1",    # États-Unis
    "312": "1",    # États-Unis
    "313": "1",    # États-Unis
    "316": "1",    # États-Unis
    "460": "86",   # Chine
    "404": "91",   # Inde
    "405": "91",   # Inde
    "440": "81",   # Japon
    "441": "81",   # Japon
    "505": "61",   # Australie
}


def get_country_code_from_imsi(imsi):
    """Extrait le code pays depuis un IMSI"""
    if not imsi or len(str(imsi)) < 3:
        return None

    # Les 3 premiers chiffres = MCC (Mobile Country Code)
    mcc = str(imsi)[:3]
    return MCC_TO_COUNTRY_CODE.get(mcc)


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
    imsi_list = []

    if df.empty:
        return results, imsi_list

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

                # Si c'est un IMSI, le sauvegarder
                if key == "IMSI":
                    imsi_list.append(value)

                break

    return results, imsi_list


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


def extract_phone_numbers(entries_text, country_code="999"):
    """Extrait et formate les numéros de téléphone depuis le texte entries"""
    if not entries_text or entries_text == "nan":
        return ""

    # Retirer les préfixes comme "Phone-General: "
    # Utiliser regex pour capturer les numéros après le préfixe
    import re

    # Pattern pour trouver les numéros (après Phone-General: ou similaire)
    pattern = r'(?:Phone-General:\s*)?(\+?\d[\d\s\.-]+)'

    matches = re.findall(pattern, entries_text, re.IGNORECASE)

    if not matches:
        return ""

    # Nettoyer et formater les numéros
    formatted_numbers = []
    for num in matches:
        # Nettoyer le numéro (retirer espaces, points, tirets, et le +)
        clean_num = re.sub(r'[\s\.\-\+]', '', num)

        # Si le numéro est vide, ignorer
        if not clean_num:
            continue

        # Si le numéro commence par un indicatif international (plus de 10 chiffres et pas de 0 au début)
        if len(clean_num) > 10 and not clean_num.startswith('0'):
            # Probablement déjà un numéro international, le garder tel quel
            formatted_numbers.append(clean_num)
        elif clean_num.startswith('0'):
            # Remplacer le 0 par l'indicatif pays
            formatted_numbers.append(f"{country_code}{clean_num[1:]}")
        else:
            # Ajouter l'indicatif pays devant
            formatted_numbers.append(f"{country_code}{clean_num}")

    # Joindre tous les numéros avec un espace
    return ' '.join(formatted_numbers)


def process_contacts(df, country_code="999"):
    """Extrait les données de la feuille Contacts"""
    contacts_sim = []
    contacts_whatsapp = []

    if df.empty:
        return contacts_sim, contacts_whatsapp

    # Afficher les colonnes disponibles pour déboguer
    print(f"    Colonnes disponibles: {list(df.columns)}")

    # Trouver les colonnes de façon flexible (insensible à la casse et strip des espaces)
    columns_lower = {str(col).strip().lower(): col for col in df.columns}

    name_col = columns_lower.get("name")
    entries_col = columns_lower.get("entries")
    source_col = columns_lower.get("source")

    print(f"    name_col trouvée: {name_col}")
    print(f"    entries_col trouvée: {entries_col}")
    print(f"    source_col trouvée: {source_col}")

    if not name_col or not entries_col or not source_col:
        print("Warning: Colonnes 'name', 'entries' ou 'source' non trouvées dans Contacts")
        return contacts_sim, contacts_whatsapp

    # Parcourir toutes les lignes
    for idx, row in df.iterrows():
        name = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ""
        entries = str(row[entries_col]).strip() if not pd.isna(row[entries_col]) else ""
        source = str(row[source_col]).strip() if not pd.isna(row[source_col]) else ""

        # Remplacer les sauts de ligne par des espaces dans entries
        entries = entries.replace('\n', ' ').replace('\r', ' ')
        entries = ' '.join(entries.split())

        if not entries or entries == "nan":
            continue

        # Déterminer le Type1 selon la source
        type1 = "Téléphone" if source.upper() == "SIM" else "Vecteur de com"

        # Extraire et formater les numéros de téléphone
        num1 = extract_phone_numbers(entries, country_code)

        # Créer le commentaire
        commentaire = f"Nom : {name if name and name != 'nan' else ''} Tel : {entries}"

        # Créer l'entrée
        contact_entry = {
            "Name": name if name and name != "nan" else "",
            "Entries": entries,
            "Num1": num1,
            "Type1": type1,
            "relation": "apparaît dans le carnet d'adresse de",
            "Num2": "",
            "Type2": "",
            "commentaire": commentaire
        }

        # Répartir selon la source
        if source.upper() == "SIM":
            contacts_sim.append(contact_entry)
        else:
            contacts_whatsapp.append(contact_entry)

    return contacts_sim, contacts_whatsapp


def process_excel_file(file_path, country_code="999"):
    """Traite un fichier Excel et extrait les informations"""
    print(f"Processing {os.path.basename(file_path)}...")

    all_results = []
    all_contacts_sim = []
    all_contacts_whatsapp = []
    all_imsi = []

    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return all_results, all_contacts_sim, all_contacts_whatsapp, all_imsi

    # Traiter Device Info
    if DEVICE_INFO_SHEET in xls.sheet_names:
        try:
            df_device = pd.read_excel(xls, sheet_name=DEVICE_INFO_SHEET, header=1)  # header=1 car colonnes sur ligne 2
            device_results, imsi_list = process_device_info(df_device)
            all_results.extend(device_results)
            all_imsi.extend(imsi_list)
            print(f"  - {len(device_results)} entrées trouvées dans {DEVICE_INFO_SHEET}")
            if imsi_list:
                print(f"  - {len(imsi_list)} IMSI trouvé(s)")
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

    # Traiter Contacts
    if CONTACTS_SHEET in xls.sheet_names:
        try:
            df_contacts = pd.read_excel(xls, sheet_name=CONTACTS_SHEET, header=1)  # header=1 car colonnes sur ligne 2
            contacts_sim, contacts_whatsapp = process_contacts(df_contacts, country_code)
            all_contacts_sim.extend(contacts_sim)
            all_contacts_whatsapp.extend(contacts_whatsapp)
            print(f"  - {len(contacts_sim)} contacts SIM trouvés dans {CONTACTS_SHEET}")
            print(f"  - {len(contacts_whatsapp)} contacts WhatsApp trouvés dans {CONTACTS_SHEET}")
        except Exception as e:
            print(f"Error processing {CONTACTS_SHEET}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"  - Sheet '{CONTACTS_SHEET}' non trouvée")

    return all_results, all_contacts_sim, all_contacts_whatsapp, all_imsi


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

    # Étape 1 : Scanner les fichiers pour détecter les IMSI
    print("Recherche de l'indicatif pays...")
    all_imsi_detected = []

    for file_name in files:
        file_path = os.path.join(INPUT_FOLDER, file_name)
        try:
            xls = pd.ExcelFile(file_path)
            if DEVICE_INFO_SHEET in xls.sheet_names:
                df_device = pd.read_excel(xls, sheet_name=DEVICE_INFO_SHEET, header=1)
                _, imsi_list = process_device_info(df_device)
                all_imsi_detected.extend(imsi_list)
        except:
            pass

    # Déterminer le code pays
    country_code = None
    if all_imsi_detected:
        # Prendre le premier IMSI et extraire le code pays
        first_imsi = all_imsi_detected[0]
        country_code = get_country_code_from_imsi(first_imsi)

        if country_code:
            print(f"✓ IMSI détecté : {first_imsi}")
            print(f"✓ Code pays : +{country_code}\n")
        else:
            mcc = str(first_imsi)[:3]
            print(f"⚠ IMSI détecté ({first_imsi}) mais MCC ({mcc}) non reconnu dans la base")

    # Si pas de code pays détecté, demander à l'utilisateur
    if not country_code:
        print("Aucun IMSI détecté ou MCC non reconnu.")
        country_code = input("Veuillez entrer l'indicatif pays (ex: 33 pour France, 1 pour USA) : ").strip()

        if not country_code:
            print("Aucun indicatif fourni, utilisation de 999 par défaut")
            country_code = "999"
        else:
            print(f"✓ Utilisation de l'indicatif : +{country_code}\n")

    # Étape 2 : Traiter tous les fichiers avec le code pays
    all_data = []
    all_contacts_sim = []
    all_contacts_whatsapp = []

    for file_name in files:
        file_path = os.path.join(INPUT_FOLDER, file_name)
        results, contacts_sim, contacts_whatsapp, _ = process_excel_file(file_path, country_code)
        all_data.extend(results)
        all_contacts_sim.extend(contacts_sim)
        all_contacts_whatsapp.extend(contacts_whatsapp)

    # Créer le DataFrame pour Info_Perso
    df_output = pd.DataFrame(all_data, columns=OUTPUT_COLUMNS)

    # Supprimer les doublons
    nb_avant = len(df_output)
    df_output = df_output.drop_duplicates()
    nb_apres = len(df_output)
    nb_doublons = nb_avant - nb_apres

    # Créer les DataFrames pour les contacts
    df_contacts_sim = pd.DataFrame(all_contacts_sim, columns=CONTACTS_COLUMNS)
    df_contacts_whatsapp = pd.DataFrame(all_contacts_whatsapp, columns=CONTACTS_COLUMNS)

    # Supprimer les doublons pour les contacts
    nb_contacts_sim_avant = len(df_contacts_sim)
    df_contacts_sim = df_contacts_sim.drop_duplicates()
    nb_contacts_sim_apres = len(df_contacts_sim)

    nb_contacts_whatsapp_avant = len(df_contacts_whatsapp)
    df_contacts_whatsapp = df_contacts_whatsapp.drop_duplicates()
    nb_contacts_whatsapp_apres = len(df_contacts_whatsapp)

    # Créer le fichier de sortie
    output_file = os.path.join(OUTPUT_FOLDER, "Info_Perso.xlsx")

    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        df_output.to_excel(writer, sheet_name="Info_Perso", index=False)
        df_contacts_sim.to_excel(writer, sheet_name="Feuil_Contacts", index=False)
        df_contacts_whatsapp.to_excel(writer, sheet_name="Feuil_What'sapp", index=False)

    print("\n" + "=" * 60)
    print(f"TERMINÉ !")
    print(f"  - Info_Perso: {nb_apres} entrées ({nb_doublons} doublons supprimés)")
    print(f"  - Feuil_Contacts: {nb_contacts_sim_apres} entrées ({nb_contacts_sim_avant - nb_contacts_sim_apres} doublons supprimés)")
    print(f"  - Feuil_What'sapp: {nb_contacts_whatsapp_apres} entrées ({nb_contacts_whatsapp_avant - nb_contacts_whatsapp_apres} doublons supprimés)")
    print(f"Fichier créé : {output_file}")
    print("=" * 60)
