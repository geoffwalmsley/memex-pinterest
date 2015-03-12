__author__ = 'tomas'


class search_term_learner(object):

    #receives a list of seeds, and returns the fetched urls
    def from_seeds_to_urls(self, seeds):
        urls = []
        return urls

    # save the url that the user finds relevant or not
    def save_scored_urls(self, url, score):
        #save the url and score, relative to the current workspace
        return None

    # save the url that the user finds relevant or not
    #def get_scored_urls(self, url, score):
    #    #save the url and score, relative to the current workspace
    #    return None

    # uses the stored information for clustering, ranking and learning a classifier
    # the input is retrieved from the db, processed and stored again
    def process(self):
        # this is where the magic happens
        return None



    def get_positive_seeds_for_crawling(self):
        urls = []
        # fetch the urls that are the output of the 'process' from the db,
        return urls

