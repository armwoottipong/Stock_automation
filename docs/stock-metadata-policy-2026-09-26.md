# Stock metadata policy check — 2026-09-26

This project stores one English metadata catalog per asset set and exports platform CSV files. The catalog records the content's actual origin separately from buyer-facing titles and keywords. An exporter rejects a generative-AI catalog for Shutterstock. A CSV is a metadata sidecar; it does not write IPTC/EXIF/XMP into the image.

## Platform requirements used by the exporter

| Topic | Adobe Stock | Shutterstock |
| --- | --- | --- |
| AI-generated contributor content | Accepted if rights and quality conditions are met; select **Created using generative AI tools** in Contributor Portal | [Not accepted from contributors](https://submit.shutterstock.com/help/en/articles/10594622-content-policy-updates-ai-generated-content) |
| CSV fields | `Filename,Title,Keywords,Category,Releases`; first three populated | `Filename,Description,Keywords,Categories`; all four populated |
| Text | Descriptive title, at most 70 characters and no commas/special characters; English catalog assumes Adobe account metadata language is English | English factual description; exporter uses at most 150 characters to satisfy the stricter submission UI limit |
| Keywords | 7–49 unique relevant phrases, most important first; 49 is conservative against Adobe's 49/50 guidance | 7–50 relevant unique English phrases |
| Category | Optional numeric CSV field; left blank for portal selection | One required category, using `Food and drink` for eligible real fruit photos |
| Files | This fruit set's transparent PNG cutouts can be considered under Adobe's PNG requirements: 4–100 MP, sRGB, transparency, at most 45 MB | JPEG or TIFF technical requirements apply to eligible non-AI image submissions |

Adobe sources: [CSV requirements](https://helpx.adobe.com/stock/contributor/manage-your-portfolio/csv-requirements-content.html), [title and keyword guidance](https://helpx.adobe.com/stock/contributor/content-policies-guidelines/metadata/tips-effective-titles-keywords.html), [AI submission steps](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-generative-ai-content/submit-generative-ai-content.html), [transparent PNG requirements](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-pngs/technical-requirements-png-submission.html), and [similarity guidance](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-generative-ai-content/distinct-generative-ai-submission-best-practices.html).

Shutterstock sources: [AI submission policy](https://submit.shutterstock.com/help/en/articles/10594622-content-policy-updates-ai-generated-content), [contextual metadata](https://submit.shutterstock.com/help/en/articles/10617427-content-publishing-standards-contextual-metadata), [CSV instructions](https://submit.shutterstock.com/help/en/articles/10617486-how-do-i-include-existing-metadata-with-my-content-submission), [submission UI requirements](https://submit.shutterstock.com/help/en/articles/10617414-portfolio-preparing-your-uploaded-content-for-submission), and [image file requirements](https://submit.shutterstock.com/help/en/articles/10617390-what-are-the-technical-requirements-for-images).

## Fruit set status

`output/fruit_isolates_2026-09-26/metadata/catalog.json` describes all 25 cutouts. `adobe_stock_draft.csv` uses the cutout filenames, English titles and ordered keywords. The file names were checked against Adobe's 30-character CSV limit. The catalog records `source_type: generative_ai` and `shutterstock_eligible: false`; the CSV deliberately has no AI keyword because Adobe asks for a visual subject title and a separate portal disclosure.

These are **draft metadata**, not a cleared upload set. Every image still needs full-size review for anatomy, edge quality, text, logo, branding and excessive similarity. Confirm the image-generation tool's commercial stock licensing rights. Verify or embed an sRGB profile on submission PNGs; the current cutout PNGs have no embedded ICC profile. Recheck file size and Adobe's PNG upload rules. In the Adobe portal choose the correct category and select the AI disclosure checkbox before any submission. The 25 fruit variants should be curated for distinctness; do not automatically submit all five of each fruit.

The Shutterstock exporter is for future genuine eligible photography. Use truthful `source_type: camera_photo`, English factual metadata, a supported JPEG/TIFF asset set and a valid category. Policy and platform UI rules may change; recheck official guidance before uploading.

## Commands

```powershell
python scripts/fruit_metadata.py
python scripts/export_stock_metadata.py --catalog output/fruit_isolates_2026-09-26/metadata/catalog.json --assets output/fruit_isolates_2026-09-26/cutout --platform adobe --output output/fruit_isolates_2026-09-26/metadata/adobe_stock_draft.csv
```

The corresponding Shutterstock command fails for this AI set by design. Neither command uploads images or metadata.
