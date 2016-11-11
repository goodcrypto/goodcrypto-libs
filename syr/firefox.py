#! /usr/bin/env python
'''
    Parse firefox bookmarks

    First, create json file by hand:
        Bookmarks / Show all bookmarks / Import and backup / Backup

    Based on Jay Rambhia's great code:
        Fetch bookmarks from Browser using Python - Jay Rambhia
        http://www.jayrambhia.com/blog/fetch-bookmarks-from-browser-using-python/

    Portions Copyright 2014-2016 GoodCrypto

    Last modified: 2016-04-20
'''
from __future__ import unicode_literals

import datetime
import json
import os
import sys
import time
import pickle

def usage():
    sys.exit('usage: firefox-bookmarks JSON_BOOKMARKS_FILE')

def parse_bookmark(tag, bookmark):
    try:
        if 'children' in bookmark:
            bookmarks = bookmark['children']
            if bookmarks:
                for bookmark in bookmarks:
                     yield parse_bookmark(tag, bookmark)

        else:
            uri = bookmark['uri']
            title = bookmark['title']
            dateAdded =  bookmark['dateAdded'] # it gives a long int eg. 1326378576503359L
            add_date = dateAdded/1000000.0  # The output of time.time() would be 1326378576.503359
            lastModified = bookmark['lastModified']
            modified_date = lastModified/1000000.0

            yield (uri, title, tag, add_date, modified_date)

    except:
        print(repr(bookmark))
        print(bookmark.keys())
        raise

def bookmarks(input):
    con = json.load(input)

    # Get Bookmarks Menu / Bookmarks toolbar / Tags / Unsorted Bookmarks
    con_list = con['children'] # this list will have all of the above mentioned things

    for i in range(len(con_list)):
        con_sub_list = con_list[i]['children']  # Access them individually
        for tags in con_sub_list:
            if 'children' in tags: # Accessing Tags # get tag list
                bookmarks = tags['children'] # get all the bookmarks corresponding to the tag
                if bookmarks:
                    for bookmark in bookmarks: # Access each bookmark
                        tag = tags['title']
                        for result in parse_bookmark(tag, bookmark):
                            yield result
            else:
                if (tags['title'] != 'Recently Bookmarked'
                    and tags['title'] != 'Recent Tags'
                    and tags['title'] != 'Most Visited'
                    and con_list[i]['title'] != 'Bookmarks Menu'):

                     # Accessing Unsorted Bookmarks
                     tag = con_list[i]['title']
                     for result in parse_bookmark(tag, bookmark):
                        yield result

def main():
    def timestamp_string(seconds):
        return seconds

    if len(sys.argv) != 2:
        usage()

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        sys.exit('{} does not exist'.format(json_path))

    with open(json_path) as input:
        for bookmark in bookmarks(input):
            """
            uri, title, tag, add_date, modified_date = bookmark
            bookmark = uri, title, tag, add_date, modified_date
            """
            print(repr(bookmark))

if __name__ == '__main__':
    main()