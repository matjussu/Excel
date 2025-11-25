import os
import pandas as pd
import re

# Configuration
INPUT_FOLDER = "BRUT"
OUTPUT_FOLDER = "OUTPUT"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Noms des feuilles à analyser
DEVICE_INFO_SHEET = "Device Info"
USER_ACCOUNTS_SHEET = "User Accounts"
CONTACTS_SHEET = "Contacts"
CALL_LOG_SHEET = "Call Log"

# Colonnes de sortie
OUTPUT_COLUMNS = ["Entité", "Types", "Numéro associé", "Name"]
CONTACTS_COLUMNS = ["Name", "Entries", "Num1", "Type1", "relation", "Num2", "Type2", "commentaire"]
CALL_LOG_COLUMNS = ["Parties", "Direction", "Num1", "Type", "Relation", "Num2", "Durée", "Dates", "Heure"]

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
    mcc = str(imsi)[:3]
    return MCC_TO_COUNTRY_CODE.get(mcc)


def is_phone_number(text):
    """Détecte si le texte est un numéro de téléphone"""
    if pd.isna(text):
        return False
    text_str = str(text).strip()
    phone_patterns = [
        r'^\+\d{1,3}[\s\.-]?\d{1,4}[\s\.-]?\d{1,4}[\s\.-]?\d{1,9}$',
        r'^0[1-9]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}$',
        r'^\d{10,15}$',
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

    device_mappings = {
        "IMEI": {"Entité": "Moyen de com", "Types": "IMEI"},
        "IMSI": {"Entité": "Moyen de com", "Types": "IMSI"},
        "Advertising ID": {"Entité ": "Vecteur de com", "Types": "Advertising ID"},
        "Mac Address": {"Entité": "IOC", "Types": "Mac Address"},
        "Bluetooth Address": {"Entité": "IOC", "Types": "Bluetooth address"},
    }

    # Détecter les colonnes Name et Value
    columns_lower = {str(col).strip().lower(): col for col in df.columns}
    nom_col = columns_lower.get("name")
    value_col = columns_lower.get("value")

    if not nom_col or not value_col:
        return results, imsi_list

    for idx, row in df.iterrows():
        nom = str(row[nom_col]).strip() if not pd.isna(row[nom_col]) else ""
        value = str(row[value_col]).strip() if not pd.isna(row[value_col]) else ""

        if not nom or not value or value == "nan":
            continue

        for key, mapping in device_mappings.items():
            if key.lower() in nom.lower():
                results.append({
                    "Entité": mapping["Entité"],
                    "Types": mapping["Types"],
                    "Numéro associé": value,
                    "Name": ""
                })

                if key == "IMSI":
                    imsi_list.append(value)

                break

    return results, imsi_list


def process_user_accounts(df):
    """Extrait les données de la feuille User Accounts"""
    results = []

    if df.empty:
        return results

    columns_lower = {str(col).strip().lower(): col for col in df.columns}

    entries_col = columns_lower.get("entries")
    source_col = columns_lower.get("source")
    account_name_col = columns_lower.get("account name")

    if not entries_col or not source_col:
        return results

    for idx, row in df.iterrows():
        entries = str(row[entries_col]).strip() if not pd.isna(row[entries_col]) else ""
        source = str(row[source_col]).strip() if not pd.isna(row[source_col]) else ""
        account_name = str(row[account_name_col]).strip() if account_name_col and not pd.isna(row[account_name_col]) else ""

        entries = entries.replace('\n', ' ').replace('\r', ' ')
        entries = ' '.join(entries.split())

        if not entries or entries == "nan":
            continue

        Entite = "Vecteur de com"
        if is_phone_number(entries):
            Entite = "Moyen de com"

        results.append({
            "Entité": Entite,
            "Types": source if source and source != "nan" else "Unknown",
            "Numéro associé": entries,
            "Name": account_name if account_name and account_name != "nan" else ""
        })

    return results


def extract_phone_numbers(entries_text, country_code="999"):
    """Extrait et formate les numéros de téléphone depuis le texte entries"""
    if not entries_text or entries_text == "nan":
        return ""

    # Accepter Phone-General, Phone-Mobile, ou n'importe quel numéro
    pattern = r'(?:(?:Phone-General|Phone-Mobile):\s*)?(\+?\d[\d\s\.-]+)'
    matches = re.findall(pattern, entries_text, re.IGNORECASE)

    if not matches:
        return ""

    formatted_numbers = []
    for num in matches:
        clean_num = re.sub(r'[\s\.\-\+]', '', num)

        if not clean_num:
            continue

        if len(clean_num) > 10 and not clean_num.startswith('0'):
            formatted_numbers.append(clean_num)
        elif clean_num.startswith('0'):
            formatted_numbers.append(f"{country_code}{clean_num[1:]}")
        else:
            formatted_numbers.append(f"{country_code}{clean_num}")

    return ' '.join(formatted_numbers)


def process_contacts(df, country_code="999"):
    """Extrait les données de la feuille Contacts"""
    contacts_sim = []
    contacts_whatsapp = []

    if df.empty:
        return contacts_sim, contacts_whatsapp

    columns_lower = {str(col).strip().lower(): col for col in df.columns}

    name_col = columns_lower.get("name")
    entries_col = columns_lower.get("entries")
    source_col = columns_lower.get("source")

    if not name_col or not entries_col or not source_col:
        return contacts_sim, contacts_whatsapp

    for idx, row in df.iterrows():
        name = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ""
        entries = str(row[entries_col]).strip() if not pd.isna(row[entries_col]) else ""
        source = str(row[source_col]).strip() if not pd.isna(row[source_col]) else ""

        entries = entries.replace('\n', ' ').replace('\r', ' ')
        entries = ' '.join(entries.split())

        if not entries or entries == "nan":
            continue

        type1 = "Téléphone" if source.upper() == "SIM" else "Vecteur de com"
        num1 = extract_phone_numbers(entries, country_code)
        commentaire = f"Nom : {name if name and name != 'nan' else ''} Tel : {entries}"

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

        if source.upper() == "SIM":
            contacts_sim.append(contact_entry)
        else:
            contacts_whatsapp.append(contact_entry)

    return contacts_sim, contacts_whatsapp


def convert_duration_to_seconds(duration_str):
    """Convertit une durée au format HH:MM:SS en secondes"""
    if not duration_str or duration_str == "nan" or duration_str == "":
        return ""

    try:
        # Si c'est un objet datetime.time (créé par pandas)
        if hasattr(duration_str, 'hour') and hasattr(duration_str, 'minute') and hasattr(duration_str, 'second'):
            total_seconds = duration_str.hour * 3600 + duration_str.minute * 60 + duration_str.second
            return str(total_seconds)

        # Si c'est un timedelta
        if hasattr(duration_str, 'total_seconds'):
            return str(int(duration_str.total_seconds()))

        # Format HH:MM:SS en string
        if ":" in str(duration_str):
            parts = str(duration_str).split(":")
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                total_seconds = hours * 3600 + minutes * 60 + seconds
                return str(total_seconds)
            elif len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                total_seconds = minutes * 60 + seconds
                return str(total_seconds)

        # Si c'est déjà un nombre
        return str(duration_str)
    except:
        return str(duration_str)


def process_call_log(df, country_code="999"):
    """Extrait les données de la feuille Call log"""
    call_log_entries = []

    if df.empty:
        print("    ⚠ Call log vide (0 lignes)")
        return call_log_entries

    # Créer le mapping des colonnes (case-insensitive et trimmed)
    columns_lower = {str(col).strip().lower(): col for col in df.columns}

    # Debug : afficher TOUTES les colonnes
    print(f"    → Colonnes disponibles ({len(columns_lower)}) : {list(columns_lower.keys())}")

    # Rechercher les colonnes avec flexibilité
    parties_col = None
    date_col = None
    time_col = None
    duration_col = None
    direction_col = None
    source_col = None

    for key, col in columns_lower.items():
        if not parties_col and ("parties" in key or "party" in key or "partie" in key):
            parties_col = col
        if not date_col and "date" in key:
            date_col = col

        if not time_col and "time" in key:
            time_col = col

        if not duration_col and ("duration" in key or "durée" in key or "duree" in key):
            duration_col = col

        if not direction_col and "direction" in key:
            direction_col = col


    for idx, row in df.iterrows():
        # Récupérer les valeurs brutes avec vérification pd.isna()
        parties_raw = row[parties_col] if parties_col and not pd.isna(row[parties_col]) else ""
        date_raw = row[date_col] if date_col and not pd.isna(row[date_col]) else ""
        time_raw = row[time_col] if time_col and not pd.isna(row[time_col]) else ""
        duration_raw = row[duration_col] if duration_col and not pd.isna(row[duration_col]) else ""
        direction_raw = row[direction_col] if direction_col and not pd.isna(row[direction_col]) else ""

        # Convertir en string et nettoyer
        parties = str(parties_raw).strip()
        date = str(date_raw).strip()
        time = str(time_raw).strip()
        duration = str(duration_raw).strip()
        direction = str(direction_raw).strip()


        # Convertir Duration en secondes
        duration_seconds = convert_duration_to_seconds(duration)

        # Convertir Direction : Outgoing = 1, autre = 2
        if direction and direction != "nan" and direction != "":
            direction_value = "1" if direction.upper() == "OUTGOING" else "2"
        else:
            direction_value = "2"  # Par défaut

        # Déterminer la relation selon la direction
        relation = "a appelé" if direction_value == "1" else "a reçu l'appel"

        # Formater le numéro de téléphone
        num1 = extract_phone_numbers(parties, country_code)

        # Créer l'entrée avec clés exactement comme dans CALL_LOG_COLUMNS
        call_log_entry = {
            "Parties": parties,
            "Direction": direction_value,
            "Num1": num1 if num1 else parties,
            "Type": "Téléphone",
            "Relation": relation,
            "Num2": "",
            "Durée": duration_seconds,
            "Dates": date if date and date != "nan" else "",
            "Heure": time if time and time != "nan" else ""
        }

        call_log_entries.append(call_log_entry)
    return call_log_entries


def process_excel_file(file_path, country_code="999"):
    """Traite un fichier Excel et extrait les informations"""
    all_results = []
    all_contacts_sim = []
    all_contacts_whatsapp = []
    all_call_log = []
    all_imsi = []

    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"  ✗ Erreur de lecture : {e}")
        return all_results, all_contacts_sim, all_contacts_whatsapp, all_call_log, all_imsi

    # Traiter Device Info
    if DEVICE_INFO_SHEET in xls.sheet_names:
        try:
            df_device = pd.read_excel(xls, sheet_name=DEVICE_INFO_SHEET, header=1)
            device_results, imsi_list = process_device_info(df_device)
            all_results.extend(device_results)
            all_imsi.extend(imsi_list)
        except Exception as e:
            print(f"  ✗ Erreur Device Info : {e}")

    # Traiter User Accounts
    if USER_ACCOUNTS_SHEET in xls.sheet_names:
        try:
            df_accounts = pd.read_excel(xls, sheet_name=USER_ACCOUNTS_SHEET, header=1)
            accounts_results = process_user_accounts(df_accounts)
            all_results.extend(accounts_results)
        except Exception as e:
            print(f"  ✗ Erreur User Accounts : {e}")

    # Traiter Contacts
    if CONTACTS_SHEET in xls.sheet_names:
        try:
            df_contacts = pd.read_excel(xls, sheet_name=CONTACTS_SHEET, header=1)
            contacts_sim, contacts_whatsapp = process_contacts(df_contacts, country_code)
            all_contacts_sim.extend(contacts_sim)
            all_contacts_whatsapp.extend(contacts_whatsapp)
        except Exception as e:
            print(f"  ✗ Erreur Contacts : {e}")

    # Traiter Call log
    if CALL_LOG_SHEET in xls.sheet_names:
        try:
            # Essayer header=1 d'abord
            df_call_log = pd.read_excel(xls, sheet_name=CALL_LOG_SHEET, header=1)
            call_log_entries = process_call_log(df_call_log, country_code)

            all_call_log.extend(call_log_entries)
        except Exception as e:
            print(f"  ✗ Erreur Call log : {e}")
            import traceback
            traceback.print_exc()

    return all_results, all_contacts_sim, all_contacts_whatsapp, all_call_log, all_imsi


