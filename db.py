import pymongo
from datetime import datetime, timedelta
import logging

################# This module defines functions for interacting with our MongoDB database #################
# The basic utility of the db is to store previously received or calculated results, to reduce the necessary number of API calls
# to the news api as well as to increase speed. 
# We will store all previous searches so that future searches with the same parameters can just be retrieved from the db instead 
# of needing to make a duplicate API call. These are stored in the 'news-searches' collection.
# The number of term occurrences for a given term is also stored so that once it is calculated we do not need to calculate it again.
# These are stored in a separate collection ('articles') so that searches with overlapping articles can take advantage of any results already calculate.

# Connect to client
client = pymongo.MongoClient("mongodb://localhost:27017/")

# Connect to the news DB
news_db = client.newsDB

# The maximum time differential, in minutes, we are willing to accept when retrieving a news-search from the db
MAX_TIME_DIFF_NEWS_RETRIEVAL_MIN = 60


################# Simple wrappers of db functions #################


# Return the projected fields in the filtered document in the given collection
def retrieve_one(collection_name: str, filter: dict, projection: dict):
    return news_db.get_collection(collection_name).find_one(filter, projection)


# Return a boolean indicating if the filtered document exists in the given collection
def contains(collection_name: str, filter: dict) -> bool:
    return retrieve_one(collection_name, filter, {}) != None


# Insert one document into the given collection
def insert_one(collection_name: str, document):
    return news_db.get_collection(collection_name).insert_one(document)


################# Helper db functions #################


# Update or create a new entry if it doesn't already exist
def update_or_create_entry(collection_name: str, filter: dict, update: dict) -> bool:
    return news_db.get_collection(collection_name).update_one(
        filter,
        update,
        upsert=True  # upsert = True so that it only creates new doc if not already existing
    ).acknowledged

# Retrieve a db entry that has ONLY the given filters/fields, excluding all other fields that are provided.
# This allows us to differentiate between an entry that only has the given fields and one that also has them in addition to other fields
def retrieve_only_with_existing_fields(all_fields: list, collection_name: str, filters: dict, projection: dict):
    missing_fields = all_fields - filters.keys()
    filter = dict(filters)
    filter.update({k: {'$exists': False} for k in missing_fields})  # set any fields not passed in to not exist. 
    result = retrieve_one(collection_name, filter, projection)
    return result


################# Functions for handling newsapi's sources #################


# Insert a new sources entry into the db, return a bool indicating if entry was successful
def insert_new_sources_entry(args: dict, sources: list) -> bool:
    document = {
        **args,
        'sources': sources
    }
    return insert_one('sources', document).acknowledged


# Update a sources entry in the db, return a bool indicating if update was successful
def update_or_create_sources_entry(filter: dict, sources: list) -> bool:
    update_result = update_or_create_entry(
        'sources', filter, {'$set': {'sources': sources}})
    return update_result


# Retrieve a sources entry from the db, return the list of sources if found, otherwise None.
# Expects category, country, and/or language (1-3).
def retrieve_sources_entry(filters: dict) -> list | None:
    all_possible_filters = ['category', 'country', 'language']

    # we want to retrieve only entries that contain the filters passed in and don't contain any other fields (besides for the actual sources field),
    # because there is a difference between an entry that has a the category and language filter vs an entry with only a category filter, for example -
    # the former is more narrowed down and will have less sources.
    result = retrieve_only_with_existing_fields(
        all_possible_filters, 'sources', filters, {'sources': 1, '_id': 0})
    if result != None:
        return result.get('sources')
    else:
        return None


################# Functions for handling news-api's news searches #################


# Retrieve an article from the db
def retrieve_article(filters: dict, projection: dict = None) -> dict | None:
    if projection == None:
        projection = {'_id': 0}
    return retrieve_one('articles', filters, projection)

