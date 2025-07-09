# https://github.com/maliawan0/Apartments-for-Rent-Classified/blob/main/Apartment-For-Rent-Project.ipynb
# https://github.com/rozhanvassef/DataMining_apartment_rent_dataset/blob/main/apartment_rent_DataMining.ipynb

'''
a.	Among the discrete variables (e.g., Balcony), identify three that are most likely to contribute to high-priced properties. 
Compare your selections and justify why you have selected them for the activity.

b.	Assess whether there is a correlation — positive or negative — 
between the number of rooms, price, and rental duration of an apartment.  

c.	Determine whether an apartment’s address is a significant predictor of price increases, 
and identify three additional attributes that are associated with high rental rates. 
Justify your selections by comparing them to other variables and provide supporting evidence.

'''

import pandas as pd



def run_preliminary_analysis(df: pd.DataFrame):
    
    pass



if __name__ == '__main__':
    # python -m scripts.analytics.modelling
    from scripts.load import load
    training, testing = load()

