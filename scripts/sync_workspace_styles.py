"""Share native layout CSS and locally installed font files with Reflex."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    assets = ROOT / "reflex_demo/assets"
    assets.mkdir(parents=True, exist_ok=True)
    css = (ROOT / "frontend/src/styles.css").read_text()
    fonts = ROOT / "frontend/node_modules/@fontsource/instrument-sans/files"
    declarations = []
    for weight in (400, 500, 600):
        name = f"instrument-sans-latin-{weight}-normal.woff2"
        shutil.copy2(fonts / name, assets / name)
        declarations.append(f"@font-face{{font-family:'Instrument Sans';font-style:normal;font-weight:{weight};font-display:swap;src:url('/{name}') format('woff2');}}")
    overrides = ".save-button{background:var(--primary);color:#fff;border:0;border-radius:6px;padding:4px 10px}.decision-options button{border:0;background:transparent;border-radius:5px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}.evidence-drawer{transform:none!important;left:auto!important;top:0!important;bottom:0!important;right:0!important;margin:0!important;border-radius:0!important;}"
    overrides += ".save-button:disabled{background:var(--muted);color:var(--quiet);cursor:not-allowed}.workspace input::placeholder,.workspace textarea::placeholder{color:var(--quiet);opacity:1}.evidence-drawer{color:var(--ink);color-scheme:light;font:14px/1.5 'Instrument Sans',sans-serif}"
    (assets / "workspace.css").write_text("\n".join(declarations) + "\n" + css + "\n" + overrides)
    print("Reflex assets generated from shared CSS and installed font files.")


if __name__ == "__main__":
    main()
