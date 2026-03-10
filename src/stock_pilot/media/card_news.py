"""Card news image generation via HTML/CSS + Puppeteer."""
from __future__ import annotations
import json, logging, subprocess, tempfile
from pathlib import Path
from stock_pilot.content.generator import ContentPackage

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _render_html(pkg: ContentPackage, chart_b64: str = "") -> str:
    """Render card news HTML from template."""
    tmpl = (TEMPLATE_DIR / "card_news.html").read_text(encoding="utf-8")
    sign = "▲" if pkg.change_pct > 0 else ("▼" if pkg.change_pct < 0 else "■")
    color = "#00e676" if pkg.change_pct > 0 else ("#ff5252" if pkg.change_pct < 0 else "#ffd740")
    return (
        tmpl
        .replace("{{SYMBOL}}", pkg.symbol)
        .replace("{{PRICE}}", f"${pkg.price:,.2f}")
        .replace("{{CHANGE}}", f"{sign} {abs(pkg.change_pct):.2f}%")
        .replace("{{CHANGE_COLOR}}", color)
        .replace("{{TITLE}}", pkg.card_title)
        .replace("{{SUBTITLE}}", pkg.card_subtitle)
        .replace("{{BODY}}", pkg.card_body.replace("\n", "<br>"))
        .replace("{{CHART_B64}}", chart_b64)
    )


def generate_card_news(pkg: ContentPackage, output_path: Path, chart_b64: str = "") -> bool:
    """Generate card news PNG. Returns True on success."""
    html = _render_html(pkg, chart_b64)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        html_path = f.name

    puppet_script = _get_puppet_script(html_path, str(output_path))
    script_path = Path(tempfile.mktemp(suffix=".mjs"))
    script_path.write_text(puppet_script, encoding="utf-8")

    try:
        result = subprocess.run(
            ["node", str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("Puppeteer failed: %s", result.stderr)
            return False
        return output_path.exists()
    except FileNotFoundError:
        logger.error("node not found — install Node.js to use card news generation")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Puppeteer timed out")
        return False
    finally:
        Path(html_path).unlink(missing_ok=True)
        script_path.unlink(missing_ok=True)


def _get_puppet_script(html_path: str, output_path: str) -> str:
    return f"""
import puppeteer from 'puppeteer';
const browser = await puppeteer.launch({{args: ['--no-sandbox', '--disable-setuid-sandbox']}});
const page = await browser.newPage();
await page.setViewport({{width: 1080, height: 1080}});
await page.goto('file://{html_path}', {{waitUntil: 'networkidle0'}});
await page.screenshot({{path: '{output_path}', type: 'png', fullPage: false}});
await browser.close();
"""
