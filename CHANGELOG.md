    Version 1.0 MC 2012-08-16
    --  Using VIVO as the current state, process a bibtex file, checking VIVO
        for the presence of paper, authors, journal and publisher.  Create
        missing entities as needed.  Never delete or change anything.  Only
        add new items. Don't handle papers with more than 50 authors.

    Version 1.1 MC 2012-09-02
    --  Corporate authorship.  bibtex2rdf now handles author lists of any
        length. A parameter, MAX_AUTHORS controls how many authors appear in
        an authorship before the rest are placed in a corporate authorship.
    --  New report for disambiguation lists the paper and all the choices for
        an author that needs to be disambiguated
    --  Cosmetic improvements to paper titles -- roman numerals, 's, escaped
        chars &,<,>
    --  Fix bug in lst files that caused author lists to be out of order
    --  Fix bug in which bibtex with no journal field attempted to create
        publisher/journal cross links
    --  Version of the software now in the name of the file

      Version 1.2 MC 2012-11-25
    --  Use UF Entity rather than UFID as the base for the dictionaries to get
        more people into the dictionaries and cut down on stub creation
    --  Use key_string on people names to improve matches on mixed case names,
        names with space, punctuation and unicode
    --  Show the current time on the console at the start of each major step
        in the work
    --  Move make dictionary and find functions to vivotools

    Version 1.2.1 MC 2013-04-06
    --  Fix bug regarding disambiguated UF authors.  Version 1.2 erroneously
        created concatenated URIs in Authorships and authorInAuthorship. 1.2.1
        picks a URI.  This is consistent with previous versions.
    --  Updated harvestedBy text to indicate version 1.2.1
    Version 1.2.2 MC 2013-12-21
    --  Show name parts and number of publications for each alternative in
        the disambiguation report
    Version 1.3 MC 2014-01-01
    --  Uses update_pubmed to provide PMCID, NIHMSID, Abstract, full text link,
        MESH keywords and grants cited for all papers added that have a DOI and
        can be found in PubMed.  The Concept dictionary is created and
        updated as needed.
    --  Requires pybtex 1.6 which uses mixed case bibtex field names
    --  Provided test.bib for simple testing

