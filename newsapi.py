import json
import requests
from requests import Response

##############################################################################
#     This module defines functions for using the news api (newsapi.org)     #
##############################################################################

USE_API = True
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