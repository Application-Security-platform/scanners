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
        # "sonarqube": {
        #     "image": "sonarsource/sonar-scanner-cli:latest",
        #     "command": [
        #         "sonar-scanner",
        #         "-Dsonar.projectBaseDir={source_path}",
        #         "-Dsonar.projectKey={project_key}",
        #         "-Dsonar.sources=.",
        #         "-Dsonar.host.url={sonar_host}",
        #         "-Dsonar.java.binaries=."
        #     ]
        # }
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