import pandas as pd
import re
import spacy
import streamlit as st
from spacy.language import Language
from spacy.matcher import Matcher
from spacy.tokens import Span

@st.cache_data(show_spinner='Parsing recipe...')
def parse_ingredients(ingred_list):
    """
    this function extracts nouns and noun phrases (while accounting for errors) from ingredients
    and stores them in a list
    """
    
    # load nlp()
    nlp = spacy.load('en_core_web_sm')
    
    food_list = []
    
    for ingred in ingred_list:

        # from start of string, remove characters, R/TM symbols, white spaces
        re.sub(r'^.*[®™]+\s', '', ingred)

        # remove 'medium', if applicable
        if ingred[:7] == 'medium ':
            ingred = ingred[7:]

        # run nlp()
        doc = nlp(ingred)

        # get_ingredients() already delt with None and ''
        # when there is one token, it has to be a noun
        if len(doc) == 1:
            idx_list = []
            idx_list.append(0)
        # when there are two or more tokens
        else:
            idx_list = []
            span = doc[:]
            # remove everything to the left of PUNCT (inclusive) and the token after, if applicable
            for token in doc:
                if token.pos_ == 'PUNCT':
                    span = doc[token.i+2:]
            # remove ADJ NOUN, if ADJ NOUN NOUN (NOUN)
            if (len(span) >= 3) and (span[0].pos_ == 'ADJ') and (span[1].pos_ == span[2].pos_ == 'NOUN'):
                span = span[2:]
            # record indices of nouns and proper nouns
            for token in span:
                if token.pos_ in ('NOUN', 'PROPN'):
                    idx_list.append(token.i)
                    # special case: n<-nsubj<-v, e.g., teriyaki sauce
                    if (token.head.pos_ == 'VERB') and (token.dep_ == 'nsubj'):
                        idx_list.append(token.head.i)
                    # special case: n<-compound/dobj<-v, e.g., taco seasoning, curry powder
                    elif (token.head.pos_ == 'VERB') and (token.dep_ in ('compound', 'dobj')) and (len(span) == 2):
                        idx_list.append(token.head.i)

            # special case: no noun recognized
            if len(idx_list) == 0:
                # for some reason idx_list.append(span.root.i) did not work
                # each doc only has one sent
                idx_list.extend([sent.root.i for sent in doc.sents])

            # special case: if indices not continuous, remove index/indices from left side
            if len(idx_list) >= 2:
                subset = idx_list
                for i in range(0, len(subset)-1):
                    if subset[i+1]-subset[i] > 1:
                        subset[:i+1] = [None]*len(subset[:i+1])
                idx_list = [idx for idx in subset if idx is not None]

        # create span for food
        food = doc[min(idx_list): max(idx_list)+1]
        food_list.append(food.lemma_)
    
    return food_list, nlp

def ingred_to_matcher(n_np_list, nlp):
    """
    this function converts parsed ingredients into a nlp matcher
    """
    matcher = Matcher(nlp.vocab)
    
    for n_np in n_np_list:
        # get_ingredients() already delt with None and ''
        # default separator is any white space
        if len(n_np.split()) == 1:
            pattern = [{'LEMMA': n_np}]
            matcher.add(n_np.upper(), [pattern])
        else:
            pattern = [{'LEMMA': n, 'OP': '?'} for n in n_np.split()]
            matcher.add(n_np.upper(), [pattern])

    return matcher

def get_descriptor(ingredient_curr, ingredients, doc, prep_text=''):
    """
    this function extracts descriptor for current ingredient
    search scope: right-most left child of current ingredient
    """
    # only extracts NOUN, PROPN, ADJ
    # for action+dobj, use default prep_text=''
    # for action+prep+pobj, use prep_text=prep.text+' '
    if (doc[ingredient_curr.i-1].head == ingredient_curr) and (doc[ingredient_curr.i-1].pos_ in ('NOUN', 'PROPN', 'ADJ')):
        ingredients.append(prep_text+doc[ingredient_curr.i-1].text+' '+ingredient_curr.text)
    else:
        ingredients.append(prep_text+ingredient_curr.text)   
    return ingredients

def chain_ingredients(ingredient_curr, ingredients, doc):
    """
    this function recursively extracts chained ingredient for current ingredient
    search scope: right children of current ingredient
    """
    # only extracts NOUN, PROPN
    for possible_next in ingredient_curr.rights:
        if possible_next.pos_ in ('NOUN', 'PROPN'):
            # use default prep_text=''
            ingredients = get_descriptor(possible_next, ingredients, doc)  
            ingredients = chain_ingredients(possible_next, ingredients, doc)
    return ingredients

def get_until(action_i, until, until_start, sent, doc):
    """
    this function extracts text after 'until' for current action
    search scope: between current action and end of sentence
    """
    # in theory should search for possible_until between current and next action
    # since mostly there is only one action per sentence
    for possible_until in doc[action_i+1:sent.end-1]:
        # (until is None) to extract nearest possible_time
        if (until is None) and (possible_until.text == 'until'):
            until = possible_until.text
            until_start = possible_until.i
            for descr_until in doc[until_start+1:sent.end-1]:
                if descr_until.pos_ == 'PUNCT':
                    break
                # 'be' to account for 'is', 'are'
                # 'have' to account for 'has', 'have'
                elif descr_until.lemma_ in ('a', 'an', 'the', 'be', 'have'):
                    continue
                else:
                    until += ' '+descr_until.text
    return until

