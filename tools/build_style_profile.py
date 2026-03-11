import json
import os
import sys

import anthropic
from dotenv import load_dotenv

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))


def load_samples():
    """Load writing samples from data/writing_samples.json."""
    path = os.path.join(_project_root, "data", "writing_samples.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            "data/writing_samples.json not found.\n"
            "Run this first:  python -m tools.collect_writing_samples"
        )
    with open(path) as f:
        return json.load(f)


def build_style_profile(samples=None):
    """Analyze writing samples with Claude and save a style guide to data/style_profile.md.

    Returns the generated profile text.
    """
    if samples is None:
        samples = load_samples()

    if not samples:
        print("No writing samples found. Add emails to data/writing_samples.json first.")
        return None

    # Build sample text blocks — use up to 20, skip empties
    sample_texts = []
    for s in samples[:20]:
        body = s.get("body", "").strip()
        if not body:
            continue
        subj = s.get("subject", "")
        to = s.get("to", "")
        context = f"Subject: {subj}"
        if to:
            context += f" | To: {to}"
        sample_texts.append(f"--- ({context}) ---\n{body}")

    if not sample_texts:
        print("No email bodies found in samples. Nothing to analyze.")
        return None

    samples_block = "\n\n".join(sample_texts)

    prompt = f"""Below are real emails this person wrote. Analyze them carefully and write a detailed, specific writing style guide so an AI can generate emails that sound exactly like them.

EMAILS WRITTEN BY THIS PERSON:
{samples_block}

---

Write a style guide in Markdown covering these sections. Be concrete and specific — quote real phrases from the examples where useful. This guide will be fed directly into an AI to generate draft replies in this person's voice.

## Greeting
How do they open emails? (Hi vs Hello vs Hey, first name only vs full name, any punctuation after the greeting, etc.)

## Tone
What's the overall feel? (casual, formal, warm, direct, brief, chatty, etc.) What specific language choices signal this?

## Length & Structure
Typical email length (short/medium/long). How do they organize their thoughts? Do they use bullet points, paragraphs, numbered lists?

## Sign-off
How do they close? (sign-off word/phrase, how they write their name, anything after the name)

## Vocabulary & Phrases
Words or phrases they favor. Expressions they use often. How formal or casual is their word choice?

## Punctuation & Formatting
Comma usage, use of contractions, capitalization, ellipses, exclamation points, question marks. Any quirks.

## What to Avoid
Things they clearly don't do — filler phrases, over-formal language, unnecessary padding, etc.

Write the guide to be immediately usable. An AI reading this guide should be able to write a reply that sounds like this person wrote it."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

    print(f"Analyzing {len(sample_texts)} email samples with {model}...")
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    profile_body = response.content[0].text

    os.makedirs(os.path.join(_project_root, "data"), exist_ok=True)
    output_path = os.path.join(_project_root, "data", "style_profile.md")
    with open(output_path, "w") as f:
        f.write("# My Writing Style Guide\n\n")
        f.write(
            "*Auto-generated from your sent emails. "
            "Edit this file freely — it's the source of truth for your style.*\n\n"
        )
        f.write(profile_body)

    print(f"\nStyle profile saved to data/style_profile.md")
    print("Open the file and tweak anything that doesn't sound like you.")
    return profile_body


if __name__ == "__main__":
    build_style_profile()
