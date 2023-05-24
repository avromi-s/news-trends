from datetime import datetime, timedelta, timezone
import requests
import json
import re
import db
import newsapi
from bs4 import BeautifulSoup
from tldextract import extract
import logging


### This module defines useful tools for use in the app ###


# Clean the arguments so that we can perform a news search.
def clean_news_search_args(use_db: bool, args: dict):
    args = dict(args)
    # search is performed with lowercase text so that future requests with different casing can retrieve result from db
    args['q'] = str(args.get('q', '')).lower()
    args = update_news_search_date_args(args)
    args = update_news_search_with_domains(use_db, args)
    return args


# Update the args dict with the sources' domains for the given args if filters warranting a domain restriction were provided.
def update_news_search_with_domains(use_db: bool, args: dict):
    # (The 'language' param is a valid filter for the articles (/everything) endpoint, so we will not bother using it as
    # a filter here to narrow down the sources).

    prop_to_extract = 'url'
    available_filter_params = ['category', 'country']
    if 'category' in args or 'country' in args:
        # Get and remove all the potential parameters from the args dict that are there.
        filters = {k: args.pop(k) for k in available_filter_params if k in args}

        succeeded, result, errors = retrieve_sources(use_db, filters)
        if succeeded:
            # We are only returning the property required for our /everything request, which is the domain + suffix.
            # E.g., 'amazon.com'. For each source, the below line extracts just the domain and suffix, joins them together,
            # so they become 'domain.suffix' and joins all domains by commas as the newsapi expects.
            domains = ",".join(
                ['.'.join(extract(source[prop_to_extract])[-2:]) for source in result if prop_to_extract in source])
            args['domains'] = domains
    return args


# Update the 'from' and 'to' date arguments for a news search request to the beginning and end of their days,
# respectively, and return in utc time.
def update_news_search_date_args(args: dict) -> dict:
    max_days_between_dates = 30

    # If a 'from' date was provided, set it to set its time to 00:00. If not provided then construct a utc date and set its time to 00:00.
    if 'from' in args:
        from_date = datetime.fromisoformat(args['from'])
    else:
        # Create a new date object for exactly one month ago
        from_date = datetime.now(timezone.utc) - timedelta(days=max_days_between_dates)

    # Always set the 'from' time to 00:00:00 (in the local time, or utc if 'from' wasn't provided)
    from_date = datetime(year=from_date.year, month=from_date.month,
                         day=from_date.day, hour=0, minute=0, second=0, tzinfo=from_date.tzinfo)

    # If a 'to' date is provided, and it is today or after today, then set it to be today at the current time in the local time.
    # Otherwise, set the time to be 23:59:59 in the local time.
    if 'to' in args:
        to_date = datetime.fromisoformat(args['to'])
        now = datetime.now(tz=to_date.tzinfo)
        if to_date.date() >= now.date():
            to_date = now
        else:
            to_date = datetime(year=to_date.year, month=to_date.month, day=to_date.day, hour=23, minute=59, second=59,
                               tzinfo=to_date.tzinfo)
    else:
        to_date = datetime.now(timezone.utc)

    # Convert the times to UTC time and get their ISO strings and return
    from_date_utc_iso = datetime.fromtimestamp(from_date.timestamp(), tz=timezone.utc).isoformat()
    to_date_utc_iso = datetime.fromtimestamp(to_date.timestamp(), tz=timezone.utc).isoformat()

    args['from'] = from_date_utc_iso
    args['to'] = to_date_utc_iso
    return args


# Retrieve news sources based on the given filters.
# Sources are used to filter down a search result by providing only the sources the search should use.
# Return a bool indicating if retrieval was successful and the sources (if any) as a list of dicts.
# If 'use_and_update_db' is true, function attempts to retrieve via db if it exists, else it uses the API.
# Also, if 'use_and_update_db' is true, a new entry is created in the db if an API call was needed, because in that case
# the db did not already have the result.
def retrieve_sources(use_and_update_db: bool, filters: dict) -> tuple[bool, dict, dict]:
    # Values to return:
    succeeded = False
    result = None
    errors = {}

    # Attempt to retrieve via db
    if use_and_update_db:
        result = db.retrieve_sources_entry(filters)
        succeeded = result is not None

    # If a result is not found from the db then retrieve via the API
    if not succeeded:
        response = newsapi.get_sources(**filters)

        # If we got a successful response, then return the results and store them in the db for future queries.
        if response.status_code == 200:
            result = json.loads(response.content).get('sources')
            if use_and_update_db:
                db.insert_new_sources_entry(filters, sources=result)
            succeeded = True
        else:
            # If we failed to retrieve the results then provide the errors
            errors = {
                'error_source': 'external',
                'status_code': str(response.status_code),
                # response is dict of a few fields about the error when the api call errored, so provide those
                **json.loads(response.content)
            }
            succeeded = False
    return succeeded, result, errors


