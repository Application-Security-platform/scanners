def preprocess_gitleaks(data, organization_id, repo_name):
    """Preprocess Gitleaks data."""
    # Add custom preprocessing logic for Gitleaks data
    print(f"Preprocessing Gitleaks data for {repo_name}")

    processed_data = []
    for entry in data:
        temp={
            "description": entry.get('Description'),
            "start_line":entry.get('StartLine'),
            "end_line": entry.get('EndLine'),
            "start_column":entry.get('StartColumn'),
            "end_column": entry.get('EndColumn'),
            "match":entry.get('Match'),
            "secret":entry.get('Secret'),
            "file_path": f"/data/repos/{repo_name}/" + entry.get('File'),
            "symlink_file":entry.get('SymlinkFile'),
            "commit": entry.get('Commit'),
            "entropy":entry.get('Entropy'),
            "author":entry.get('Author'),
            "email": entry.get('Email'),
            "date":entry.get('Date'),
            "message":entry.get('Message'),
            "tags": entry.get('Tags'),
            "rule_id":entry.get('RuleID'),
            "gitleaks_fingerprint": entry.get('Fingerprint'),
        }
        # For example, we can filter out any low-severity findings
        
        processed_data.append({
            "organization_id": organization_id,
            "repo_name":repo_name,
            "source":"osint",
            "scanner_source":"gitleaks",
            **temp
        })
    return processed_data

def preprocess_trufflehog(data, organization_id, repo_name):
    """Preprocess Trufflehog data."""
    # Add custom preprocessing logic for Trufflehog data
    print(f"Preprocessing Trufflehog data for {repo_name}")
    processed_data = []
    for entry in data:
        # For example, we can filter out any low-severity findings
        processed_data.append({
            "organization_id": organization_id,
            "repo_name":repo_name,
            "source":"osint",
            "scanner_source":"trufflehog",
            **entry
        })
    return processed_data

def preprocess_semgrep(data, organization_id, repo_name):
    """Preprocess Semgrep data."""
    # Add custom preprocessing logic for Semgrep data
    print(f"Preprocessing Semgrep data for {repo_name}")
    processed_data = []
    for entry in data.get("results", []):
        # For example, we can filter out any low-severity findings
        temp = {
            "description": entry.get('extra',{}).get('message'),
            "start_line":entry.get('start',{}).get('line'),
            "end_line": entry.get('end',{}).get('line'),
            "start_column":entry.get('start',{}).get('col'),
            "end_column": entry.get('end',{}).get('col'),
            "match":entry.get('extra',{}).get('lines'),
            "secret":entry.get('Secret'),
            "file_path": entry.get('path'),
            "category":entry.get('extra',{}).get('metadata',{}).get('category'),
            "confidence":entry.get('extra',{}).get('metadata',{}).get('confidence'),
            "impact":entry.get('extra',{}).get('metadata',{}).get('impact'),
            "cwe":{i.split(': ')[0]:i.split(': ')[-1] for i in entry.get('extra',{}).get('metadata',{}).get('cwe',{})},
            "metadata": entry.get('extra',{}).get('metadata'),
            "metavars":entry.get('extra',{}).get('metavars'),
            "severity":entry.get('extra',{}).get('severity'),
            "rule_id":entry.get('check_id'),
            "semgrep_fingerprint": entry.get('extra',{}).get('fingerprint'),
            "is_ignored":entry.get('extra',{}).get('is_ignored'),
            "validation_state":entry.get('extra',{}).get('validation_state')
        }
        processed_data.append({
            "organization_id": organization_id,
            "repo_name":repo_name,
            "source":"osint",
            "scanner_source":"semgrep",
            **temp
        })
    return processed_data
