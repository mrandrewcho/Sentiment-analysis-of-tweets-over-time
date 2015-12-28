#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tweepy
import json
import time
import io
import re
import pandas
import vincent
import csv
import nltk

stemmer = nltk.stem.PorterStemmer()

# Authentication details. To  obtain these visit dev.twitter.com
consumer_key = 'l8qhSfNVJWBrhJkpJTnZ0jmuU'
consumer_secret = 'wxOwUlt0Id2iIDFENyq885KHZOIzmRxvY2iTdTcrUKmciX2YwN'
access_token = '23411820-7uSSFxJOrokwTWdwtwD7OSI66Z76GDypD7CMces6s'
access_token_secret = 'TPwm5Mg1LakrTzTXKjEYAZ7ZGz6UUpd21sijL8cELztFe'

start_time = time.time() #grabs the system time
keyword_list = ['winter'] #track list


# Part A: Download Streaming Tweets
# This is the listener, responsible for receiving data
class listener(tweepy.StreamListener):
    def __init__(self, start_time, time_limit):
        self.time = start_time
        self.limit = time_limit
        self.tweet_data = []

    def on_data(self, data):
        saveFile = open('raw_tweets.json', 'w')
        while (time.time() - self.time) < self.limit:
            try:
                # Twitter returns data in JSON format - we need to decode it first
                decoded = json.loads(data)
                data_write = json.dumps({'time': decoded['created_at'],'tweet': decoded['text']}).encode('utf-8')
                self.tweet_data.append(data_write)
                self.tweet_data.append("\n")
                return True
            except BaseException, e:
                print 'failed on_data,', str(e)
                print data
            return True
        print "saving file"
        #Save data to json file
        print "Saving Streaming Tweets"
        saveFile.write(u''.join(self.tweet_data).encode('utf-8'))
        saveFile.close()
        #Exit code
        return False

    def on_error(self, status):
        print status

#Part B: Pre-processing tweets
#Lower Case - Convert the tweets to lower case.
#URLs - Replace all URLs with the string 'URL' via regular expression matching.
#@username - Replace @usernames with string '@username' via regex matching
#hashtag - hash tags can give us some useful information, so it is useful to replace them with the exact same word without the hash. E.g. #nike replaced with 'nike'.
#Punctuations and additional white spaces - remove punctuation at the start and ending of the tweets. E.g: ' the day is beautiful! ' replaced with 'the day is beautiful'. It is also helpful to replace multiple whitespaces with a single whitespace

def clean_data():
    with open('raw_tweets.json') as data_file:
        cfp = open('cleaned_tweets.json', 'w')
        for line in data_file:
            data = json.loads(line)
            #print data['tweet']
            processedTweet = processTweet(data['tweet'])

            cleaned_data = json.dumps({'time': data['time'],'tweet': processedTweet}).encode('utf-8')
            #print cleaned_data
            cfp.write(u''.join(cleaned_data).encode('utf-8'))
            cfp.write(u'\n')
        cfp.close()

def processTweet(tweet):
    # process the tweets
    #Convert to lower case
    #print tweet
    tweet = tweet.lower()
    #Convert www.* or https?://* to URL
    tweet = re.sub('((www\.[^\s]+)|(https?://[^\s]+))','URL',tweet)
    #Convert @username to AT_USER
    tweet = re.sub('@[^\s]+','AT_USER',tweet)
    #Remove additional white spaces
    tweet = re.sub('[\s]+', ' ', tweet)
    #Replace #word with word
    tweet = re.sub(r'#([^\s]+)', r'\1', tweet)
    #trim
    tweet = tweet.strip('\'"')
    #print tweet
    return tweet

#Part C:
#Feed Training set to classifer
# Preprocessing text.
def preprocess(text):
    pre_text = re.sub('[^A-Za-z0-9#\?\!\'\"\@\(\)\:\$\%\_]+',' ',text)
    pre_text = re.sub('\?',' ? ',pre_text)
    pre_text = re.sub('\@[A-Za-z0-9]_*',' @user ',pre_text)
    pre_text = re.sub('\!',' ! ',pre_text)
    pre_text = re.sub('\(',' ( ',pre_text)
    pre_text = re.sub('\)',' ) ',pre_text)
    pre_text = re.sub('\"',' \" ',pre_text)
    pre_text = re.sub('\:',' : ',pre_text)
    pre_text = re.sub('\$',' $ ',pre_text)
    pre_text = re.sub('\%',' % ',pre_text)
    pre_text = re.sub(' [ ]*', ' ', pre_text)
    out_text = pre_text.lower()
    #out_text = stemmer.stem(pre_text)
    return out_text


