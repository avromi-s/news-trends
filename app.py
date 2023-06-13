from flask import Flask, render_template, request
import json
from werkzeug.exceptions import HTTPException
import tools
import db

##########################
#     The server app     #
##########################

app = Flask(__name__)
USE_DB = True  # If false, then it will always use the API


@app.route('/')
@app.route('/home')
@app.route('/index')
@app.route('/search')
def home():
    return render_template('index.html')


# Used for news searches. No args expected.
@app.route('/internal/get-languages')
def get_languages():
    result = db.news_db.get_collection('enums').find_one({'name': 'language'}, {'_id': 0, 'values': 1})
    if result is not None:
        languages = result.get('values', {})
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, len(languages), True, {}, languages)
    else:
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, 0, False,
            {'error_source': 'internal', 'message': 'error retrieving languages'},
            {})
    return json.dumps(return_dict)


# Used for news searches. No args expected.
@app.route('/internal/get-countries')
def get_countries():
    result = db.news_db.get_collection('enums').find_one({'name': 'country'}, {'_id': 0, 'values': 1})
    if result is not None:
        countries = result.get('values')
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, len(countries), True, {}, countries)
    else:
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, 0, False,
            {'error_source': 'internal', 'message': 'error retrieving countries'},
            {})
    return json.dumps(return_dict)


# Used for news searches. No args expected.
@app.route('/internal/get-categories')
def get_categories():
    result = db.news_db.get_collection('enums').find_one({'name': 'category'}, {'_id': 0, 'values': 1})
    if result is not None:
        categories = result.get('values')
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, len(categories), True, {}, categories)
    else:
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, 0, False,
            {'error_source': 'internal', 'message': 'error retrieving categories'},
            {})
    return json.dumps(return_dict)


# Return news articles based on the given parameters. Only returns the first 10 articles, but gives the total number of articles that exist.
# Expects:
#   'q' (required)
#   'from' (an iso string)
#   'to' (an iso string)
#   'language'
#   'country'
#   'category'
#   'searchIn'
# For the dates ('from' and 'to' args), make the request to this method with either an utc date, or a local date denoted with the time offset.
# The function will then return the results for the corresponding UTC time range.
@app.route('/internal/get-articles')
def get_articles():
    num_articles_to_return = 10
    return_dict = tools.get_template_response_dict(
        url=request.base_url, args=request.args)
    errors = {}
    if len(request.args.get('q', '')) > 0:
        succeeded, results, errors = tools.retrieve_news_search(
            request.args, False, USE_DB)
        return_dict['succeeded'] = succeeded
        return_dict['errors'] = errors
        if succeeded:
            return_dict['results']['num_results'] = 2
            return_dict['results']['values'] = {'num_articles': results.get('totalResults'),
                                                'articles': results.get('articles')[:num_articles_to_return]}
            return json.dumps(return_dict), 200
        else:
            return_dict['num_results'] = 0
            return_dict['errors']['error_source'] = errors.get('error_source', 'internal')
            return_dict['errors']['message'] = errors.get('message', 'error retrieving news articles')
            return json.dumps(return_dict), 500

    return_dict['results']['num_results'] = 0
    return_dict['errors']['error_source'] = errors.get('error_source', 'internal')
    return_dict['errors']['message'] = errors.get('message', 'invalid input: missing parameter \'q\'')
    return json.dumps(return_dict), 400


# Return the total number of times the term appears on all webpages for a news search.
@app.route('/internal/get-num-term-occurrences')
def get_num_term_occurrences():
    return_dict = tools.get_template_response_dict(
        url=request.base_url, args=request.args)
    errors = {}
    if len(request.args.get('q', '')) > 0:
        succeeded, results, errors = tools.retrieve_news_search(
            request.args, True, USE_DB)
        return_dict['succeeded'] = succeeded
        return_dict['errors'] = errors
        if succeeded:
            urls = [article.get('url') for article in results.get('articles')]
            num_occurrences = tools.num_occurrences_on_pages(USE_DB, request.args.get('q'), urls)
            return_dict['results']['num_results'] = 1
            return_dict['results']['values'] = {'num_occurrences': num_occurrences, 'num_articles': results.get('totalResults', -1)}
            return json.dumps(return_dict), 200
        else:
            return_dict['results']['num_results'] = 0
            return_dict['errors']['error_source'] = errors.get('error_source', 'internal')
            return_dict['errors']['message'] = errors.get('message', 'error retrieving num term occurrences')
            return json.dumps(return_dict), 500

    return_dict['results']['num_results'] = 0
    return_dict['errors']['error_source'] = errors.get('error_source', 'internal')
    return_dict['errors']['message'] = errors.get('message', 'invalid input: missing parameter \'q\'')
    return json.dumps(return_dict), 400


# Source: https://github.com/BeeFriedman/FluxNodeUptimeMonitor/blob/da0f425b5bf64efa62e4d7c05ec1b16df0282dc5/app.py#LL40C6-L40C6
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return str(e.code) + ' error', e.code
    return '500 internal server error', 500
