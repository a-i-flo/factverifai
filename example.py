#%%
from factverifai import fact_check


# text = "Nicușor Dan is the president of Romania in 2025, winning against Simion"
text = "Judges rule that Trump overstepped his authority when he used an emergency law to impose tariffs"
fact_check(text, output="pretty_print", max_workers=4, verbose = True)






# %%
