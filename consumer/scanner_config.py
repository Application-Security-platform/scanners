# add scanner commands and images here

SCANNER_CONFIGS = {
    "sast": {
        "semgrep": {
            "image": "returntocorp/semgrep:latest",
            "command": [
                "semgrep",
                "--config=auto",
                "{source_path}",
                "--json",
                "--output",
                "{output_path}"
            ]
        },
    },
    "secrets": {
        "gitleaks": {
            "image": "zricethezav/gitleaks:latest",
            "command": [
                "gitleaks", "detect",
                "--source={source_path}",
                "--report-format=json",
                "--report-path={output_path}",
                "--exit-code=0"
            ]
        }
    }
}