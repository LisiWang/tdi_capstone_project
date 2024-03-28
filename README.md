Recently, I completed the intensive Data Science Fellowship at The Data Incubator (TDI), during which I worked on the following **capstone project**: \
In case you're curious about my **weekly projects**, please go to [this repo](https://github.com/LisiWang/tdi_weekly_projects.git).
## SousChef.ai, a project management web app for home chefs
This web app aims to extract and visualize essential information from online recipes, so that home chefs can skip the trouble of reading densely written text.
### Problem statement
- **Problem:** As someone who cooks at home often and likes to learn from online recipes, I've struggled with keeping track of what to do with what ingredient.
- **Final product:** SousChef.ai transforms instructions from any given online recipe (from tasty.co) into a Gantt chart; in which only actions, ingredients, and intermediate products are presented. It also provides a rough estimate of time, so that home chefs can better plan and multitask.
- **Usage:** Home chefs should find a recipe from [tasty.co](https://tasty.co/) first, then copy and paste the url to [SousChef.ai](INSERT RENDER).
### Project details
- **What techniques or models power it:** SousChef.ai leverages pre-trained CNNs from the [spaCy library](https://spacy.io/), combined with rule-based approaches. 
- **Where I got the data from:** I fetched recipe ingredients and instructions from tasty.co through the [Tasty API](https://rapidapi.com/apidojo/api/tasty).
- **How I created the models:** I built the ingredients parser based on 100 recipes and the instructions parser based on 10 recipes. I also made sure the parsers were able to run on the 1600 recipes I downloaded.
- **How I put together the final product:**
<p align="center">
<img src="How SousChef.ai works.png" height="300">
</p>

1. SousChef.ai extracts nouns and noun phrases from the ingredients.
2. They become part of a custom named entity recognizer in the following step.
3. Essential information from the instructions is extracted utilizing rules based on the custom component, syntactic dependency parser, and part-of-speech tagger.
4. All the above steps enable SousChef.ai to visualize the structured data.
