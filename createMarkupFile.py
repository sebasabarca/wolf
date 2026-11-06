from pathlib import Path
from datetime import datetime


def save_analysis(markdown_text, ticker="stock"):
    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker.lower()}_{timestamp}.md"
    file_path = reports_dir / filename

    file_path.write_text(markdown_text, encoding="utf-8")

    return file_path