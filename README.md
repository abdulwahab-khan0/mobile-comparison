# 📱 Mobile Comparison Assistant

A Streamlit app that compares 2–4 phones and tells you which one gives the best
price-to-value, using Google's Gemini Flash model.

## Features

- Enter 2–4 phone model names, with an optional price and currency
- Optionally upload a spec screenshot for each phone (Gemini reads the image)
- Side-by-side spec table, 0–10 scores (performance, display, camera, battery, value)
- Best price-to-value pick, best raw-specs pick, and a written verdict
- Pros and cons for every phone

## Project structure

```
.
├── app.py             # Streamlit app
├── requirements.txt   # Python dependencies
└── README.md
```

## Run locally

1. Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. Install dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Add your key. Create `.streamlit/secrets.toml`:

   ```toml
   GEMINI_API_KEY = "your-key-here"
   # Optional: change the model (default is gemini-2.5-flash)
   # GEMINI_MODEL = "gemini-2.5-flash"
   ```

   Or set an environment variable instead: `export GEMINI_API_KEY="your-key-here"`

4. Start the app:

   ```bash
   streamlit run app.py
   ```

## Deploy on Streamlit Community Cloud

1. Push this project to GitHub (never commit `secrets.toml`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **Create app**, pick your repo, branch `main`, and main file `app.py`.
4. Open **Advanced settings → Secrets** and paste:

   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```

5. Click **Deploy**.

## Notes

- Specs and prices come from the AI model's knowledge (or your screenshot), so they can
  be outdated or wrong. Always verify before buying.
- If Gemini renames or retires a model, set `GEMINI_MODEL` in your secrets to a current
  Flash model name.
