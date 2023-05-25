# news-trends

This is a web application that allows searching and comparing terms to see how frequent and relevant they are in the news. The search can be filtered by beginning and end dates, country, category, language, and the location of the term in the news articles. After entering a term, the webpage displays the total number of articles that term occurred in based on the filters provided as well as the 10 most recent of those articles. The page also displays how many times the term appears across all the articles counted in the search. If two terms were given, the terms are compared.

There are 2 main endpoints for our internal server: [`get-articles`](https://github.com/avrohom-schneierson/news-trends/blob/cd04c574ff6e0a7c0f1b8d7c88469eea9db937b8/app.py#L82) and [`get-num-term-occurrences`](https://github.com/avrohom-schneierson/news-trends/blob/cd04c574ff6e0a7c0f1b8d7c88469eea9db937b8/app.py#L115). [`get-articles`](https://github.com/avrohom-schneierson/news-trends/blob/cd04c574ff6e0a7c0f1b8d7c88469eea9db937b8/app.py#L82) returns all the news articles found based on the given parameters. [`get-num-term-occurrences`](https://github.com/avrohom-schneierson/news-trends/blob/cd04c574ff6e0a7c0f1b8d7c88469eea9db937b8/app.py#L115) returns the number of times the term occurs, in total, across all news article pages for the given search.

Both of these endpoints make use of a NoSQL database (MongoDB) to reduce the required number of API calls and to reduce wait times for results.

For news searches, if a news search is requested and retrieved from the news API, it will be stored in the database so that future duplicate requests do not need to make another API call to the news API.

For the number of term occurrences, each article page in the search is stored in the database with the search term's count on that page so that future requests can query from the database. Although this endpoint wouldn't require any news API calls without the database, using the database still makes it much faster for future requests because they no longer need to make a new request to each website, wait for the result, and calculate the number of times the term occurs. Articles are stored in a separate collection from the news searches so that any overlapping articles in separate news searches can take advantage of a previously computed result if the term is the same.

The news API used is [newsapi.org](https://newsapi.org/).
