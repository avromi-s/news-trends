# News Trends

News Trends is a web application that allows comparing terms to see how frequently they appear in the news in relation to each other.

To search, simply type in 2 terms to compare. The webpage will then display the number of articles that each term occurred in based on the filters provided.

![image](https://github.com/user-attachments/assets/37485f24-b807-422e-a474-21a32ec9f0ab)

You can test it out [here](https://www.newstrends.app).

## Backend setup

There are 2 main endpoints for our internal server: [`get-articles`](https://github.com/abe-s1/news-trends/blob/1ea69fd84ef0dcf5815e9c2b7d9cc7917feeda82/main.py#L86) and [`get-num-term-occurrences`](https://github.com/abe-s1/news-trends/blob/1ea69fd84ef0dcf5815e9c2b7d9cc7917feeda82/main.py#L115)
- [`get-articles`](https://github.com/abe-s1/news-trends/blob/1ea69fd84ef0dcf5815e9c2b7d9cc7917feeda82/main.py#L86) returns all the news articles found based on the given parameters
- [`get-num-term-occurrences`](https://github.com/abe-s1/news-trends/blob/1ea69fd84ef0dcf5815e9c2b7d9cc7917feeda82/main.py#L115) returns the number of times the term occurs, in total, across all news article pages for the given search
  - because this is an expensive operation, it is only run for results that have less than 100 articles

## Optimizations

Both of our main internal endpoints make use of a NoSQL database (MongoDB) to cache results. This helps reduce the required number of API calls as well as reduce load times.
- For news searches, if a news search is requested and retrieved from the news API, it will be stored in the database so that future duplicate requests do not need to make another API call to the news API
- For the number of term occurrences, each article page in the search is stored in the database with the search term's count on that page so that future requests can query from the database. Although this endpoint wouldn't require any news API calls without the database, using the database still makes it much faster for future requests because they no longer need to make a new request to each website, wait for the result, and calculate the number of times the term occurs. Articles are stored in a separate collection from the news searches so that any overlapping articles in separate news searches can take advantage of a previously computed result if the term is the same.

The news API used is [newsapi.org](https://newsapi.org/).
