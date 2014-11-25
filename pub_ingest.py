#!/user/bin/env/python
"""
    pub_ingest.py -- Read a bibtex file and make VIVO RDF

    The following objects will be made as needed:
      -- publisher
      -- journal
      -- information resource
      -- timestamp for the information resource
      -- people
      -- authorships
      -- concepts

    The resulting ADD and SUB RDF file can then be read into VIVO

    To Do
    --  Complete refactor as an update process. Create resuable parts so that
        a publication can be created from bibtex, doi or pmid
    --  Improve DateTimeValue accuracy.  Currently all publications are entered
        as yearMonth precision.  Sometimes we have more information, sometimes
        we have less.  We should use the information as presented by the
        publisher, not overstate (yearMonth when there is only year) and not
        understate (yearMonth when we know the day).
    --  Reuse date objects -- only create dates when the appropriate date entity
        is not already in VIVO
    --  Update for VIVO-ISF
    --  Update or vivofoundation and vivopubs
"""

__author__ = "Michael Conlon"
__copyright__ = "Copyright 2014, University of Florida"
__license__ = "BSD 3-Clause license"
__version__ = "1.3"

import sys
from datetime import datetime, date
from pybtex.database.input import bibtex
import tempita
import vivotools

MAX_AUTHORS = 50

publisher_report = {}
journal_report = {}
title_report = {}
author_report = {}
disambiguation_report = {}

dictionaries = []
journal_dictionary = {}
publisher_dictionary = {}
title_dictionary = {}

def open_files(bibtex_file_name):
    """
    Give the name of the bibitex file to be used as input, generate the file
    names for rdf, rpt and lst.  Return the open file handles
    """
    base = bibtex_file_name[:bibtex_file_name.find('.')]
    rpt_file = open(base+'.rpt', 'w')
    lst_file = open(base+'.lst', 'w')
    rdf_file = open(base+'.rdf', 'w')
    return [rdf_file, rpt_file, lst_file]

def update_disambiguation_report(authors, publication_uri):
    """
    Given the authors structure and thte publication_uri, add to the report
    if any of the authors need to be disambiguated
    """
    for value in authors.values():
        if value[8] == "Disambig":
            if publication_uri in disambiguation_report:
                result = disambiguation_report[publication_uri]
                result[len(result.keys())+1] = value
                disambiguation_report[publication_uri] = result
            else:
                disambiguation_report[publication_uri] = {1:value}
    return

# start here.  Create a parser for bibtex and use it to read the file of
# bibtex entries. open the output files

print datetime.now(), "Read the BibTex"
bibtex_file_name = sys.argv[1]
[rdf_file, rpt_file, lst_file] = open_files(bibtex_file_name)
parser = bibtex.Parser()
bib_data = parser.parse_file(bibtex_file_name)
bib_sorted = sorted(bib_data.entries.items(),
    key=lambda x: x[1].fields['title'])

print >>rdf_file, "<!--", len(bib_data.entries.keys()),\
    "publications to be processed -->"
print datetime.now(), len(bib_data.entries.keys()),\
    "publications to be processed."

#  make dictionaries for people, papers, publishers, journals, concepts

print datetime.now(), "Creating the dictionaries"
print datetime.now(), "Publishers"
publisher_dictionary = vivotools.make_publisher_dictionary()
print datetime.now(), "Journals"
journal_dictionary = vivotools.make_journal_dictionary()
print datetime.now(), "People"
dictionaries = make_people_dictionaries()
print datetime.now(), "Titles"
title_dictionary = vivotools.make_title_dictionary()
print datetime.now(), "Concepts"
vivotools.make_concept_dictionary()

# process the papers

print >>rdf_file, vivotools.rdf_header()

