import json
import requests
from requests import Response

##############################################################################
#     This module defines functions for using the news api (newsapi.org)     #
##############################################################################

USE_API = False
BASE_URL = 'https://newsapi.org'
api_key_file = open(r"tokens/newsapiorg_apikey.txt", "r")
API_KEY = api_key_file.readline()

headers = {
    'Authorization': API_KEY if USE_API else ""
}

################################################
#     Simple wrappers of newsapi.org's API     #
################################################


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


################################################
#     Helper newsapi functions     #
################################################

# Does not take a page argument, that will be handled internally here.
def get_articles_all_pages(**params) -> Response | None:
    # Copy arguments and add a page arg
    arguments = dict(params)
    arguments['page'] = 1
    articles = []

    # While we successfully retrieved additional articles and did not yet retrieve all of them: collect the articles and request the next page
    while True:
        response = get_articles(arguments)
        response_content = json.loads(response.content)
        articles += response_content.get('articles', [])
        arguments['page'] += 1

        # If the request failed or we are done collecting all articles, then break out of the loop
        if response.status_code != 200 or len(articles) >= response_content.get('totalResults', float('inf')):
            break

    if response.status_code == 200:
        response_content.update({'articles': articles})
        response._content = json.dumps(response_content)
    return response