# Insert a new news-searches entry, and add any new articles.
# Since articles may have already been encountered from a different news search, we only update those with this search's term
# instead of making a full new entry.
# Expects:
#   args - the args used for the search
#   total_results - the number of results (articles retrieved)
#   articles - the article objects, which contain the urls as well as the other associating info
def insert_new_news_search(args: dict, total_results: int, articles: list) -> bool:
    # For the articles, we keep only the url for the db entry in the 'news-searches' collection.
    # The other article info will be stored separately in the 'articles' collection, along with the number of term occurrences.
    article_urls = [article.get('url') for article in articles]

    # For the args, we input them as received, except that we make actual date objects for the 'from' and 'to' parameters so
    # we can search and index with them more easily.
    if ('from' in args):
        args['from'] = datetime.fromisoformat(args['from'])
    if ('to' in args):
        args['to'] = datetime.fromisoformat(args['to'])

    news_searches_document = {
        **args,
        'totalResults': total_results,
        'articles': article_urls
    }

    try:
        news_search_insertion_succeeded = insert_one(
            'news-searches', news_searches_document).acknowledged

        # Add a new article entry (update or insert) for each article
        article_insertion_succeeded = True
        for article in articles:
            # Filter is set just based on the url as that is what makes an article unique. Also, this way entries
            # will be updates as time goes on if some of the other data changes.
            article_filter = {
                'url': article.get('url', '')
            }

            # Article is a dict of values, each value needs to be '$set' since we are using update
            article_update = {
                '$set': article
            }

            article_insertion_succeeded = article_insertion_succeeded and update_or_create_entry(
                'articles', article_filter, article_update)
        return news_search_insertion_succeeded and article_insertion_succeeded
    except:
        return False


# Retrieve a news-search entry from the DB, taking in the args that would be sent to the newsapi if we were making a new api call.
# max_time_difference_min sets the maximum time difference the caller is willing to accept when retrieving from the db.
# If this is greater than 0, the function will try to find a suitable db entry that is within the given number of minutes
# of the 'from' and 'to' date times, even if it is not an exact match.
def retrieve_news_search(request_args: dict, max_time_difference_min: int = None) -> dict | None:

    if max_time_difference_min is None:
        max_time_difference_min = MAX_TIME_DIFF_NEWS_RETRIEVAL_MIN

    # All fields for news search entries. set any not passed in to not exist so that we can differentiate between an entry that only has the
    # given fields and one that also has them in addition to other fields, as such a difference makes the entry unique.
    all_fields = ['q',
                  'searchIn',
                  'sources',
                  'domains',
                  'excludeDomains',
                  'from',
                  'to',
                  'language',
                  'sortBy',
                  'pageSize',
                  'page'
                  ]

    # The fields we want to get back are set to 1, excluded set to 0 (others are by default excluded I believe, except for _id)
    projection = {'totalResults': 1, 'articles': 1, '_id': 0}

    # Replace the 'from' and 'to' date args with actual date objects.
    filters = dict(request_args)
    if 'from' in filters:
        from_date = datetime.fromisoformat(filters['from'])
        lowest_from_date = from_date - timedelta(minutes=max_time_difference_min)
        greatest_from_date = from_date + timedelta(minutes=max_time_difference_min)
        filters['from'] = {'$gte': lowest_from_date, '$lte': greatest_from_date}
    if 'to' in filters:
        to_date = datetime.fromisoformat(filters['to'])
        lowest_to_date = to_date - timedelta(minutes=max_time_difference_min)
        greatest_to_date = to_date + timedelta(minutes=max_time_difference_min)
        filters['to'] = {'$gte': lowest_to_date, '$lte': greatest_to_date}

    # Get the news search entry
    result = retrieve_only_with_existing_fields(
        all_fields, 'news-searches', filters, projection)

    # Get all article urls
    if result is not None:
        # articles are stored with just the urls in the 'news-searches' collection. Retrieve each article entry for all
        # urls in the news-search.
        article_urls = result.get('articles')
        for i, url in enumerate(article_urls):
            article_data = retrieve_article({'url': url})
            # article data contains url + all other info not stored in the news-searches collection
            result['articles'][i] = article_data
    return result