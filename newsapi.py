import json
import requests
from requests import Response
import logging

################# This module defines functions for using the news api (newsapi.org) #################

USE_API = True
BASE_URL = 'https://newsapi.org'
api_key_file = open(r"tokens/newsapiorg_apikey.txt", "r")
API_KEY = api_key_file.readline()

headers = {
    'Authorization': API_KEY if USE_API else ""
}


######### Simple wrappers of newsapi.org's API #########

# Get all news sources. All parameters are optional and can be used as filters, but not required.
def get_sources(**params) -> Response:
    endpoint = '/v2/top-headlines/sources'
    url = BASE_URL + endpoint
    result = requests.get(url, headers=headers, params=params)
    return result


# Return all news articles for the given filters. Using the 'everything' endpoint.
def get_articles(params) -> Response:
    endpoint = '/v2/everything'
    url = BASE_URL + endpoint
    result = requests.get(url, headers=headers, params=params)
    return result


######### Helper newsapi functions #########

# Return articles for the given arguments from ALL pages. Does not take a page argument, that will be handled internally here.
def get_articles_all_pages(**params) -> Response | None:
    # Copy arguments and add a page arg
    arguments = dict(params)
    arguments['page'] = 1

    articles = []

    # While we successfully retrieved additional articles and did not yet retrieve all of them: collect the articles and request the next page
    while True:
        # Get articles from the next page
        response = get_articles(arguments)
        response_content = json.loads(response.content)
        articles += response_content.get('articles', [])
        arguments['page'] += 1

        # If the latest request failed, we finished retrieving all articles, or the response for some reason doesn't contain the
        # 'totalResults' value - then break out of the loop.
        if response.status_code != 200 or len(articles) >= response_content.get('totalResults', float('inf')):
            break

    # Update the response object's content with all the articles we've received. If we hit an error, do not return the result as it is incomplete.
    if response.status_code == 200:
        response_content.update({'articles': articles})
        response._content = json.dumps(response_content)
    return response
