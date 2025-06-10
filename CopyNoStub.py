# EchoLeaf Version 1.5c
# This is the CopyNoStub subroutine that will replace the present tempFileCheck
# routine in Mount.
# The present routine tests for certain conditions and does not allow files passing
#  those tests to be stubbed, although they are copied.  The purpose is to
#  allow files that need to be "live" on the cache to stay that way, while
#  the copy onto tape allows for restoration should those files need to be
#  restored.
#  This new routine will be called tempFileCheck, but will be inside of a separate file
#    i.e. this one, for ease of maintenance.   Early versions will simply put the proper
#    test conditions in a list.   We can add sophisticaiton later for screening based on
#    the apps we are working with.
#  Note:  Old routine screened for hidden files "/.".   We are removing this test condition.
# --------------------------
# October 9, 2018
# Author Fred Bonner
# Copyright 2018 EchoLeaf Systems
# --------------------------
# Note:  After testing in March 2020 -- This module is only used to screen on filenames and file folders
# Additonal screening (after writing to ToTapeQueue should be made in filemanger.py
# Which has it's own screening routines.

import re    #  Regular Expressions, used to test conditions -- will be useful into the future.

    #    ~\Z , .swp\Z , .swz\Z , Changer.cfg\Z , Folder.cfg\Z , .vdm\Z , _tmp\Z ,
    #   .bin\Z , .mf , .kmd\Z , .md\Z , kmp , kmp+ , /.mflog , /.mflog , /.trash/.md
    #   /.delete , /.audit , /.recall

def tempFileCheck(checkfile):
    
    checkterms_echoleaf = ("~\Z", ".swp\Z", ".swz\Z", "Changer.cfg\Z", "Folder.cfg\Z")
    checkterms_veeam = (".vdm\Z", "_tmp\Z", ".bin\Z")
    checkterms_komprise1 = (".mf", ".kmd\Z", ".md\Z", "kmp-", "kmp+", "/.mflog")
    checkterms_komprise2 = ("/.mflog", "/.trash/.md", "/.delete", "/.audit", "/.recall")                    
    checkterms = checkterms_echoleaf + checkterms_veeam + checkterms_komprise1 + checkterms_komprise2
            # checkterms is the collection of all tuples with all REs for testing
    returnval = 2
    
    for checkterm in checkterms:
        myregex = checkterm # loading our checkterm into a more generic variable
        myteststring = checkfile   # This is the filename we we are testing for
        p = re.compile(".*({}).*".format(myregex)) #each RE is compiled.  This format
                                                # is needed to pass a variable to compile -- finicky!
        m = p.search(myteststring) #  If not match, m yeields None -- which is what we
           # are looking for.  If it matches, we need a specific return code.
           # we just need a yes or a no.  If is does match we get all kinds of
           # information, but we don't really care about it.  We just set the return value.
           # Loop is set to break on a match -- our work here is done.
           # print myregex
           # Note using NOT m below.
           # In the echoleaf Mount module, we return a -1 if there IS a match

        if not m:
            # print "Match Not Found For Testvalue " + myregex
            returnval = True   # The testfile has not been flagged as CopyNoStub
            # print  m
            # print "Returnvalue = " + str(returnval)    
        
        else:
            # print "Match baby! for Testvalue " + myregex
            returnval = False   # The testfile has been flagged as CopyNoStub
            # print m
            # print "Returnvalue = " + str(returnval)
            break
        
    # print returnval
    return returnval
# Use print statements (above) and self contained (below) to test module

#checkfile = "nada.mf"
#copynostub = tempFileCheck(checkfile)
#print copynostub

# Notes:
                    
# ------------------------------
                    
# Tests from Komprise Documentation
# Match *.mf* # search for ".mf"
# End with .kmd search for .kmd
# End with .md  search ".md" 
# Match *kmp-*  # search for "kmp-"
# Match *kmp+*  #search for "kmp+" 
# Directories
# Match */.mflog*  #search for "/.mflog"
# Match */.trash/.md  # search for "/.trash/.md
# Match */.delete  #search for "/.delete"
# Match */.audit   # search for "/.audit"
# Match */.recall  #search for "/.recall"

# -----------------------------------

# Tests from original tempFileCheck
#    return checkFile.find("/.") == -1 and not
#checkFile.endswith("~") and not
#checkFile.endswith(".swp") and not
#checkFile.endswith(".swx") and not
#checkFile.endswith(".vdm") and not
#checkFile.endswith("_tmp") and not
#checkFile.endswith(".bin") and not
#checkFile.endswith("Changer.cfg") and not
#checkFile.endswith("Folder.cfg")                    
                    


                    

