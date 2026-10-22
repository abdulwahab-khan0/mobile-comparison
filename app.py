"""Mobile Comparison Assistant
Compare phones by specs and price-to-value using Google Gemini (Flash) and Streamlit.
"""

import json
import os
import re

import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

DEFAULT_MODEL = "gemini-3.8-flash"
MAX_PHONES = 4

SYSTEM_PROMPT = """You are an expert mobile phone analyst.
You will receive 2 to 4 phones. Each phone has a model name, an optional price,
and optionally a screenshot of its specifications.

Tasks:
1. For each phone, recall or read its key specs: processor/chipset, RAM, storage,
   display (size, type, refresh rate), main camera, battery (mAh) and charging
   speed, software support/updates, and build.
2. If a price is given, use it. If not, estimate a typical street price and say
   so in the "price_note" field. Never invent precision you do not have: if you
   are unsure about a spec, write "Unknown".
3. Score each phone from 0 to 10 for: performance, display, camera, battery,
   and overall value_for_money (specs relative to price).
4. Pick one winner for best value and one for best raw specs (they may differ).
5. Be honest and balanced. Do not exaggerate.

Return ONLY valid JSON, with this exact structure:
{
  "phones": [
    {
      "name": "string",
      "price": number or null,
      "currency": "string",
      "price_note": "string",
      "specs": {
        "chipset": "string",
        "ram": "string",
        "storage": "string",
        "display": "string",
        "camera": "string",
        "battery": "string",
        "other": "string"
      },
      "scores": {
        "performance": number,
        "display": number,
        "camera": number,
        "battery": number,
        "value_for_money": number
      },
      "pros": ["string"],
      "cons": ["string"]
    }
  ],
  "best_value": "name of the best price-to-value phone",
  "best_specs": "name of the phone with the best raw specs",
  "verdict": "short paragraph explaining the recommendation",
  "disclaimer": "short note that specs/prices should be verified"
}
"""

