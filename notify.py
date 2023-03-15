#!/usr/bin/env python3
import json
import re
from typing import Optional

import requests
from pathlib import Path
from bs4 import BeautifulSoup

def translate_to_english(scientific_name: str) -> Optional[str]:
    translations_file = Path.cwd() / "data/translations.html"

    soup = BeautifulSoup(translations_file.read_bytes(), "html.parser")

    table = soup.find_all("table", id="species")[0]

    latin_column = 0
    english_column = 1

    first = True
    for row in table.find_all("tr"):
        if first:
            first = False
            continue

        tds = row.find_all("td")
        if tds[latin_column].text == scientific_name:
            return tds[english_column].text

    return None

def get_species(observation):
    species_in_observation = []

    for species in observation.children:
        specie = species.find_all("span", class_="sci_name")[0].parent.text
        scientific_name = get_scientific_name(specie)
        english_name = translate_to_english(scientific_name)

        if english_name is not None:
            species_in_observation.append(specie + " " + english_name)
        else:
            species_in_observation.append(specie)

    return species_in_observation


def get_comarca_abbr(location: str) -> str:
    """Get the comarca from the location name.

    Return the comarca abbreviation."""

    comarca_abbr = re.findall("[A-Z]{3}", location)[0]

    return comarca_abbr

def get_scientific_name(sighting: str) -> Optional[str]:
    scientific_name = re.search(r"\((.*)\)", sighting)

    if scientific_name:
        return scientific_name.group(1)
    else:
        return None


def get_raw_sighting():
    for page in range(0, 20):
        url = f"https://www.ornitho.cat/index.php?m_id=4&sp_DOffset=2&mp_item_per_page=20&mp_current_page={page}"

        page = requests.get(url)

        soup = BeautifulSoup(page.content, "html.parser")

        list_locations = soup.find_all("div", class_="listSubmenu")

        list_species = soup.find_all("div", class_="listObservation")

        for location, species in zip(list_locations, list_species):
            species_list = get_species(species)
            yield {"location": location.text, "species": species_list}

def get_next_sighting() -> dict:
    raw_sighting_generator = get_raw_sighting()
    previous = next(raw_sighting_generator)

    for current_sighting in raw_sighting_generator:
        if previous["location"] == current_sighting["location"]:
            previous["species"] += current_sighting["species"]
        else:
            yield previous
            previous = current_sighting

def save_sighting(sighting: dict):
    data = Path.cwd() / "data"
    data.mkdir(exist_ok=True)

    file = data / "last_sent.json"

    with file.open("w") as fp:
        json.dump(sighting, fp, indent=2)


def load_sighting() -> dict:
    file = Path.cwd() / "data/last_sent.json"

    if not file.exists():
        return {}

    with file.open("r") as fp:
        return json.load(fp)


def format_sighting(sighting: dict) -> str:
    formatted = ""
    formatted += f"Location: {sighting['location']}\n"
    formatted += f"Comarca: {get_comarca_abbr(sighting['location'])}\n"

    for species in sighting["species"]:
        formatted += f"  {species}\n"

    return formatted


def send_sighting(sighting: dict) -> None:
    print(format_sighting(sighting))


def print_new_sightings():
    last_notified = load_sighting()

    for index, sighting in enumerate(get_next_sighting()):
        if sighting == last_notified:
            # This sighting was already sent - finish
            return

        if index > 20:
            # Do not send more than 20...
            return

        if index == 0:
            # Current one is going to be sent, save it to avoid
            # resending it later
            save_sighting(sighting)

        send_sighting(sighting)

if __name__ == "__main__":
    print_new_sightings()
