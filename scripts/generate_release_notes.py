#!/usr/bin/env python3
"""
The Scribe's Scroll: Automated Release Note Generator for Candlekeep.
Synthesizes technical git history into a semi-D&D themed changelog via Gemini.
"""
import os
import subprocess
import sys
import google.generativeai as genai

def get_git_history():
    """Extracts commit history since the last tag."""
    try:
        # Get the most recent tag
        last_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD^"], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        # Get all merge commit messages (which usually contain PR titles)
        # and standard commits between last tag and HEAD
        history = subprocess.check_output(
            ["git", "log", f"{last_tag}..HEAD", "--oneline", "--no-merges"],
            stderr=subprocess.STDOUT
        ).decode().strip()
        
        return last_tag, history
    except subprocess.CalledProcessError:
        # Fallback if no tags exist
        history = subprocess.check_output(
            ["git", "log", "-n", "50", "--oneline", "--no-merges"],
            stderr=subprocess.STDOUT
        ).decode().strip()
        return "the dawn of time", history

def generate_arcane_notes(last_tag, history):
    """Uses Gemini to synthesize the technical history into a themed changelog."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")

    prompt = f"""
    You are the First Scribe of Candlekeep. Your task is to write the technical release notes 
    for version {os.getenv('CANDLEKEEP_VERSION', 'Next')}, summarizing the changes since {last_tag}.

    VOICE AND TONE:
    - Primarily Technical: 90% of the content must be clear, precise technical documentation for engineers.
    - D&D Flare: Use 10% "arcane library" flavor (e.g., refer to the server as the 'fortress', 
      features as 'arcane arts' or 'scrolls', and ingestion as 'cataloging').
    - Professional & Senior: You are an expert librarian, not a dungeon master. Keep it sophisticated.

    INPUT DATA (Git History):
    {history}

    OUTPUT STRUCTURE:
    1. A short, atmospheric opening (1-2 sentences).
    2. 'Major Features' (Categorize and explain the 'why' behind major changes).
    3. 'Infrastructure & Arcane Wards' (CI, Docker, performance, security).
    4. 'Minor Scrolls' (Bug fixes, chores, small updates).
    5. A short closing.

    Formatting: Use Markdown. Group related commits into single bullet points where it makes sense.
    Exclude noise like 'bump version' or 'fix typo' if they are redundant.
    """

    response = model.generate_content(prompt)
    return response.text

if __name__ == "__main__":
    tag, hist = get_git_history()
    print(generate_arcane_notes(tag, hist))