SCORE_KEYS = ["performance", "display", "camera", "battery", "value_for_money"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def get_api_key() -> str | None:
    """Read the Gemini API key from Streamlit secrets or environment."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # no secrets file present
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def get_model_name() -> str:
    try:
        if "GEMINI_MODEL" in st.secrets:
            return st.secrets["GEMINI_MODEL"]
    except Exception:
        pass
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def extract_json(text: str) -> dict:
    """Parse JSON from a model response, tolerating markdown code fences."""
    text = (text or "").strip()
    if not text:
        raise ValueError("The model returned an empty response.")
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def validate_result(data: dict) -> dict:
    """Make sure the response has the fields the UI needs."""
    if not isinstance(data, dict) or not isinstance(data.get("phones"), list) or not data["phones"]:
        raise ValueError("The model response did not contain a list of phones.")
    for phone in data["phones"]:
        phone.setdefault("name", "Unknown phone")
        try:
            phone["price"] = float(str(phone.get("price")).replace(",", "")) if phone.get("price") else None
        except (TypeError, ValueError):
            phone["price"] = None
        phone.setdefault("currency", "")
        phone.setdefault("price_note", "")
        phone.setdefault("specs", {})
        phone.setdefault("pros", [])
        phone.setdefault("cons", [])
        scores = phone.setdefault("scores", {})
        for key in SCORE_KEYS:
            try:
                value = float(scores.get(key, 0))
            except (TypeError, ValueError):
                value = 0.0
            scores[key] = max(0.0, min(10.0, value))
    data.setdefault("best_value", "")
    data.setdefault("best_specs", "")
    data.setdefault("verdict", "")
    data.setdefault("disclaimer", "Verify specs and prices before buying.")
    return data


def build_contents(phones: list[dict]) -> list:
    """Build the multimodal content list for Gemini."""
    contents: list = ["Compare these phones:\n"]
    for i, phone in enumerate(phones, start=1):
        price_text = (
            f"{phone['price']} {phone['currency']}".strip()
            if phone["price"]
            else "not provided (please estimate)"
        )
        contents.append(f"Phone {i}: {phone['name']} | Price: {price_text}")
        if phone.get("image") is not None:
            contents.append(f"Specification screenshot for Phone {i}:")
            contents.append(phone["image"])
    return contents


def compare_phones(phones: list[dict], api_key: str, model: str) -> dict:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=build_contents(phones),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )
    return validate_result(extract_json(response.text))


def value_ranking(data: dict) -> list[tuple[str, float]]:
    """Rank phones by value_for_money score, highest first."""
    ranked = [(p["name"], p["scores"]["value_for_money"]) for p in data["phones"]]
    return sorted(ranked, key=lambda item: item[1], reverse=True)


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
def render_results(data: dict) -> None:
    phones = data["phones"]

    st.subheader("🏆 Result")
    col1, col2 = st.columns(2)
    col1.metric("Best price-to-value", data["best_value"] or "-")
    col2.metric("Best raw specs", data["best_specs"] or "-")
    if data["verdict"]:
        st.info(data["verdict"])

    st.subheader("📊 Specifications")
    table = {}
    for p in phones:
        price = f"{p['price']:,.0f} {p['currency']}".strip() if p.get("price") else "N/A"
        specs = p["specs"]
        table[p["name"]] = {
            "Price": price,
            "Chipset": specs.get("chipset", "Unknown"),
            "RAM": specs.get("ram", "Unknown"),
            "Storage": specs.get("storage", "Unknown"),
            "Display": specs.get("display", "Unknown"),
            "Camera": specs.get("camera", "Unknown"),
            "Battery": specs.get("battery", "Unknown"),
            "Other": specs.get("other", ""),
        }
    st.dataframe(table)
    notes = [f"**{p['name']}**: {p['price_note']}" for p in phones if p.get("price_note")]
    if notes:
        st.caption("Price notes — " + " | ".join(notes))

    st.subheader("⭐ Scores (0–10)")
    score_table = {
        p["name"]: {k.replace("_", " ").title(): p["scores"][k] for k in SCORE_KEYS}
        for p in phones
    }
    st.bar_chart(score_table)

    st.subheader("💰 Value for money ranking")
    for rank, (name, score) in enumerate(value_ranking(data), start=1):
        st.write(f"{rank}. **{name}** — {score:.1f}/10")

    st.subheader("👍 Pros and 👎 Cons")
    cols = st.columns(len(phones))
    for col, p in zip(cols, phones):
        with col:
            st.markdown(f"**{p['name']}**")
            for pro in p["pros"]:
                st.markdown(f"✅ {pro}")
            for con in p["cons"]:
                st.markdown(f"⚠️ {con}")

    st.caption(data["disclaimer"])


def main() -> None:
    st.set_page_config(page_title="Mobile Comparison Assistant", page_icon="📱", layout="wide")
    st.title("📱 Mobile Comparison Assistant")
    st.write(
        "Enter 2–4 phone models (and prices if you know them). "
        "The AI compares specs and tells you which gives the best value."
    )

    api_key = get_api_key()
    model = get_model_name()
    if not api_key:
        st.error(
            "No Gemini API key found. Set `GEMINI_API_KEY` in `.streamlit/secrets.toml` "
            "(or Streamlit Cloud secrets) or as an environment variable."
        )
        st.stop()

    count = st.number_input("Number of phones", min_value=2, max_value=MAX_PHONES, value=2, step=1)

    phones: list[dict] = []
    columns = st.columns(int(count))
    for i, col in enumerate(columns):
        with col:
            st.markdown(f"#### Phone {i + 1}")
            name = st.text_input("Model name", key=f"name_{i}", placeholder="e.g. Samsung Galaxy S24")
            price = st.number_input(
                "Price (optional, 0 = estimate)", min_value=0.0, value=0.0, step=1000.0, key=f"price_{i}"
            )
            currency = st.text_input("Currency", value="PKR", key=f"cur_{i}")
            upload = st.file_uploader(
                "Spec screenshot (optional)", type=["png", "jpg", "jpeg", "webp"], key=f"img_{i}"
            )
            image = None
            if upload is not None:
                try:
                    image = Image.open(upload)
                    image.load()
                    st.image(image)
                except Exception:
                    st.warning("Could not read that image; it will be ignored.")
                    image = None
            phones.append(
                {"name": name.strip(), "price": price or None, "currency": currency.strip(), "image": image}
            )

    if st.button("Compare phones", type="primary"):
        if any(not p["name"] for p in phones):
            st.warning("Please enter a model name for every phone.")
            st.stop()
        names = [p["name"].lower() for p in phones]
        if len(set(names)) != len(names):
            st.warning("Each phone must be different.")
            st.stop()

        with st.spinner("Analyzing phones..."):
            try:
                st.session_state["result"] = compare_phones(phones, api_key, model)
            except Exception as exc:  # show a friendly error instead of a traceback
                st.session_state.pop("result", None)
                st.error(f"Something went wrong while contacting Gemini: {exc}")

    if "result" in st.session_state:
        render_results(st.session_state["result"])


if __name__ == "__main__":
    main()