# Extract ngram feature from text.
def extract_feature(text, size = 2, minlen = 3):
    tokens = text.split(' ')
    features = {}
    while tokens.__contains__(''):
        tokens.remove('')
    tokens[:] = [stemmer.stem(x) for x in tokens]
    if size < 1:
        size = 1
    if tokens.__len__() < size or tokens.__len__() < minlen:
        return None
    #print tokens
    for i in range(0,tokens.__len__()-size):
        feature = tokens[i]
        if features.has_key(feature):
            features[feature] = features[feature] + 1
        else:
            features[feature] = 1
    for i in range(0,tokens.__len__()-size+1):
        feature = '+'.join(tokens[i:i+size])
        if features.has_key(feature):
            features[feature] = features[feature] + 1
        else:
            features[feature] = 1
    #print features
    return features


# Load training data.
def load_training_data():
    read_csv = csv.reader(open('training_set.csv', 'rb'), delimiter=',')
    read_csv.next()
    labeled_set = []
    for tweet in read_csv:
        if tweet.__len__() != 3:
            print "format error! " + tweet
        feature = extract_feature(preprocess(tweet[0]))
        if feature != None:
            labeled_set.append((feature, tweet[2]))

    # Train and evaluate classifer.
    #(use first 200 as training, rest as test to evaluate)
    train_set, test_set = labeled_set[:1200], labeled_set[1200:]
    print nltk.classify.accuracy(nltk.NaiveBayesClassifier.train(train_set), test_set)

    # Train final classifer using all labeled dataset.
    classifier = nltk.NaiveBayesClassifier.train(labeled_set)
    return classifier


#Part D:
#Sentiment Analysis on Tweets

# Read tweet stream file, apply trained classifier, and generate label. Output to json file.
def sentiment_analysis(classifier):
    sfp = io.open('cleaned_tweets_sentiments.json', 'w', encoding='utf-8')
    tweets = open('cleaned_tweets.json', 'r')
    for line in tweets:
        tweet = json.loads(line)
        feature = extract_feature(preprocess(tweet['tweet']))
        if feature != None:
            label = classifier.classify(feature)
        else:
            label = "Neutral"

        sentiment_data = json.dumps({'time': tweet['time'],'tweet': tweet['tweet'],'sentiment':label})
        sfp.write(u''.join(sentiment_data))
        sfp.write(u'\n')
    sfp.close()


#Part E:
#Trends in Tweets:
#1) Quantity of tweets in time

def time_series_tweets():
    with open('cleaned_tweets.json') as graph_file:
        d = dict()
        time_array = []
        for line in graph_file:
            data = json.loads(line)
            time_array.append(data['time'])
        # a list of "1" to count the dates
        ones = [1]*len(time_array)
        # the index of the series
        idx = pandas.DatetimeIndex(time_array)
        #print idx
        # the actual series (at series of 1s for the moment)
        t_array = pandas.Series(ones, index=idx)
        #print t_array

        # Resampling / bucketing
        t_array = t_array.resample('1s', how='sum').fillna(0)
        time_chart = vincent.Line(t_array)
        time_chart.axis_titles(x='Time', y='Freq')
        time_chart.to_json('time_chart_quantity.json')

#Trends in Tweets:
#2) Sentiments in time

def time_series_sentiments():
    with open('cleaned_tweets_sentiments.json') as graph_file:
        d = dict()
        time_array = []
        for line in graph_file:
            data = json.loads(line)
            #parsed_time = datetime.datetime.strptime(data['time'], '%a %b %d %H:%M:%S +0000 %Y')
            if (data['sentiment']=="Positive"):
                time_array.append(data['time'])
        # a list of "1" to count the dates
        ones = [1]*len(time_array)
        # the index of the series
        idx = pandas.DatetimeIndex(time_array)
        #print idx
        # the actual series (at series of 1s for the moment)
        t_array = pandas.Series(ones, index=idx)
        #print t_array

        # Resampling / bucketing
        t_array = t_array.resample('1s', how='sum').fillna(0)
        time_chart = vincent.Line(t_array)
        time_chart.axis_titles(x='Time', y='Freq')
        time_chart.to_json('time_chart_sentiments.json')



if __name__ == '__main__':
    #will listen Twitter stream for 1200 seconds
    l = listener(start_time, time_limit=1200)
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    print "Collecting Streaming Tweets"

    # There are different kinds of streams: public stream, user stream, multi-user streams
    # In this example follow #sunday tag
    # For more details refer to https://dev.twitter.com/docs/streaming-apis
    #Listen to Twitter streaming data for the given keyword. Narrow it down to English.

    stream = tweepy.Stream(auth, l)
    stream.filter(track=keyword_list, languages=['en'])

    print "Cleaning streaming data"
    #Clean data  - save to cleaned_tweet.json
    clean_data()

    print "Training classifiers using training data"
    #Train the classifieres using the training data
    classifier = load_training_data()

    print "Performing sentiment analysis"
    #Perform sentiment analysis on the downloaded tweets using trained classifiers
    sentiment_analysis(classifier)

    print "Creating time-series plots"
    #Plot time-series of number of tweets/second
    time_series_tweets()

    #Plot time-series of changing positive sentiments/second
    time_series_sentiments()