for key, value in bib_sorted:
    try:
        title = value.fields['title'].title() + " "
    except:
        title_report["No title"] = ["No Title", None, 1]
        print >>rdf_file, "<!-- No title found. No RDF necessary -->"
        continue
    title = abbrev_to_words(title)
    title = title[0:-1]
    if title in title_report:
        print >>rdf_file, "<!-- Title", title,\
            "handled previously.  No RDF necessary -->"
        title_report[title][2] = title_report[title][2] + 1
        continue
    else:
        print >>rdf_file, "<!-- Begin RDF for " + title + " -->"
        print datetime.now(), "<!-- Begin RDF for " + title + " -->"
        document = {}
        document['title'] = title
        title_report[title] = ["Start", None, 1]
        [found, uri] = vivotools.find_title(title, title_dictionary)
        if not found:
            title_report[title][0] = "Create" # Create

            # Authors

            [author_rdf, authors] = make_author_rdf(value)
            document['authors'] = make_document_authors(authors)
            if count_uf_authors(authors) == 0:
                print >>rdf_file, "<!-- End RDF.  No UF authors for " +\
                    title + " No RDF necessary -->"
                title_report[title][0] = "No UF Auth"
                continue
            update_author_report(authors)

            # Datetime

            [datetime_rdf, datetime_uri] = make_datetime_rdf(value, title)

            # Publisher

            [journal_create, journal_name, journal_uri] =\
                make_journal_uri(value)
            [publisher_create, publisher, publisher_uri, publisher_rdf] =\
                make_publisher_rdf(value)

            # Journal

            [journal_rdf, journal_uri] = make_journal_rdf(value,\
                journal_create, journal_name, journal_uri)

            # Publisher/Journal bi-directional links

            publisher_journal_rdf = ""
            if journal_uri != "" and publisher_uri != "" and\
                (journal_create or publisher_create):
                publisher_journal_rdf = \
                    make_publisher_journal_rdf(publisher_uri, journal_uri)

            # Authorships

            publication_uri = vivotools.get_vivo_uri()
            title_report[title][1] = publication_uri 
            [authorship_rdf, authorship_uris] = make_authorship_rdf(authors,\
                publication_uri)

            # AuthorInAuthorships

            author_in_authorship_rdf = make_author_in_authorship_rdf(authors,\
                authorship_uris)

            #  Journal/Publication bi-directional links

            if journal_uri != "" and publication_uri != "":
                journal_publication_rdf = \
                    make_journal_publication_rdf(journal_uri, publication_uri)

            #  PubMed values

            pubmed_rdf = ""
            if 'doi' in value.fields:
                [pubmed_rdf, sub] = vivotools.update_pubmed(publication_uri,\
                    value.fields['doi'])
                if sub != "":
                    raise Exception("Non empty subtraction RDF"+\
                        "for Update PubMed")

            # Publication

            publication_rdf = make_publication_rdf(value,\
                title,publication_uri,datetime_uri,authorship_uris)
            print >>rdf_file, datetime_rdf, publisher_rdf, journal_rdf,\
                publisher_journal_rdf, author_rdf, authorship_rdf,\
                author_in_authorship_rdf, journal_publication_rdf,\
                publication_rdf, pubmed_rdf
            print >>rdf_file, "<!-- End RDF for " + title + " -->"
            print >>lst_file, vivotools.string_from_document(document),\
                'VIVO uri', publication_uri, '\n'
            update_disambiguation_report(authors, publication_uri)
        else:
            title_report[title][0] = "Found"
            title_report[title][1] = uri
            print >>rdf_file, "<!-- Found: " + title + " No RDF necessary -->"
print >>rdf_file, vivotools.rdf_footer()

#
# Reports
#
print >>rpt_file,"""

Publisher Report

Lists the publishers that appear in the bibtex file in alphabetical order.  For
each publisher, show the improved name, the number of papers in journals of this publisher,
the action to be taken for the publisher and the VIVO URI -- the URI is the new
URI to be created if Action is Create, otherwise it is the URI of the found publisher
in VIVO.

Publisher                             Papers Action VIVO URI
---------------------------------------------------------------------------------"""
publisher_count = 0
actions = {}
for publisher in sorted(publisher_report.keys()):
    publisher_count = publisher_count + 1
    [create,uri,count] = publisher_report[publisher]
    if create:
        result = "Create"
    else:
        result = "Found "
    actions[result] = actions.get(result,0) + 1
    print >>rpt_file, "{0:40}".format(publisher[0:40]),"{0:>3}".format(count),result,uri
print >>rpt_file,""
print >>rpt_file, "Publisher count by action"
print >>rpt_file, ""
for action in sorted(actions):
    print >>rpt_file, action,actions[action]
print >>rpt_file, publisher_count,"publisher(s)"

