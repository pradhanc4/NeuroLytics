from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_directories_exist():
    required_directories = [
        "backend",
        "database",
        "ml",
        "analytics",
        "features",
        "models",
        "ranking",
        "backtesting",
        "frontend",
        "tests",
        "reports",
        "scripts",
        "docs",
    ]

    for directory in required_directories:
        assert (PROJECT_ROOT / directory).is_dir()


def test_required_files_exist():
    required_files = [
        "README.md",
        "PROJECT_STATUS.md",
        "CHANGELOG.md",
        "requirements.txt",
        ".gitignore",
        ".env.example",
        "run.py",
    ]

    for file_name in required_files:
        assert (PROJECT_ROOT / file_name).is_file()