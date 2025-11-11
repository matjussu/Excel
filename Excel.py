import os
import pandas as pd
import re

folder_path = "INPUT"
output_folder = "OUTPUT"
os.makedirs(output_folder, exist_ok=True)

CONTACTS_SHEET_NAME = "Contacts"
EMAIL_COLUMN = "Email"

social_patterns = [
    ("facebook", r"(?:https?://)?(?:www\.|m\.|mobile\.)?facebook\.com/(?:profile\.php\?id=\d+|[a-zA-Z0-9\.]+)/?"),
    ("linkedin", r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9\-]+/?"),
    ("instagram", r"(?:https?://)?(?:www\.)?instagram\.com/[a-zA-Z0-9_\.]+/?"),
    ("twitter", r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9_]+/?"),
    ("youtube", r"(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|user/|@)?[a-zA-Z0-9_\-]+/?"),
    ("tiktok", r"(?:https?://)?(?:www\.)?tiktok\.com/@[a-zA-Z0-9_\.]+/?"),
]

web_patterns = [
    ("website_with_protocol", r"https?://(?:www\.)?[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?:/[^\s]*)?"),
    ("website_www", r"\bwww\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?"),
]

email_patterns = [
    ("email", r"\b[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}@[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b")
]

phone_patterns = [
    ("phone_international", r"\+\d{1,3}[\s\.-]?\(?\d{1,4}\)?[\s\.-]?\d{1,4}[\s\.-]?\d{1,4}[\s\.-]?\d{1,9}"),
    ("phone_fr_fixe", r"\b0[1-59]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\b"),
    ("phone_fr_mobile", r"\b0[67]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{2}\b"),
]

local_phone_patterns = [
    ("phone_with_parens", r"\(\d{2,4}\)\s?\d{2,4}[\s\.-]?\d{2,4}[\s\.-]?\d{2,4}"),
    ("phone_local", r"\b\d{2}[\s\.-]\d{2}[\s\.-]\d{2}[\s\.-]\d{2}[\s\.-]\d{2}\b"),
]

all_patterns_groups = [
    ("emails", "email", email_patterns),
    ("phones", "phone", phone_patterns),
    ("social", "social", social_patterns),
    ("websites", "website", web_patterns),
    ("local_phones", "local_phone", local_phone_patterns)
]

def process_excel_file(file_path):
    """Analyse un fichier Excel et extrait les emails, téléphones, réseaux sociaux et sites web"""
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None, None, None, None

    results = []
    social_links = []
    summary_counts = []
    filtered_contacts = pd.DataFrame(columns=[EMAIL_COLUMN])

    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception as e:
            print(f"Error reading sheet {sheet_name} from {file_path}: {e}")
            continue

        for row_idx, row in df.iterrows():
            for col_idx, cell in enumerate(row):
                if pd.isna(cell) or str(cell).strip() == '':
                    continue

                if len(str(cell).strip()) < 3:
                    continue

                if col_idx == 0:
                    continue

                cell_str = str(cell).lower()

                for group_name, pattern_name, patterns in all_patterns_groups:
                    for label, pattern in patterns:
                        matches = re.findall(pattern, cell_str)
                        if matches:
                            for match in matches:
                                value = match[0] if isinstance(match, tuple) else match
                                results.append({
                                    "file_path": os.path.basename(file_path),
                                    "sheet_name": sheet_name,
                                    "row": row_idx,
                                    "column": col_idx,
                                    "label": label,
                                    "group": group_name,
                                    "value": value,
                                    "original_text": cell_str
                                })
                                
                                summary_counts.append({
                                    "file_path": os.path.basename(file_path),
                                    "sheet_name": sheet_name,
                                    "group": group_name,
                                    "label": label
                                })

                                if group_name == "social":
                                    social_links.append(cell_str)

    if CONTACTS_SHEET_NAME in xls.sheet_names:
        try:
            df_contacts = pd.read_excel(xls, sheet_name=CONTACTS_SHEET_NAME, header=0)
            if EMAIL_COLUMN in df_contacts.columns:
                df_contacts = df_contacts.dropna(subset=[EMAIL_COLUMN])
                df_contacts["file_path"] = os.path.basename(file_path)

                df_contacts[EMAIL_COLUMN] = df_contacts[EMAIL_COLUMN].str.split(r'[;, ]')

                filtered_contacts = df_contacts.explode(EMAIL_COLUMN)
                filtered_contacts[EMAIL_COLUMN] = filtered_contacts[EMAIL_COLUMN].str.strip()

                filtered_contacts = filtered_contacts[filtered_contacts[EMAIL_COLUMN].str.contains('@', na=False)]
                filtered_contacts = filtered_contacts[~filtered_contacts[EMAIL_COLUMN].str.contains(r'[\(\)]', na=False)]
                filtered_contacts = filtered_contacts[filtered_contacts[EMAIL_COLUMN].str.len() > 5]
                filtered_contacts = filtered_contacts.dropna(subset=[EMAIL_COLUMN])
                filtered_contacts = filtered_contacts[filtered_contacts[EMAIL_COLUMN] != '']

                email_regex = r"^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}@[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
                filtered_contacts = filtered_contacts[filtered_contacts[EMAIL_COLUMN].str.match(email_regex, na=False)]

        except Exception as e:
            print(f"Error processing sheet {CONTACTS_SHEET_NAME} from {file_path}: {e}")
    
    return results, social_links, summary_counts, filtered_contacts


if __name__ == "__main__":
    all_results = []
    all_social_links = []
    all_summary_counts = []
    all_contacts = []

    files = [f for f in os.listdir(folder_path) if f.endswith('.xlsx')]

    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        print(f"Processing {file_name}...")

        results, social_links, summary_counts, contacts = process_excel_file(file_path)

        if results:
            all_results.extend(results)
            all_social_links.extend(social_links)
            all_summary_counts.extend(summary_counts)
            if contacts is not None:
                all_contacts.append(contacts)

    df_results = pd.DataFrame(all_results)
    df_social_links = pd.DataFrame(all_social_links, columns=["SocialLinks"])
    df_social_links = df_social_links.drop_duplicates()

    df_summary = pd.DataFrame(all_summary_counts)
    if not df_summary.empty:
         df_summary = df_summary.groupby(["file_path", "sheet_name", "group", "label"]).size().reset_index(name='count')

    if all_contacts:
        df_all_contacts = pd.concat(all_contacts, ignore_index=True)
        df_all_contacts_unique = df_all_contacts.drop_duplicates(subset=[EMAIL_COLUMN])
    else:
        df_all_contacts = pd.DataFrame(columns=[EMAIL_COLUMN])
        df_all_contacts_unique = pd.DataFrame(columns=[EMAIL_COLUMN])

    output_file = os.path.join(output_folder, "final_report_core.xlsx")
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:

        df_group_summary = pd.DataFrame()
        if not df_results.empty:
            df_group_summary = df_results.groupby('group').size().reset_index(name='count')

            for group_name in df_results['group'].unique():
                df_group = df_results[df_results['group'] == group_name]
                df_group.to_excel(writer, sheet_name=group_name, index=False)

        df_results.to_excel(writer, sheet_name="all_results", index=False)
        df_group_summary.to_excel(writer, sheet_name="group_summary", index=False)
        df_social_links.to_excel(writer, sheet_name="SocialNetworks", index=False)
        df_all_contacts_unique.to_excel(writer, sheet_name="EmailContacts", index=False)
        df_summary.to_excel(writer, sheet_name="summary_counts", index=False)

    print(f"Export termine : {output_file}")