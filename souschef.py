import recipe_getter
import recipe_parser
import recipe_visualizer
import streamlit as st

# spacy and matplotlib needed to be installed in .venv

# cached data
# get_recipe
# parse_ingredients
# broken_barh

st.set_page_config(layout="wide")
st.markdown("<h1 style='text-align: left; color: #f46524;'>SousChef.ai</h1>", unsafe_allow_html=True)
st.write('What would you like to cook, home chef?')

# text_input box should only take 1/2 of screen
col1, _ = st.columns([1, 1])
url = col1.text_input(label='What would you like to cook, home chef?',
                      placeholder='https://tasty.co/recipe/classic-chicken-noodle-soup',
                      label_visibility='collapsed')

def parse_url(s):
    """
    this function extracts dashed version of recipe name for tasty api
    and non-dashed version for presentation
    """
    recipe_dash = s[s.rindex('/')+1:]
    recipe = s[s.rindex('/')+1:].replace('-', ' ')
    return recipe_dash, recipe

# if url starts with 'https://tasty.co/recipe/' and the rest only contains alphabets and dashes
if url.startswith('https://tasty.co/recipe/'):
    recipe_dash, recipe = parse_url(url)
    st.write('')
    st.write(f'Check out the following plan for {recipe}:')
    
    recipe = recipe_getter.get_recipe(recipe_dash)
    
    # get ingredients
    ingred_list = [i['ingredient']['name'].lower() for i in recipe['sections'][0]['components'] \
                   if (i['ingredient'] is not None) and (i['ingredient'] != '')]
    
    # get instructions
    instr_dict = {}
    for step in recipe['instructions']:
        instr_dict[step['position']] = step['display_text']
    
    # parse ingredients
    n_np_list, nlp = recipe_parser.parse_ingredients(ingred_list)
    
    # ingredients to matcher
    matcher = recipe_parser.ingred_to_matcher(n_np_list, nlp)
    
    # parse instructions
    df = recipe_parser.parse_instructions(instr_dict, nlp, matcher)
    
    # clean instructions
    df = recipe_visualizer.clean_df(df)
    
    # visualize instructions
    fig, ax = recipe_visualizer.broken_barh(df)
    st.pyplot(fig)

else:
    st.write('')
    st.write('Please copy and paste your recipe URL from Tasty.co!')