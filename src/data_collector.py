# Data Collector

# System
import os
import json

# Web Scraping
import requests
from bs4 import BeautifulSoup
import re

import urllib.parse

# Data
import numpy as np
import pandas as pd

# user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36

# Utilities
def httpRequest(url: str, useSplash: bool):
    if useSplash:
        print(url)
        url = urllib.parse.quote(url)
        url = 'http://192.168.1.117:8050/render.html?url=' + url
        response = requests.get(url)
    else:
        response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    return soup

def httpProxyRequest(url:  str, useProxy: bool):
    if useProxy:
        response = requests.get(
            url,
            proxies={
                "http": "http://771c716e95864cda990b52bac3f61b8d:@proxy.crawlera.com:8011/",
                "https": "http://771c716e95864cda990b52bac3f61b8d:@proxy.crawlera.com:8011/",
            },
            verify='./zyte-proxy-ca.crt'
        )
    else:
        response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def readCSV(name: str, index_label='id') -> pd.DataFrame:
    return pd.read_csv('../data/' + name + '.csv', index_col=index_label)

def saveCSV(df: pd.DataFrame, name: str, index_label='id'):
    df.to_csv('../data/' + name + '.csv', index_label=index_label)

# Classes
busines_template = {
    'Name': None,
    'Url': None,
    'Loaded': None,
    "ExpensiveLevel": None,
    'Category': None,
    'SubCategories': None,
    'Claimed': None,
    'HasWebsite': None,
    'Stars': None,
    'Reviews': None,
    'Photos': None,

    'MenuCount': None,
    'MenuStartsCount': None,
    'MenuReviewsCount': None,
    'MenuPhotosCount': None,

    'Attributes Has': None,
    'AttributesCount': None,
    'QuestionsCount': None
}

for i in range(1, 8):
    busines_template['OpenHour' + str(i)] = None
    busines_template['EndHour' + str(i)] = None
    busines_template['CountHour' + str(i)] = None

def empty_busines():
    return busines_template.copy()

# Collectors
def collectLocations():
    soup = httpRequest('https://www.yelp.com/locations', False)
    links = soup.select('.cities a')
    locations = []
    while len(links) > 0:
        locations.append(links.pop().getText())

    locations = pd.Series(locations)
    locations.sort_values(inplace=True)

    df = pd.DataFrame({'Name': locations.tolist(), 'Collected': np.full(len(locations), False)})
    df.drop(index=df.tail(8).index, inplace=True)

    saveCSV(df, 'locations')
    saveCSV(df, 'original/locations')

def collectUrl(locations: pd.DataFrame):
    # Get Location name
    indexes = locations[locations['Loaded'] == False].index.tolist()
    if len(indexes) == 0:
        return False
    locationID = indexes[0]
    locationName = locations.iloc[locationID]['Name']

    # Start to Collect Urls
    categoryName = 'Restaurants'
    print('Collactting \"' + categoryName + '\" in \"' + locationName + '\"')

    links = []

    startParam = 0
    url = ""
    while url != None:
        url = 'https://www.yelp.com/search?find_loc={}&find_desc={}&start={}'.format(locationName, categoryName, startParam)
        startParam += 10
        soup = httpRequest(url, True)
        main = soup.select_one('main ul')
        if main == None:
            url = None
        else:
            for link in main.select('a'):
                if link.get('href').find('/biz/') != -1:
                    links.append('https://www.yelp.com' + link.get('href'))

    
    print("Create Table For The Data")

    # Remove Duplicates Links
    links = list(set(links))

    # Save Urls
    businesses = readCSV('businesses')

    new_businesses = pd.Series(links)

    businesses_data = empty_busines()

    for key in businesses_data:
        businesses_data[key] = np.full(len(links), None)

    businesses_data['Loaded'] = np.full(len(links), False)
    businesses_data['Url'] = new_businesses.tolist()
    businesses_data['Category'] = np.full(len(links), categoryName)

    businesses_data['Name'] = businesses_data['Name'].astype(str)
    businesses_data['SubCategories'] = businesses_data['SubCategories'].astype(object)
    for i in businesses_data.index:
        businesses_data.at[i, 'Name'] = ' '
        businesses_data.at[i, 'SubCategories'] = []

    df = pd.DataFrame(businesses_data)

    df.index += len(businesses.index)

    businesses = pd.concat([businesses, df])

    print("Save New Businesses to load")
    saveCSV(businesses, 'businesses')

    # Set Collected to True
    locations.at[[locationID], 'Collected'] = True
    saveCSV(locations, 'locations')
    return True

def collectUrls():
    locations = readCSV('locations')

    hasNext = True
    while hasNext:
        hasNext = collectUrl(locations)

def removeDuplicatesUrls():
    businesses = readCSV('businesses')
    print('Before remove ' + str(len(businesses.index)))

    businesses.drop_duplicates(subset='Url', keep='first', inplace=True)
    businesses.index = np.arange(len(businesses.index))

    print('After remove ' + str(len(businesses.index)))

    saveCSV(businesses, 'businesses')

def collectPages():
    print("Collect Pages")
    businesses = readCSV('businesses')

    hasNext = True
    while hasNext:
        hasNext = collectPage(businesses)