print >>rpt_file, """

Journal Report

Lists the journals that appear in the bibtex file in alphabetical order.  For
each journal, show the improved name, the number of papers t be linked to the journal,
the action to be taken for the journal and the VIVO URI -- the URI is the new
URI to be created if Action is Create, otherwise it is the URI of the found journal
in VIVO.

Journal                               Papers Action VIVO URI
---------------------------------------------------------------------------------"""
journal_count = 0
actions = {}
for journal in sorted(journal_report.keys()):
    journal_count = journal_count + 1
    [create,uri,count] = journal_report[journal]
    if create:
        result = "Create"
    else:
        result = "Found "
    actions[result] = actions.get(result,0) + 1
    print >>rpt_file, "{0:40}".format(journal[0:40]),"{0:>3}".format(count),result,uri
print >>rpt_file, ""
print >>rpt_file, "Journal count by action"
print >>rpt_file, ""
for action in sorted(actions):
    print >>rpt_file, action,actions[action]
print >>rpt_file, journal_count,"journal(s)"


print >>rpt_file, """

Title Report

Lists the titles that appear in the bibtex file in alphabetical order.  For
each title, show the action to be taken, the number of times the title appears in
the bibtex, the improved title and the VIVO URI of the publication -- the URI is the new
URI to be created if action is Create, otherwise it is the URI of the found publication
in VIVO.

Action   # Title and VIVO URI
---------------------------------------------------------------------------------"""
title_count = 0
actions = {}
for title in sorted(title_report.keys()):
    title_count = title_count +1
    [action,uri,count] = title_report[title]
    actions[action] = actions.get(action,0) + 1
    print >>rpt_file, "{0:>10}".format(action),title,uri
print >>rpt_file, ""
print >>rpt_file, "Title count by action"
print >>rpt_file, ""
for action in sorted(actions):
    print >>rpt_file, action,actions[action]
print >>rpt_file, title_count,"title(s)"

print >>rpt_file, """

Author Report

For each author found in the bibtex file, show the author's name followed by the number of papers
for the author in the bibtex to be entered, followed by 
a pair of results for each time the author appears on a paper in the bibtex.  The result
pair contains an action and a URI.  The action is "non UF" if a non-UF author stub will be
be created, the URI is the URI of the new author stub.  Action "Make UF" if a new UF author
stub will be created with the URI of the new author stub.  "Found UF" indicate the author was
found at the URI.  "Disambig" if multiple UF people were found with the given name.  The URI
is the URI of one of the found people.  Follow-up is needed to determine if correct and
reassign author if not correct.

Author                    Action   URI                                          Action   URI
----------------------------------------------------------------------------------------------"""
author_count = 0
actions = {}
for author in sorted(author_report.keys()):
    author_count = author_count + 1
    results = ""
    papers = len(author_report[author])
    action = author_report[author][1][8] # 1st report, 8th value is action
    actions[action] = actions.get(action,0) + 1    
    for key in author_report[author].keys():
        value = author_report[author][key]
        results = results + value[8] + " " + "{0:45}".format(value[9])
    print >>rpt_file, "{0:25}".format(author),"{0:>3}".format(papers),results
print >>rpt_file, ""
print >>rpt_file, "Author count by action"
print >>rpt_file, ""
for action in sorted(actions):
    print >>rpt_file, action,actions[action]
print >>rpt_file, author_count,"authors(s)"

print >>rpt_file, """

Disambiguation Report

For each publication with one or more authors to disambiguate, list the paper, and
then the authors in question with each of the possible URIs to be disambiguated, show the URI
of the paper, and then for each author that needs to be disambiguated on the paper, show
the last name, first name and middle initial and the all the URIs in VIVO for UF persons
with the same names.
"""

for uri in disambiguation_report.keys():
    print >>rpt_file,"The publication at",uri,"has one or more authors in question"
    for key,value in disambiguation_report[uri].items():
        uris = value[9].split(";")
        print >>rpt_file,"    ",value[4],value[5],value[6],":"
        for u in uris:
            person = vivotools.get_person(u)
            if 'last_name' not in person:
                person['last_name'] = "No last name"
            if 'middle_name' not in person:
                person['middle_name'] = "No middle name"
            if 'first_name' not in person:
                person['first_name'] = "No first name"
            if 'home_department_name' not in person:
                person['home_department_name'] = "No home department"
            npubs = len(person['authorship_uris'])
            print >>rpt_file,"        ",u,person['last_name'], \
                person['first_name'],person['middle_name'], \
                person['home_department_name'],"Number of pubs = ",npubs
        print >>rpt_file
    print >>rpt_file
#
#  Close the files, we're done
#
rpt_file.close()
rdf_file.close()
lst_file.close()

    
