# v0.3.0 Beta 2 Screenshots

These images were captured from the real local application and native HTML generators on September 1, 2026.

| File | Evidence |
|---|---|
| `workbench-overview.png` | Infinite-canvas workbench with real HTML palette and live node previews |
| `guided-creation.png` | Text requirement analysis and recommended composition |
| `gallery-preview.png` | Complete HTML template preview and page extraction |
| `ai-settings.png` | User-managed OpenAI-compatible / Ollama configuration |
| `workbench-night.png` | Pixel Night theme |
| `output-landing.png` | Native landing-page generator output |
| `output-dashboard.png` | Native dashboard generator output |
| `output-deck.png` | Native presentation-deck generator output |
| `output-poster.png` | Native poster generator output |
| `output-archdoc.png` | Native architecture-document generator output |

Capture and verification commands:

```bash
python e2e_verify.py
python -m pytest tests -q -p no:cacheprovider
```

Raw evidence is stored in `docs/test-evidence/`.