#TEMP
gBusinesses = None
gRoot = None
gHeader = None

def collectPage(businesses: pd.DataFrame):
    # Get Location name
    indexes = businesses[businesses['Loaded'] == False].index.tolist()
    if len(indexes) == 0:
        return False
    businessID = indexes[0]
    url = businesses.iloc[businessID]['Url']

    # Start to collect the Page
    soup = httpProxyRequest(url, False)
    if soup.getText().find('Sorry, you’re not allowed to access this page.') != -1:
        print('Sorry, you’re not allowed to access this page.')
        return False
    
    root = soup.select_one('yelp-react-root div')
    header = root.select_one('[data-testid="photoHeader"]')

    # TEMP
    global gBusinesses
    global gRoot
    global gHeader
    gBusinesses = businesses
    gRoot = root
    gHeader = header

    collectedHead = collectHeadinfo(header)
    collectedBody = collectPageBody(root, header)

    for key in collectedHead:
        businesses.at[businessID, key] = collectedHead[key]

    for key in collectedBody:
        businesses.at[businessID, key] = collectedBody[key]

    # Set Collected to True
    businesses.at[businessID, 'Loaded'] = True

    print(businesses.iloc[businessID].to_dict())

    #saveCSV(businesses, 'businesses')
    return False #True
    
def collectHeadinfo(header):

     # find "photo count" in header
     photoCount = header.find(string = re.compile('See \d+ photos'))
     photoCount = int(re.findall("\d+",photoCount)[0])

     # gets into where the fun stuff is so we wont have to search as much
     headInfo = header.find(class_ = re.compile('photo\-header\-content__.+'))
     headInfo = headInfo.findChild().findChild(class_=re.compile('.+ arrange-unit-fill.+'))

     # find "expensive level" in header
     expensiveLevel = len(headInfo.find(string=re.compile('\$+')))

     # find the rating of the resturant
     starRating = headInfo.find(class_=re.compile('.i-stars.+'))['aria-label']
     starRating = float((re.findall("[0-5]\.?5?",starRating))[0])
     starRating = int(starRating*2)

     # find the number of ratings
     reviews = headInfo.find(text=re.compile('.+reviews'))
     reviews = int(re.findall("\d+",reviews)[0])

     # find whether a resturant is claimed
     isClaimed = headInfo.find(text=re.compile('.+laimed'))
     isClaimed = (isClaimed=="Claimed")

     # only categories have this type of link as it seems
     categorieslinks= headInfo.findAll(href=re.compile('/c/sf.+'))
     categories=[]
     for category in (categorieslinks):
        categories.append(category.get_text())
     
     return {
         "ExpensiveLevel": float(expensiveLevel),
         "Stars": float(starRating),
         "Claimed": float(isClaimed),
         "Reviews": float(reviews),
         "SubCategories": categories,
         "Photos": float(photoCount)
     }

def collectPageBody(root :BeautifulSoup, header :BeautifulSoup):

    data = {
        'Name': ' ',
        'HasWebsite': None,
        'MenuCount': None,
        'MenuStartsCount': None,
        'MenuReviewsCount': None,
        'MenuPhotosCount': None,
        'Attributes Has': None,
        'AttributesCount': None,
        'QuestionsCount': None
    }

    for i in range(1, 8):
        data['OpenHour' + str(i)] = None
        data['EndHour' + str(i)] = None
        data['CountHour' + str(i)] = None

    # Get Name
    nameElem = header.select_one('h1')
    if nameElem != None:
        data['Name'] = nameElem.getText()

    # Get Has Website
    labelElem = root.find('p', string='Business website')
    if labelElem != None:
        websiteUrlElem = labelElem.findNext('a')
        if websiteUrlElem != None:
            data['HasWebsite'] = float(websiteUrlElem.getText().find('http') != -1)

    # Get OpenHour, EndHour, CountHour
    try:
        labels = root.select('table tr th p')
        values = root.select('table tr td ul li p')

        if 0 < len(labels) and len(labels) == len(values):
            dayNumber = 1
            for i in [6, 0, 1, 2, 3, 4, 5]:
                try:
                    value = values[i].getText()

                    if values[i].getText() == 'Closed':
                        data['CountHour' + str(dayNumber)] = 0
                    else:
                        sp = value.split(' - ')
                        openHour = timeToNumber(sp[1])
                        endHour = timeToNumber(sp[0])

                        data['OpenHour' + str(dayNumber)] = openHour
                        data['EndHour' + str(dayNumber)] = endHour
                        data['CountHour' + str(dayNumber)] = endHour - openHour
                except:
                    pass
                dayNumber += 1
    except:
        pass
    return data

def timeToNumber(ts: str):
    ret = 0
    if ts.find('AM') != -1:
        ret = 24
    sp = ts.split(' ')[0].split(':')

    if float(sp[1]) >= 30:
        ret += 1

    ret += float(sp[0]) * 2
    return ret



# Entry Point

#collectLocations()

#collectUrls()

#removeDuplicatesUrls()

#this i made

# 'https://www.yelp.com/biz/farmhouse-kitchen-thai-cuisine-san-francisco'
# collectPages()

