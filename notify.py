#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

def get_observations(observation):
    species_in_observation = []

    # list(observation.children)[0].find_all("span", class_="sci_name")[0].text
    for species in observation.children:
        specie = species.find_all("span", class_="sci_name")[0].text
        species_in_observation.append(specie)

    return species_in_observation

def main():
    url = "https://www.ornitho.cat/index.php?m_id=4&sp_DOffset=2&mp_item_per_page=20&mp_current_page=1"
    page = requests.get(url)

    soup = BeautifulSoup(page.content, "html.parser")

    list_submenus = soup.find_all("div", class_="listSubmenu")

    list_observations = soup.find_all("div", class_="listObservation")

    for location, observation in zip(list_submenus, list_observations):
        print("Location:", location.text)
        observations_list = get_observations(observation)
        print(observations_list)

if __name__ == "__main__":
    main()