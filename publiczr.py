from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
import sys
import os
from openai import OpenAI
import json
import random
import uuid
import feedparser

load_dotenv()

client = OpenAI(
    api_key= os.getenv("GPT_API_KEY"),
)

SANITY_PROJECT_ID = os.getenv("SANITY_PROJECT_ID")  # Indsæt dit Sanity projekt-ID
SANITY_DATASET = "production"  # Brug det dataset, du arbejder med, fx "production"
SANITY_TOKEN = os.getenv("SANITY_TOKEN") 
    # API URL til Sanity
SANITY_URL = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2023-10-03/data/mutate/{SANITY_DATASET}"

    # Headers til Sanity API anmodningen
SANITY_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SANITY_TOKEN}"
}

rss_urls_to_scrape = []

rss_feeds = [
    'https://www.dagens.com/feeds/rss/articles/latest-news'
    #'https://www.dagens.dk/feeds/rss/articles/latest-news',
    #'https://trend.dk/feeds/rss/articles/latest-news'
]

# Loop gennem RSS-feeds og udtræk artikellinks
for rss_url in rss_feeds:
    feed = feedparser.parse(rss_url)
    for entry in feed.entries:
        rss_urls_to_scrape.append(entry.link)


  #getJournalist API
journalists_fetch = requests.get(f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2023-10-03/data/query/{SANITY_DATASET}?query=*[_type == 'journalist']")
if journalists_fetch.status_code == 200:
    journalists = journalists_fetch.json().get('result', [])
    print('Journalister Hentet')
    jourIds = []
        #print(journalists)
    for journalist in journalists:
        jourId = journalist['_id']
        jourIds.append(jourId)
        if jourIds:
            randomJournalist = random.choice(jourIds)

else:
    print(f"Der opstod en fejl: {journalists_fetch.status_code}")
    print(journalists_fetch.json())

    #getTags API
tags_fetch = requests.get(f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2023-10-03/data/query/{SANITY_DATASET}?query=*[_type == 'tag']")
if tags_fetch.status_code == 200:
    tags = tags_fetch.json().get('result', [])
    print('Tags Hentet')
    tagFull = []
    tagNames = []
    for tag in tags:
        tagData = {'_Id':tag['_id'], 'name':tag['name']}
        tagFull.append(tagData)
        tagName = tag['name']
        tagNames.append(tagName)
else:
    print(f"Der opstod en fejl med Tags: {tags_fetch.status_code}")
    print(tags_fetch.json())

print(tagNames)


    #getCategories API
categories_fetch = requests.get(f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2023-10-03/data/query/{SANITY_DATASET}?query=*[_type == 'category']")
if categories_fetch.status_code == 200:
    categories = categories_fetch.json().get('result', [])
    print('Kategorier Hentet')
    catFull = []
    catNames = []
    for category in categories:
        catData = {'_id':category['_id'], 'name':category['name']}
        catFull.append(catData)
        catName = category['name']
        catNames.append(catName)
else:
    print(f"Der opstod en fejl med Kategorier: {categories_fetch.status_code}")
    print(categories_fetch.json())

print(catNames)

class Article:
    def __init__(self, title, teaser, content):
        self.title = title
        self.teaser = teaser
        self.content = content

    def __str__(self):
        return f"Title: {self.title}\nTeaser: {self.teaser}\nContent: {self.content}"
    

# Hentede artikler fra rss
for page_to_scrape in rss_urls_to_scrape:

    try:
        soup = BeautifulSoup(requests.get(page_to_scrape).content, 'html.parser')

        # Try to get the title; if not found, move to the next article
        # Denne kun godt gøre længere så den kan scapre flere sider af gangen
        title_tag = soup.find('h1') # or soup.find('smthing')
        if not title_tag or not title_tag.text:
            print(f"Title not found in {page_to_scrape}, skipping.")
            continue
        title = title_tag.text

        # Try to get the image; if not found, move to the next article
        image_tag = soup.find('img', class_='panorama') or soup.find('img')
        if not image_tag or not image_tag.get('src'):
            print(f"Image not found in {page_to_scrape}, skipping.")
            continue
        imageSrc = image_tag['src']

        # Optional element: if not found, just assign an empty string
        # imageRef = soup.find('span', class_='attachment-label-element') or soup.find('p', class_='editorial-image-description') or ''
        

        # Try to get the teaser; if not found, move to the next article
        teaser_tag = soup.find('span', class_='teaser-element')
        if not teaser_tag or not teaser_tag.text:
            print(f"Teaser not found in {page_to_scrape}, skipping.")
            continue
        teaser = teaser_tag.text

        # Try to get the content; if not found, move to the next article
        content = soup.find_all('div', class_='classic')
        if not content:
            print(f"Content not found in {page_to_scrape}, skipping.")
            continue

        # Extract the text from the content
        content_text = ""
        for div in content:
            for child in div.find_all(['p', 'a', '[href]', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'], recursive=False):
                content_text += child.text + "\n"

        # Create the Article object
        article = Article(title, teaser, content_text)
        #imageRef

        #image url fra GPT

        prompt = f"""
        Læs denne titel: {article.title}.
        Find derefter et gratis billede, fra fx. Pexels, Pixabay eller andet gratis medie bibliotek.
        Billedet skal være vertikalt bred da det skal kunne passe til en artikel.
        {{
         "img_url": "Her skriver du urltil billede",
         "img_caption": "Her skriver du caption til billedet og hvilken sidedu har hentet det fra"
        }}
        """

        completion = client.chat.completions.create(
         messages=[
              {
                 "role": "user",
                 "content": prompt,
             }
         ],
         model="gpt-4o",
     )

        gpt_output = completion.choices[0].message.content
        gpt_output_stripped = gpt_output.strip("```json").strip("```")


        # Konverter GPT-output til Python dict
        gpt_data = json.loads(gpt_output_stripped)

        image_url = gpt_data['img_url'] # URL til det scraped billede
        imageRef = gpt_data['img_caption']
        image_data = requests.get(image_url).content  # Hent billedet

        print(prompt)
        

        # API URL til Sanity Assets API
        sanity_image_url = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v1/assets/images/{SANITY_DATASET}"

        # Headers til billed-upload
        sanity_image_headers = {
            "Content-Type": "image/webp",  # Ændr denne, hvis billedet er i et andet format
            "Authorization": f"Bearer {SANITY_TOKEN}"
        }


        # Upload billedet til Sanity
        image_response = requests.post(sanity_image_url, headers=sanity_image_headers, data=image_data)

        # Tjek om upload var succesfuld
        if image_response.status_code == 200:
            # Hent respons data
            response_data = image_response.json()
            print("Billedet blev uploadet succesfuldt.")
            if imageRef != '':
                image_id = image_response.json()['document']['_id']  # Få asset-ID'et fra svaret
                description_mutation = {
                "mutations": [
                     {
                        "patch": {
                            "id": image_id,
                           "set": {
                               "description": imageRef or 'not defined',
                           }
                       }
                   }
                 ]
                }
                description_response = requests.post(SANITY_URL, headers=SANITY_HEADERS, json=description_mutation)
                if description_response.status_code == 200:
                 print("Beskrivelse blev tilføjet til billedet.")
                else:
                  print(f"Der opstod en fejl ved tilføjelse af beskrivelsen: {description_response.status_code}")
                  print(description_response.json())
        

        prompt = f"""
        Du er en professionel dansk journalist. Din hovedopgave er at generere dybdegående, spændende og fængende artikler på dansk baseret på modtaget indhold.
        Uanset hvilket sprog det modtagne indhold er på, skal du altid skrive artiklen på dansk.
        Du skal producere en unik dansk artikel, der er forskellig fra det oprindelige indhold for at undgå duplikationsproblemer med Google.
        Artiklen skal baseres på følgende indhold: {article.content} og være mindst 600 ord lang.
        Din skrivning skal inkludere en fængende clickbait-titel baseret på {article.title}.
        Titlen skal være i almindelig sætningstilfælde (ikke camelcase), hvilket betyder, at kun det første ord og egennavne starter med stort bogstav.
        Derefter skal du skrive en teaser baseret på {article.teaser}.
        Returnér dit output i præcis følgende JSON-format uden yderligere tekst eller forklaringer:

        {{
         "title": "Her skriver du titlen",
         "teaser": "Her skriver du teaseren",
        "content": "Her skriver du artiklens indhold i HTML-format med KUN <p>, <h3> og <a> tags"
        }}
        """


        completion = client.chat.completions.create(
         messages=[
              {
                 "role": "user",
                 "content": prompt,
             }
         ],
         model="gpt-4o",
     )

        gpt_output = completion.choices[0].message.content
        gpt_output_stripped = gpt_output.strip("```json").strip("```")


        # Konverter GPT-output til Python dict
        gpt_data = json.loads(gpt_output_stripped)

        title_output = gpt_data['title']
        teaser_output = gpt_data['teaser']

        # Parse HTML-indholdet fra GPT-output
        html_content = gpt_data['content']
        soup = BeautifulSoup(html_content, 'html.parser')

        # Opret en liste til Portable Text-blokke
        portable_text_blocks = []

        # Gennemgå alle elementer i den parsed HTML
        for element in soup.children:
            if element.name == 'p':
                # Tilføj Portable Text blok for almindelig brødtekst (p-tags)
                portable_text_blocks.append({
                    "_type": "block",
                    "_key": str(random.randint(0, 999999999999)),
                    "style": "normal",  # Definerer brødtekst
                    "children": [
                        {
                            "_type": "span",
                            "_key": str(random.randint(0, 999999999999)),
                            "text": element.text,  # Teksten fra <p>
                            "marks": []  # Ingen ekstra styling
                        }
                    ],
                    "markDefs": []
                })
            elif element.name == 'h3':
                # Tilføj Portable Text blok for overskrifter (h3-tags)
                portable_text_blocks.append({
                    "_type": "block",
                    "_key": str(random.randint(0, 999999999999)),
                    "style": "h3",  # Definerer h3-stil for overskrifter
                    "children": [
                        {
                            "_type": "span",
                            "_key": str(random.randint(0, 999999999999)),
                            "text": element.text,  # Teksten fra <h3>
                            "marks": []  # Ingen ekstra styling
                        }
                    ],
                    "markDefs": []
                })
            elif element.name == 'a':
                # Tilføj Portable Text blok for links (a-tags)
                portable_text_blocks.append({
                    "_type": "block",
                    "_key": str(random.randint(0, 999999999999)),
                    "style": "normal",
                    "children": [
                        {
                            "_type": "span",
                            "_key": str(random.randint(0, 999999999999)),
                            "text": element.text,  # Teksten fra <a>
                            "marks": ["link"]  # Markér som link
                        }
                    ],
                    "markDefs": [
                        {
                            "_type": "link",
                            "_key": "link_" + str(random.randint(0, 999999999999)),
                            "href": element['href']  # URL fra <a>
                        }
                    ]
                })

        # Udskriv Portable Text-blokkene for at kontrollere indholdet
        #print("Portable Text Blocks:", json.dumps(portable_text_blocks, indent=2))


        prompt = f"""Læs denne artikel grundigt {gpt_data}. Udvælg derefter 1 kategori KUN fra denne liste {catNames} som passer til artiklen. Udvælg derefter minimum 3 tags, gerne flere KUN fra denne liste {tagNames} som passer til artiklen.
        Skriv udvalgte kategori og tags navne i JSON form med følgende felter 'category' og 'tag'.
        """

        referencePrompt = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4o",
        )

        gpt_reference_output = referencePrompt.choices[0].message.content
        gpt_output_strippedReference = gpt_reference_output.strip("```json").strip("```")
        gpt_dataReference = json.loads(gpt_output_strippedReference)

        chosenCategory = gpt_dataReference ['category']

        print(gpt_dataReference ['category'], 'linje 284', 'gpt_dataReference')
        print(gpt_dataReference ['tag'], 'linje 285', 'gpt_dataReference')


        sanityCategory = None
        for categories in catFull:
            if categories['name'].strip().lower() == chosenCategory.strip().lower():
                print(categories, 'match', categories['_id'])
                sanityCategory = categories['_id']
                break  # Afslut loopet, når vi har fundet et match

        if sanityCategory is None:
            print(f"Fejl: Ingen matchende kategori fundet for {chosenCategory}")

        # Tag-matching (rettet logik for liste)
        sanityTags = []  # Lav en liste til at gemme matches
        chosenTags = gpt_dataReference['tag']  # Antager, at dette er en liste af tags fra GPT

        for tag in tagFull:
            for chosenTag in chosenTags:
                if tag['name'].strip().lower() == chosenTag.strip().lower():
                    print(tag, 'match', tag['_Id'])
                    sanityTags.append(tag['_Id'])  # Append matchet tag til listen
                    break  # Gå videre til næste tag, når der er fundet et match

        if not sanityTags:  # Tjekker, om listen stadig er tom
            print(f"Fejl: Ingen matchende tags fundet for {gpt_dataReference['tag']}")



        # Herefter skal portable_text_blocks bruges til at oprette Sanity-artiklen
        sanity_article_data = {
            "mutations": [
                {
                    "create": {
                        "_type": "article",
                        "title": title_output,
                        "teaser": teaser_output,
                        "overview": portable_text_blocks,  # Indsæt dine Portable Text-blokke her
                        "metaImage": {
                            "_type": "image",
                            "asset": {
                                "_type": "reference",
                                "_ref": image_id  # Brug billedets asset-ID her
                            },
                        },
                        "journalist": {
                        "_ref": f"{randomJournalist}",
                        "_type": "reference"
                        },
                        "category": {
                        "_ref": f"{sanityCategory}",
                        "_type": "reference"
                        },
                        "tag": [],
                        "views": 0,
                        "isPublished": 0,
                        "changePublishDate": False,
                        "publishMonth": 0,
                        "facebookFields": False,
                        "previewMode": False,
                        "updateJournalist": False,
                        "disclaimer": True
                    }
                }
            ]
        }
        if sanityCategory:
            sanity_article_data["mutations"][0]["create"]["category"] = {
                "_ref": f"{sanityCategory}",
                "_type": "reference"
            }
        if sanityTags:
            for tag in sanityTags:
                sanity_article_data["mutations"][0]["create"]["tag"].append({
                    "_key": str(uuid.uuid4()),  # Generer en unik nøgle
                    "_ref": f"{tag}",
                    "_type": "reference"
                })
        if randomJournalist:
            sanity_article_data["mutations"][0]["create"]["journalist"] = {
                "_ref": f"{randomJournalist}",
                "_type": "reference"
            }

        # Send POST anmodning til Sanity
        response = requests.post(SANITY_URL, headers=SANITY_HEADERS, data=json.dumps(sanity_article_data))

        # Check responsen fra Sanity API
        if response.status_code == 200:
            print("Artiklen blev oprettet succesfuldt i Sanity Studio.")
            print(response.json())
        else:
            print(f"Der opstod en fejl: {response.status_code}")
            print(response.json())
    
    except Exception as e:
        # In case any unexpected error happens
        print(f"Error occurred while processing {page_to_scrape}: {str(e)}")
        continue