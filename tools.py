from datetime import datetime, timedelta, timezone
import requests
import json
import re
import db
import newsapi
from bs4 import BeautifulSoup
from tldextract import extract


###############################################################
#     This module defines useful tools for use in the app     #
###############################################################

def retrieve_news_search(filters: dict, get_all_pages: bool, use_and_update_db: bool) -> tuple[bool, dict, dict]:
    filters = clean_news_search_args(use_and_update_db, filters)
    succeeded, result, errors = get_articles_and_num_total_results(filters, get_all_pages, use_and_update_db)
    return succeeded, result, errors


def get_articles_and_num_total_results(params: dict, get_all_pages: bool, use_and_update_db: bool) -> tuple[bool, dict, dict]:
    max_total_results = 500
    succeeded = False
    result = {}
    errors = {}

    # Copy arguments and add a page arg
    arguments = dict(params)
    arguments['page'] = 1
    articles = []
    total_results = 0

    while True:
        if use_and_update_db:
            succeeded, result = db.retrieve_news_search(arguments)
            articles += result.get('articles', []) if succeeded else []
            total_results = result.get('totalResults', total_results) if succeeded else total_results
        if not succeeded or not use_and_update_db:  # then retrieve results via api
            response = newsapi.get_articles(arguments)
            succeeded = response.status_code == 200
            result = json.loads(response.content)
            if succeeded:
                articles += result.get('articles', [])
                total_results = result.get('totalResults', total_results)
                if use_and_update_db:
                    db.insert_new_news_search_and_articles(arguments, result.get('articles', []), total_results)
            else:
                errors = {
                    'error_source': 'external',
                    'status_code': str(response.status_code),
                    'message': 'Error retrieving articles. News API status code: ' + str(response.status_code) +
                               '.\nAPI code: ' + result.get('code') + '. API Message: ' + result.get(
                        'message')
                }
                break
        if get_all_pages and total_results >= max_total_results:
            succeeded = False
            errors = {
                'error_source': 'external',
                'status_code': 426,
                'message': 'Unable to collect articles for search with over ' + str(max_total_results) + ' results'
            }
            break
        if not get_all_pages or len(articles) >= result.get('totalResults', float('inf')):
            break
        arguments['page'] += 1

    result = {
        'articles': articles,
        'totalResults': total_results
    }
    return succeeded, result, errors


# Retrieve news sources (used for filtering news searches) based on the given filters.
def retrieve_sources(use_and_update_db: bool, filters: dict) -> tuple[bool, dict, dict]:
    # Values to return:
    succeeded = False
    result = {}
    errors = {}

    if use_and_update_db:
        result = db.retrieve_sources_entry(filters)
        succeeded = result is not None

    if not succeeded:
        response = newsapi.get_sources(**filters)

        if response.status_code == 200:
            result = json.loads(response.content).get('sources')
            if use_and_update_db:
                db.insert_new_sources_entry(filters, sources=result)
            succeeded = True
        else:
            news_api_errors = json.loads(response.content)
            errors = {
                'error_source': 'external',
                'status_code': str(response.status_code),
                'message': 'Error retrieving articles. News API status code: ' + str(response.status_code) +
                           ".\nAPI code: " + news_api_errors.get('code') + ". API Message: " + news_api_errors.get(
                    'message')
            }
            succeeded = False
    return succeeded, result, errors


def clean_news_search_args(use_db: bool, args: dict):
    args = dict(args)

    # all searches are performed with lowercase text so that future requests with different casing can retrieve result
    # from db consistently (this has no effect on the api result)
    args['q'] = str(args.get('q', '')).lower()
    args = update_news_search_date_args(args)
    args = update_news_search_args_with_domains(use_db, args)
    return args


# Update the args dict with the sources' domains for the given args if filters warranting a domain restriction were provided.
def update_news_search_args_with_domains(use_db: bool, args: dict):
    # (The 'language' param is a valid filter for the articles (/everything) endpoint, so we will not bother using it as
    # a filter here to narrow down the sources).

    prop_to_extract = 'url'
    valid_sources_filters = ['category', 'country']
    if 'category' in args or 'country' in args:
        # Get and remove any parameters from the args dict that are there
        filters = {k: args.pop(k) for k in valid_sources_filters if k in args}

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

    # Retrieve or create the 'from' date
    if 'from' in args:
        from_date = datetime.fromisoformat(args['from'])
    else:
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
        num_results = len(results_values) if results_values is not None else 0
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
# each url if it's not already in the db.
def num_occurrences_on_pages(use_and_update_db: bool, term: str, urls: list) -> int:
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
# The search is not case-sensitive.
def get_num_occurrences_on_page(use_and_update_db: bool, term: str, url: str) -> int:
    term = term.lower()
    succeeded = False

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
            response = requests.get(url)
            if response.status_code != 200:
                return -1

            html_content = response.content

            # Parse the HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            main_text = soup.get_text()
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
        except Exception:  # Unknown error, return -1 to indicate so.
            return -1
