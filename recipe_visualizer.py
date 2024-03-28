import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

def clean_df(df):
    """
    this function cleans parsed instructions to prepare for visualization
    """
    # update step
    df['updated_step'] = df.groupby(['step']).ngroup()+1
    
    # inpute num_time
    df['interval'] = df['num_time'].apply(lambda x : 2 if (x is None) or (x == '') \
                                          else int(x))
    
    # add end, start, and mid
    df['end'] = df['interval'].cumsum()
    df['start'] = df['end']-df['interval']
    df['mid'] = (df['start']+df['end'])/2
    
    # concat action & ingredients
    df['text'] = df[['action', 'ingredients']].apply(lambda x : f'{x[0]} {x[1]}' if (x[1] != '') \
                                                     else f'{x[0]}', axis=1).str.capitalize()
    
    return df

@st.cache_data(show_spinner='Visualizing recipe...')
def broken_barh(df):
    """
    this function dynamically visualizes parsed and cleaned ingredients
    """
    # pixel per inch
    ppi = 96
    # height for broken_barh and annotations
    height = 51.2
    fig, ax = plt.subplots(figsize=(1280/ppi, height*len(df)/ppi), facecolor='white')

    # set x range
    # +4 bc some text until may be long
    # this ensures barh dimensions don't get too scaled
    xlim_ul = df['end'].tail(1).item()+4
    ax.set_xlim(0, xlim_ul)

    # set y range
    # invert y
    # this range is not really 51.2*len(df) bc of margins
    # but close enough that annotations won't overlap
    ylim_ul = height*len(df)
    ax.set_ylim(0, ylim_ul)
    ax.invert_yaxis()

    # set xranges & facecolors for broken_barh
    xranges_list = list(df[['start','interval']].itertuples(index=False, name=None))
    facecolors_list = ['#ffdccc' if i is None else '#f46524' for i in df['num_time']]

    # for each row, plot broken_barh, text, until, num_time
    for i, row in df.iterrows():
        ax.broken_barh(xranges=[xranges_list[i]], yrange=(height*i, height), facecolors=facecolors_list[i])
        ax.annotate(row['text'], (row['end'], height/4+height*i), 
                    xytext=(2, 0), textcoords='offset points', ha='left', va='center')
        ax.annotate(row['until'], (row['end'], height*3/4+height*i), 
                    xytext=(2, 0), textcoords='offset points', ha='left', va='center',
                    color='#757575', style = 'italic')
        ax.annotate(row['num_time'], (row['mid'], height/2+height*i), 
                    xytext=(0, 0), textcoords='offset points', ha='center', va='center')

    # plot legend
    # set xranges & facecolors for broken_barh
    xranges_legend = [(0, 2), (0, 2)]
    facecolors_legend = ['#ffdccc', '#f46524']
    text_legend = ['unspecified time', 'specified time in min']

    # for each i plot, broken_barh, text
    for i, text in enumerate(text_legend):
        ax.broken_barh(xranges=[xranges_legend[i]], yrange=(height*(len(df)-2+i), height), 
                       facecolors=facecolors_legend[i])
        ax.annotate(text, (2, height*3/4+height*(len(df)-2+i)), 
                    xytext=(2, 0), textcoords='offset points', ha='left', va='center')

    # plot X
    ax.annotate('X', (1, height/2+height*(len(df)-1)), 
                xytext=(0, 0), textcoords='offset points', ha='center', va='center')

    plt.box(False)
    plt.axis('off')

    return fig, ax