def get_num_time(action_i, num_time, sent, doc):
    """
    this function extracts number before 'minute' for current action
    search scope: between current action and end of sentence
    """
    # in theory should search for possible_time between current and next action        
    # since mostly there is only one action per sentence
    for possible_time in doc[action_i+1:sent.end-1]:
        # (num_time is None) to extract nearest possible_time
        # doc[possible_time.i-1].pos_ == 'NUM' to account for 'several minutes'
        if (num_time is None) and (possible_time.lemma_ == 'minute') and (doc[possible_time.i-1].pos_ == 'NUM'):
            num_time = doc[possible_time.i-1].text
            # from start of string, remove remove characters, non-digits
            num_time = re.sub(r'^.*[\D]+', '', num_time)
    return num_time

#@st.cache_data(show_spinner='Parsing recipe...')
def parse_instructions(instr, nlp, matcher):
    """
    this function extracts essential information (actions, ingredients, intermediate products) from instructions
    and stores it in a df with columns step, action, ingredients, until, num_time
    """
    @Language.component('ingredient_component')
    def ingredient_component_function(doc):
        matches = matcher(doc)
        spans = [Span(doc, start, end, label='INGREDIENT') for match_id, start, end in matches]
        doc.ents = spacy.util.filter_spans(spans)
        return doc

    nlp.add_pipe('ingredient_component', after='ner')
    
    df = pd.DataFrame(columns=['step', 'action', 'ingredients', 'until', 'num_time'])
    
    for step in instr.items():
        # break, if starts with 'Enjoy'
        if step[1] == 'Enjoy!':
            break
        # continue, if starts with word in all caps (e.g., 'IF', 'NOTE')
        elif step[1][:2].isupper():
            continue
        else:
            # remove white spaces, (, non-) characters, )
            text = re.sub(r'\s\([^\)]*\)', '', step[1].capitalize())
            # run nlp()
            doc = nlp(text)

            for sent in doc.sents:
                # --- get actions ---
                actions_is = set()
                # extract root.i for current sentence
                actions_is.add(sent.root.i)
                # extract head.i or head.i of head for current entity == INGREDIENT
                for ent in sent.ents:
                    if ent.label_ == 'INGREDIENT':
                        if ent.root.head.tag_ == 'VB':
                            actions_is.add(ent.root.head.i)
                        elif (ent.root.head.tag_ == 'IN') and (ent.root.head.head.tag_ == 'VB'):
                            actions_is.add(ent.root.head.head.i)
                # sort action indices so actions are in order
                actions_is = sorted(list(actions_is))
                
                for action_i in actions_is:
                    action = doc[action_i].lemma_.lower()

                    # --- get ingredients ---
                    ingredients = []
                    # search scope: right children of current action
                    for child in doc[action_i].rights:
                        # (ingredients == []) to extract nearest child
                        if (ingredients == []) and (child.dep_ == 'dobj') and (child.lemma_ != 'minute'):
                            # if child has grandc of 'prep' which has gtgrandc of 'pobj', append them
                            # else append child
                            temp = [[gtgrandc for gtgrandc in grandc.rights \
                                     if gtgrandc.dep_ == 'pobj'] for grandc in child.rights \
                                    if grandc.dep_ == 'prep']
                            if temp not in ([], [[]]):
                                # call external functions, default prep_text
                                ingredients = get_descriptor(temp[0][0], ingredients, doc)
                                ingredients = chain_ingredients(temp[0][0], ingredients, doc)
                            else:
                                # call external functions, default prep_text
                                ingredients = get_descriptor(child, ingredients, doc)
                                ingredients = chain_ingredients(child, ingredients, doc)

                        # (ingredients == []) to extract nearest grandc
                        elif (ingredients == []) and (child.dep_ == 'prep'):
                            # mostly time prep only has one child
                            for grandc in child.rights:
                                if (grandc.dep_ == 'pobj') and (grandc.lemma_ != 'minute'):
                                    # if grandc has gtgrandc of 'prep' which has gtgtgrandc of 'pobj', append them
                                    # else append grandc
                                    temp = [[gtgtgrandc for gtgtgrandc in gtgrandc.rights \
                                             if gtgtgrandc.dep_ == 'pobj'] for gtgrandc in grandc.rights \
                                            if gtgrandc.dep_ == 'prep']
                                    if temp not in ([], [[]]):
                                        # call external functions, prep_text=child.text+' '
                                        ingredients = get_descriptor(temp[0][0], ingredients, doc, prep_text=child.text+' ')
                                        ingredients = chain_ingredients(temp[0][0], ingredients, doc)
                                    else:
                                        # call external functions, prep_text=child.text+' '
                                        ingredients = get_descriptor(grandc, ingredients, doc, prep_text=child.text+' ')
                                        ingredients = chain_ingredients(grandc, ingredients, doc)

                    ingredients = ', '.join(ingredients)

                    # --- get until ---
                    until = until_start = None
                    # call external function
                    until = get_until(action_i, until, until_start, sent, doc)

                    # --- get num_time ---
                    num_time = None
                    # call external function
                    num_time = get_num_time(action_i, num_time, sent, doc)
                    
                    # put together idea_unit
                    idea_unit = [step[0], action, ingredients, until, num_time]
                    # add idea_unit to df as a row
                    df.loc[len(df.index)] = idea_unit
        
    return df
