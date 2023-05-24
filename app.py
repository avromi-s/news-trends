from flask import Flask, render_template, request
import json
import tools
import db

### The server app ###

app = Flask(__name__)

# Flag indicating whether server should utilize the db by first attempting to retrieve results from it, if false,
# then it will always use the API.
USE_DB = True


@app.route('/')
@app.route('/home')
@app.route('/index')
@app.route('/search')
def home():
    return render_template('home.html')


# Return the available languages for news searches. No args expected.
@app.route('/internal/get-languages')
def get_languages():
    result = db.retrieve_one('enums', {'name': 'language'}, {'_id': 0, 'values': 1})
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


# Return the available countries for news searches. No args expected.
@app.route('/internal/get-countries')
def get_countries():
    result = db.retrieve_one('enums', {'name': 'country'}, {'_id': 0, 'values': 1})
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


# Return the available categories for news searches. No args expected.
@app.route('/internal/get-categories')
def get_categories():
    result = db.retrieve_one('enums', {'name': 'category'}, {'_id': 0, 'values': 1})
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


# Return all news articles based on the given parameters
# Expects:
#   'q' (required)
#   'from' (an iso string)
#   'to' (an iso string)
#   'language'
#   'country'
#   'category'
#   'searchIn'
# For the dates ('from' and 'to' args), make the request to this method with either a utc date, or a local date denoted with the time offset.
# The function will then return the results for the corresponding UTC time.
@app.route('/internal/get-articles')
def get_articles():
    succeeded = False
    errors = {}

    # Get a return_dict with our url for this endpoint, and the args.
    return_dict = tools.get_template_response_dict(
        request.base_url, request.args)
    if len(request.args.get('q', '')) > 0:
        num_articles_to_return = 10  # These will be displayed as the most recent articles on the home page

        # Retrieve the news search (either via DB if it is already there, else via API)
        succeeded, result, errors = tools.retrieve_news_search(
            USE_DB, request.args)

        # If successfully retrieved then pack the results
        if succeeded:
            return_dict['succeeded'] = True
            return_dict['results']['num_results'] = 2
            return_dict['results']['values'] = {
                'num_articles': result.get('totalResults'), 'articles': result.get('articles')[:num_articles_to_return]}
    # Otherwise, pack error result
    if not succeeded:
        return_dict['errors']['error_source'] = errors.get('error_source', 'internal')
        return_dict['errors']['message'] = errors.get('message', 'invalid parameters provided: missing parameter \'q\'')
        return_dict['succeeded'] = succeeded
    return json.dumps(return_dict)


# Return the total number of times the term appears on all webpages for a news search.
# Args expected: the args used for the news search.
# The function will look up the list of article urls in the db for the given search parameters, and return the sum of
# their term counts for the term.
@app.route('/internal/get-num-term-occurrences')
def get_num_term_occurrences():
    # Update the args to match as they are stored in the DB and then retrieve the article urls from the search.
    args = tools.clean_news_search_args(USE_DB, request.args)

    # This essentially provides data validation because if it doesn't match a db entry, it will be rejected, and we will return an error.
    results = db.retrieve_news_search(args)
    if results is not None and 'articles' in results:
        urls = [article.get('url') for article in results.get('articles')]
        # Get the num of occurrences on each page
        num_occurrences = tools.num_occurrences_on_pages(USE_DB, args.get('q'), urls)
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, num_results=1, succeeded=True, errors={},
            results_values={'num_occurrences': num_occurrences})
    else:
        return_dict = tools.get_template_response_dict(
            request.base_url, request.args, num_results=0, succeeded=False,
            errors={'error_source': 'internal', 'message': 'error retrieving article urls'})
    return json.dumps(return_dict)
