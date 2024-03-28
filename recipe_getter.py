import json
import os
import requests
import streamlit as st

@st.cache_data(show_spinner='Fetching recipe from Tasty API...')
def get_recipe(recipe_dash):
    """
    this function gets recipe given 'recipe-name'
    and stores it in json format
    """
    url = "https://tasty.p.rapidapi.com/recipes/list"
    params = {
        "from": "0",
        "size": "1",
        "q": recipe_dash
    }
    headers = {
        # os.getenv() gets key from env
        "X-RapidAPI-Key": os.getenv('TASTY_API_KEY'),
        "X-RapidAPI-Host": "tasty.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=params)
    recipe = response.json()['results'][0]
    
    return recipe
