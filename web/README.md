# Sponsor Scout

Enter a brand name to see its weighted fit score, benchmark placement, reasons, public sources and outreach route. Each confirmed result is added to or refreshed in the **Prospect Research** tab. The rank compares against the reviewed baseline from the Python repo. Missing evidence is shown as unknown and AI research is provisional until a human verifies it.

## Google Apps Script deployment

1. Create a standalone Apps Script project owned by the person who will run Sponsor Scout. Copy in `Code.gs`, `Benchmark.gs` and the HTML file named `Index`. Enable **Show appsscript.json manifest file in editor** in Project Settings and copy in the manifest.
2. In **Project Settings → Script properties**, add `OPENAI_API_KEY` as a project secret. The optional `OPENAI_RESEARCH_MODEL` overrides the default web search model. Saved profiles work without an API key.
3. Select **Deploy → New deployment → Web app**. Set **Execute as** to your account and **Who has access** to **Only myself**. Authorize the spreadsheet and external request scopes, then open the deployment URL. The account needs edit access to the destination workbook.
4. Try `UTA` to check the baseline workflow. For a new brand, enter its name and optionally its official website. Confirm the new row in **Prospect Research**.

The app sends only the prospect name and optional website hint to the OpenAI Responses API. Keep the project private because script editors can access project properties. API calls for live research use the selected project's billing. The research score is an outreach fit measure.

Regenerate the benchmark after editing the weights or reviewed sponsor dataset with `python web/build.py`, then copy the updated file and deploy a new version.