if __name__ == "__main__":
    print("=" * 60)
    print("EXTRACTION DES INFORMATIONS PERSONNELLES")
    print("=" * 60)

    if not os.path.exists(INPUT_FOLDER):
        print(f"\n✗ Erreur : Le dossier '{INPUT_FOLDER}' n'existe pas!")
        exit(1)

    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.xlsx') and not f.startswith('~$')]

    if not files:
        print(f"\n✗ Erreur : Aucun fichier .xlsx trouvé dans '{INPUT_FOLDER}'")
        exit(1)

    print(f"\n{len(files)} fichier(s) détecté(s)\n")

    print("-" * 60)
    print("Traitement des fichiers...")
    print("-" * 60)

    # Traiter chaque fichier individuellement
    for file_name in files:
        file_path = os.path.join(INPUT_FOLDER, file_name)

        print(f"\n→ {file_name}")

        # Étape 1 : Détecter l'IMSI pour ce fichier
        country_code = None
        try:
            xls = pd.ExcelFile(file_path)
            if DEVICE_INFO_SHEET in xls.sheet_names:
                df_device = pd.read_excel(xls, sheet_name=DEVICE_INFO_SHEET, header=1)
                _, imsi_list = process_device_info(df_device)

                if imsi_list:
                    first_imsi = imsi_list[0]
                    country_code = get_country_code_from_imsi(first_imsi)

                    if country_code:
                        print(f"  ✓ IMSI détecté → Code pays : +{country_code}")
                    else:
                        mcc = str(first_imsi)[:3]
                        print(f"  ⚠ IMSI détecté mais MCC ({mcc}) non reconnu")
        except:
            pass

        # Si pas de code pays détecté, demander à l'utilisateur
        if not country_code:
            print("  ⚠ Aucun IMSI détecté pour ce fichier")
            country_code = input(f"  → Entrez l'indicatif pays pour '{file_name}' (ex: 33 pour France, Entrée pour 999) : ").strip()

            if not country_code:
                print("  → Utilisation de l'indicatif par défaut :")
                country_code = ""
            else:
                print(f"  ✓ Utilisation de l'indicatif : +{country_code}")

        # Étape 2 : Traiter le fichier
        results, contacts_sim, contacts_whatsapp, call_log, _ = process_excel_file(file_path, country_code)

        # Créer les DataFrames et compter les doublons
        df_output = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
        nb_info_avant = len(df_output)
        df_output = df_output.drop_duplicates()
        nb_info_apres = len(df_output)
        nb_info_doublons = nb_info_avant - nb_info_apres

        df_contacts_sim = pd.DataFrame(contacts_sim, columns=CONTACTS_COLUMNS)
        nb_sim_avant = len(df_contacts_sim)
        df_contacts_sim = df_contacts_sim.drop_duplicates()
        nb_sim_apres = len(df_contacts_sim)
        nb_sim_doublons = nb_sim_avant - nb_sim_apres

        df_contacts_whatsapp = pd.DataFrame(contacts_whatsapp, columns=CONTACTS_COLUMNS)
        nb_wa_avant = len(df_contacts_whatsapp)
        df_contacts_whatsapp = df_contacts_whatsapp.drop_duplicates()
        nb_wa_apres = len(df_contacts_whatsapp)
        nb_wa_doublons = nb_wa_avant - nb_wa_apres

        df_call_log = pd.DataFrame(call_log, columns=CALL_LOG_COLUMNS)
        nb_call_avant = len(df_call_log)
        df_call_log = df_call_log.drop_duplicates()
        nb_call = len(df_call_log)
        nb_call_doublons = nb_call_avant - nb_call

        # Générer le nom du fichier de sortie
        base_name = os.path.splitext(file_name)[0]
        output_file_name = f"{base_name}_CURE.xlsx"
        output_file = os.path.join(OUTPUT_FOLDER, output_file_name)

        # Créer le fichier de sortie
        print(f"\n  → Création du fichier Excel : {output_file_name}")

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            if nb_info_apres > 0:
                df_output.to_excel(writer, sheet_name="Info_Perso", index=False)
                print(f"     ✓ Feuille Info_Perso créée")
            if nb_sim_apres > 0:
                df_contacts_sim.to_excel(writer, sheet_name="Feuil_Contacts", index=False)
                print(f"     ✓ Feuille Feuil_Contacts créée")
            if nb_wa_apres > 0:
                df_contacts_whatsapp.to_excel(writer, sheet_name="Feuil_What'sapp", index=False)
                print(f"     ✓ Feuille Feuil_What'sapp créée")
            if nb_call > 0:
                df_call_log.to_excel(writer, sheet_name="Feuil_Call", index=False)
                print(f"     ✓ Feuille Feuil_Call créée")

        # Afficher les résultats (seulement pour les feuilles non vides)
        if nb_info_apres > 0:
            print(f"  ✓ Info_Perso : {nb_info_apres} entrées  # {nb_info_doublons} doublon(s) supprimé(s)")
        if nb_sim_apres > 0:
            print(f"  ✓ Feuil_Contacts : {nb_sim_apres} entrées  # {nb_sim_doublons} doublon(s) supprimé(s)")
        if nb_wa_apres > 0:
            print(f"  ✓ Feuil_What'sapp : {nb_wa_apres} entrées  # {nb_wa_doublons} doublon(s) supprimé(s)")
        if nb_call > 0:
            print(f"  ✓ Feuil_Call : {nb_call} entrées  # {nb_call_doublons} doublon(s) supprimé(s)")

        print(f"  ✓ Fichier créé : {output_file_name}")

    print("\n" + "=" * 60)
    print(f"✓ Traitement terminé ! {len(files)} fichier(s) traité(s)")
    print("=" * 60)
