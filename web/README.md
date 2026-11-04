# Sponsor Scout

Enter a brand name to see its weighted fit score, benchmark placement, reasons, public sources and outreach route. Each confirmed result is added to or refreshed in the **Prospect Research** tab. The rank compares against the reviewed baseline from the Python repo. Missing evidence is shown as unknown and AI research is provisional until a human verifies it.

## Google Apps Script deployment

1. Create a standalone Apps Script project owned by the person who will run Sponsor Scout. Copy in `Code.gs`, `Benchmark.gs` and the HTML file named `Index`. Enable **Show appsscript.json manifest file in editor** in Project Settings and copy in the manifest.
2. In **Project Settings → Script properties**, add `GEMINI_API_KEY` from a [Google AI Studio Free Tier project](https://aistudio.google.com/api-keys) as a project secret. Saved profiles work without an API key.
3. Select **Deploy → New deployment → Web app**. Set **Execute as** to your account and **Who has access** to **Only myself**. Authorize the spreadsheet and external request scopes, then open the deployment URL. The account needs edit access to the destination workbook.
4. Try `UTA` to check the baseline workflow. For a new brand, enter its name and optionally its official website. Confirm the new row in **Prospect Research**.

The app uses Gemini 2.5 Flash and falls back to Gemini 3.5 Flash-Lite when Google denies access to the older model. Gemini suggests candidate URLs, then checks them with URL Context. Only successfully retrieved public URLs can support evidence. Add the brand’s official website when name-only discovery is inconclusive. Use a Free Tier project with billing disabled to keep the API calls free. Keep the Apps Script project private because editors can access its properties. The research score is an outreach fit measure.

Regenerate the benchmark after editing the weights or reviewed sponsor dataset with `python web/build.py`, then copy the updated file and deploy a new version.
