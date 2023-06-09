#!/usr/bin/env python3
import functools
import json
import re
import time
import random
from collections import namedtuple
from datetime import datetime
from typing import Optional

import requests
from pathlib import Path
from bs4 import BeautifulSoup

@functools.lru_cache(maxsize=None)
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
        try:
            specie = species.find_all("span", class_="sci_name")[0].parent.text
        except IndexError:
            specie = species.find_all("i")[1].text + " (TODO: this is a strange observation, getting species only?)"

        scientific_name = get_scientific_name(specie)
        english_name = translate_to_english(scientific_name)

        if english_name is not None:
            species_in_observation.append(specie + " " + english_name)
        else:
            species_in_observation.append(specie)

    return species_in_observation


def get_comarca_abbr(location: str) -> Optional[str]:
    """Get the comarca from the location name.

    Return the comarca abbreviation."""

    comarca_abbr = re.search(r"\(([A-Z]{3})\)", location)

    if comarca_abbr:
        return comarca_abbr.group(1)
    else:
        return None


def get_scientific_name(sighting: str) -> Optional[str]:
    scientific_name = re.search(r"\((.*)\)", sighting)

    if scientific_name:
        return scientific_name.group(1)
    else:
        return None

def debug_request(url: str, page):
    dir = Path.cwd() / "data/dumps"
    dir.mkdir(exist_ok=True)

    page_content = url + "\n\n" + page.text

    filename = datetime.now().strftime("%Y%m%d-%H%M%S.%f.html")
    # print("Requested page:", url)
    # print("Dump:", filename)

    Path(dir / filename).write_text(page_content)

def get_raw_sighting():
    for page_number in range(1, 150):
        url = f"https://www.ornitho.cat/index.php?m_id=4&sp_DOffset=1&mp_item_per_page=60&mp_current_page={page_number}"
        headers = {"User-Agent": "Estem provant un script per tenir unes notificacions, jc@pina.cat"}
        page = requests.get(url, headers=headers)

        debug_request(url, page)

        soup = BeautifulSoup(page.content, "html.parser")

        dates = soup.find_all("div", class_="listTop")
        if len(dates) == 0:
            # Finish iterating
            return

        date = dates[0].text

        list_locations = soup.find_all("div", class_="listSubmenu")

        list_species = soup.find_all("div", class_="listObservation")

        for location, species in zip(list_locations, list_species):
            species_list = get_species(species)
            yield {"location": location.text, "species": species_list, "date": date}

        time.sleep(random.randint(1, 5))


def get_all_sightings() -> dict:
    raw_sighting_generator = get_raw_sighting()

    sightings = {}

    for sighting in raw_sighting_generator:
        SightingKey = namedtuple("SightingKey", "location date")
        key = SightingKey(sighting["location"], sighting["date"])

        if key in sightings:
            sightings[key] += sighting["species"]
        else:
            sightings[key] = sighting["species"]

    return sightings

def get_next_sighting() -> dict:
    raw_sighting_generator = get_raw_sighting()
    previous = next(raw_sighting_generator)

    if previous is None:
        # Early in the morning there isn't the date?
        return {}

    for current_sighting in raw_sighting_generator:
        if current_sighting is None:
            break

        if previous["location"] == current_sighting["location"]:
            previous["species"] += current_sighting["species"]
        else:
            yield previous
            previous = current_sighting

def save_sightings(sighting: list[dict]):
    data = Path.cwd() / "data"
    data.mkdir(exist_ok=True)

    file = data / "sent.json"

    with file.open("w") as fp:
        json.dump(sighting, fp, indent=2)


def load_sightings() -> list[dict]:
    file = Path.cwd() / "data/sent.json"

    if not file.exists():
        return []

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

def get_sights_for_location_date(location: str, date: str, sightings: list[dict]) -> list[str]:
    for sighting in sightings:
        if sighting["location"] == location and sighting["date"] == date:
            return sighting["species"]

    return []


def print_new_sightings():
    sightings_previously_sent = load_sightings()

    all_current_sightings = get_all_sightings()

    all_sightings = []

    for location_date, species in all_current_sightings.items():
        species_previously_sent_for_location = get_sights_for_location_date(location_date.location, location_date.date, sightings_previously_sent)

        new_species = sorted(set(species) - set(species_previously_sent_for_location))
        sight_to_send = {"location": location_date.location, "date": location_date.date, "species": new_species}

        if len(new_species) > 0:
            send_sighting(sight_to_send)

        all_sightings.append({"location": location_date.location, "date": location_date.date, "species": species})

    save_sightings(all_sightings)


if __name__ == "__main__":
    print_new_sightings()