# Retrieve a news-search.
# Return: a bool indicating if retrieval was successful, the result (the articles and the number of them - if any),
#   and errors dict with any errors.
# If 'use_and_update_db' is true, function attempts to retrieve via db if it exists, else it uses the API.
# Also, if 'use_and_update_db' is true, a new entry is created in the db if an API call was needed, because in that case
# the db did not already have the result.
def retrieve_news_search(use_and_update_db: bool, filters: dict) -> tuple[bool, dict, dict]:
    # Values to return:
    succeeded = False
    result = None
    errors = {}

    # Clean the article arguments so we can retrieve the appropriate results.
    filters = clean_news_search_args(use_and_update_db, filters)

    # Attempt to retrieve the result via db
    if use_and_update_db:
        result = db.retrieve_news_search(filters)
        succeeded = result is not None

    # If a result is not found from the db then retrieve via the API
    if not succeeded:
        response = newsapi.get_articles_all_pages(**filters)

        # If we got a successful response, then return the results and store them in the db for future queries.
        if response.status_code == 200:
            content = json.loads(response.content)
            result = {
                'articles': content.get('articles', []),
                'totalResults': content.get('totalResults', 0)
            }
            if use_and_update_db:
                db.insert_new_news_search(filters, result['totalResults'], result['articles'])
            succeeded = True
        else:
            # If we failed to retrieve the results then provide the errors
            news_api_errors = json.loads(response.content)
            errors = {
                'error_source': 'external',
                'status_code': str(response.status_code),
                'message': 'Error retrieving articles. News API status code: ' + str(response.status_code) +
                           ".\nAPI code: " + news_api_errors.get('code') + ". API Message: " + news_api_errors.get('message')
            }
            succeeded = False
    return succeeded, result, errors


# Return a dictionary with the given parameters pre-filled for sending a response back from our server.
def get_template_response_dict(url: str = None, args: dict = None, num_results: int = None, succeeded: bool = None,
                               errors: dict = None, results_values: dict | list = None, dev_logs: list = None):
    # Default values must be set below. They can NOT be set in function parameters above otherwise they can accumulate
    # with multiple calls because default param values are bound at function invocation, not definition. see https://tinyurl.com/5c47tm5c.
    if url is None:
        url = ""
    if args is None:
        args = {}
    if num_results is None:
        num_results = 0
    if succeeded is None:
        succeeded = False
    if errors is None:
        errors = {}
    if results_values is None:
        results_values = {}
    if dev_logs is None:
        dev_logs = []

    return_dict = {
        "request": {
            "url": url,
            "args": args,
            "dt_tm": str(datetime.now())
        },
        "succeeded": succeeded,
        "results": {
            "num_results": num_results,
            "values": results_values
        },
        "dev_logs": [],
        "errors": errors
    }
    return return_dict


# Return the total number of times the term appears on all webpages given.
# This can be an expensive operation the higher the number of urls provided, as it may need to make a separate request to
# each url.
# If 'use_and_update_db' is true, function attempts to retrieve results via the db if it exists, else it makes a new request for
# each url. Additionally, a new entry is created in the db if it wasn't already there.
def num_occurrences_on_pages(use_and_update_db: bool, term: str, urls: list) -> int:
    # Accumulate the sum of all occurrences
    total_sum = 0
    for url in urls:
        current_amount = get_num_occurrences_on_page(use_and_update_db, term, url)
        if current_amount < 0:  # i.e., if current page failed to count num of term occurrences
            pass
            # TODO send back that an error occurred in x num of pages
        else:
            total_sum += current_amount
    return total_sum


# Return the number of times the term occurs on the webpage.
# If there is an error in retrieving the page, then return -1.
# If 'use_and_update_db' is true then function first checks in db to see if result is already stored there in which case
# no processing is needed and we can just retrieve that result, otherwise, we process it and store the result for any future requests.
# The search is not case sensitive.
def get_num_occurrences_on_page(use_and_update_db: bool, term: str, url: str) -> int:
    succeeded = False

    # Attempt to retrieve the result via the db
    if use_and_update_db:
        # The result we're looking for was already computed if we can find an article that has the same url and has
        # this term already in the db entry.
        filters = {
            'url': url,
            'termCounts.term': term
        }
        # Only return the count of this term on the page, we don't need any other info.
        projection = {
            '_id': 0,
            # The '.$' matches only the entries where that field (the term) matches the filter, so that other terms' results are not returned
            'termCounts.$': 1
        }
        result = db.retrieve_article(filters, projection)
        succeeded = result is not None
        if succeeded:
            count = result.get('termCounts')[0].get('count')
            return count

    # If we could not retrieve the result from the db, then get the info manually and insert the results we find in the db.
    if not use_and_update_db or not succeeded:
        try:
            # Get page content
            response = requests.get(url)

            # If we did not successfully get the page, then return -1 to signify error
            if response.status_code != 200:
                return -1
            html_content = response.content

            # Parse the HTML content using Beautiful Soup
            soup = BeautifulSoup(html_content, 'html.parser')
            main_text = soup.get_text()  # Extract the main text from the webpage
            pattern = re.escape(term)

            # Find the number of occurrences
            count = len(re.findall(pattern, main_text, re.IGNORECASE))

            # Update the db with the found term's count
            if use_and_update_db:
                article_filter = {'url': url}

                # Update or insert a new term in the termCounts list for this new term and count
                update = {
                    '$push': {
                        'termCounts': {
                            'term': term,
                            'count': count
                        }
                    }
                }
                db.update_or_create_entry('articles', article_filter, update)
            return count
        except:  # Unknown error, return -1 to indicate so.
            return -1
