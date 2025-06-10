#     15 Nov 2024 -- updated to ELSentry v2.0a beta
#   FM Timer Project 10 Dec 2024




# Function to Aggregate Relevant System Data for Aggregate Reporting
# Works with filemanager 1.5c2
#  Aggregate as txt info from dashboard and put into a single text file to be emailed each day
#  requires access to common.py
#  this function will be part of a system embedded in runELArchive() with runs daily after midnite
#  June 8 2020 / v1.0
#  July 11 2020 / v1.0
#  Copied from PhoneHome05.py

# Make sure that these are all in FileManager
import common
import os
import time
from datetime import datetime
import datetime as dt
import smtplib
#     
# Move Below function to File Manager. 

def phoneHome():
    # Replace with Config pull after updated config data
    ELLocation = 'ELATstSpank'
    emailSubject = "Daily EchoLeaf Stats from " + ELLocation 
    
    # print emailSubject

    # Set up filename for email message with header.  This file will go in the email.

    emailMessageText = ' EchoLeaf Test System Status Report  \n'

    now = datetime.today()
    todaydatestr = now.strftime("%Y%m%d_%X")
    newFileName = ELLocation + 'Stats_' + todaydatestr + '.txt'  
   
    emailMessageText = emailMessageText + '   datetime_of_report = ' + todaydatestr + '\n'
    emailMessageText = emailMessageText + '   name_of_messsage_file = ' + newFileName + '\n'
        
    # Determines if FileManager and Mount are running
    # def isEchoLeafAlive():
    
    task1 = 'filemanager'  
    dict = common.alive([task1])
    
    # print 'filemanager_status'
    fmStatus = dict[task1][1]
    # print fmStatus
    
    # print 'filemanager_uptime'
    fmUptime = dict[task1][2]
    # print fmUptime
    
    emailMessageText = emailMessageText + '   filemanager_status = ' + fmStatus + '\n'
    emailMessageText = emailMessageText + '   filemanager_uptime = ' + fmUptime + '\n'
    
    task1 = 'mount'  
    dict = common.alive([task1])
    # print 'mount_status'
    mountStatus = (dict[task1][1])
    # print mountStatus
            
    # print 'mount_uptime'
    mountUptime = dict[task1][2]    
    # print mountUptime

    emailMessageText = emailMessageText + '   mount_status = ' + mountStatus + '\n'
    emailMessageText = emailMessageText + '   mount_uptime = ' + mountUptime + '\n'

    # pulls data from Library and caclulates tapes, volumes, percent used etc.
    # def getTapeAttributes2():	

    objectType = 'cartridge'
    adminCmd = 'leadm tape list -o xml'   
    dict = common.ltfsAdminCmd(objectType,adminCmd)
    # dict is the data object derived from the leadm tape list -o xml command
    # Below routine calculates basic storage statistics in library

    ctr = 0
    TotCap = 0
    UsedCap = 0
    FormattedTapes = 0
    RemCap = 0
    FreeOnCache = 0
    
    for data in dict['data']:
        ctr = ctr + 1
        if (data[1] == 'WRITABLE' or data[1] =='METADATA_WRITABLE'):
            FormattedTapes = FormattedTapes + 1            
            TotCapTemp = int(data[25])		    	
            TotCap = TotCap + TotCapTemp            
            RemCapTemp = int(data[26])
            RemCap = RemCap + RemCapTemp
    
    UsedCap = TotCap - RemCap
    PercentCapUsed = (UsedCap * 100)/(TotCap)
    
    # print 'total_tapes'
    TotalTapesStr = str(ctr)
    # print TotalTapesStr
    emailMessageText = emailMessageText + '   total_tapes = ' + TotalTapesStr + '\n'
        
    # print 'total_formatted_tapes'
    FormattedTapesStr = str(FormattedTapes)
    # print FormattedTapesStr
    emailMessageText = emailMessageText + '   total_formatted_tapes = ' + FormattedTapesStr + '\n'
            
    # print 'total_capacity'
    TotCapStr = str(TotCap)
    # print TotCapStr
    emailMessageText = emailMessageText + '   total_capacity = ' + TotCapStr + '\n'
            
    
    # print 'total_used_capacity'
    UsedCapStr = str(UsedCap)
    # print UsedCapStr
    emailMessageText = emailMessageText + '   total_used_capacity = ' + UsedCapStr + '\n'    
    
    # print 'remaining_capacity'
    RemCapStr = str(RemCap)
    # print RemCapStr
    emailMessageText = emailMessageText + '   remaining_capacity = ' + RemCapStr + '\n'
            
    
    # print 'percent_used_capacity'
    PercentCapUsedStr = str(PercentCapUsed)
    # print PercentCapUsedStr
    emailMessageText = emailMessageText + '   percent_used_capacity = ' + PercentCapUsedStr + '\n'
            
    
    # Fetch Cache Free Space    
    FreeOnCache = common.cacheFreespace()
    # print 'free_space_on_cache'
    FreeOnCacheStr = str(FreeOnCache)
    # print FreeOnCacheStr
    emailMessageText = emailMessageText + '   free_space_on_cache = ' + FreeOnCacheStr + '\n'
        
    # Determines the number of files that have been moved in last 24 hours.  Min = 3.        
    # def getFileMoveStatus():
#    ctr = 0
#    dict = common.fileMoveLog()
#    for data in dict['data']:
#        ctr = ctr + 1

    ctr = 0
    dict = common.fileMoveLog()

    if 'data' in dict and dict['data']:  # Check if 'data' key exists and is not empty
        for data in dict['data']:
            ctr = ctr + 1
    else:
        print("No data found in fileMoveLog result.")
    # Handle the case where there's no data, e.g., log an error, skip processing, etc.





        
    filesInMoveLog = ctr
    filesInMoveLogStr = str(filesInMoveLog)    
    # print 'files in move log'
    # print filesInMoveLogStr
    emailMessageText = emailMessageText + '   files in move log = ' + filesInMoveLogStr + '\n' + '      end       \n'
    
    # revise subject based on Status
    emailSubject = "Daily EchoLeaf Stats from " + ELLocation
    
        
    # Debug Print email message 
    # print ('email message text')
    print(emailMessageText)

    sendPhoneHomeMail(emailSubject,emailMessageText)
    
    
       
# Below function can be used for Testing.  Not in production.

'''
def sendPhoneHomeMailGeorge(subject, body):
    info = common.DriveProperties().getInfoAll()
	# All Drive Properties are now available

	# Determine if Mail is Available, if yes, send mail.
	
    mailAvailable = True
    
    if info["MailFrom"] != "none" and info["AdminEmail1"] != "none":
        mailAvailable = True
        
    if not mailAvailable:
        print ("EchoLeaf not configured to send email")		    
        	 
    if mailAvailable:
        try:
	    print ' start of email send section'
	    print ' Value of AdminEmail %s' %info["AdminEmail1"] 
	    print ' Value of MailFrom = %s' %info["MailFrom"]
            mailTo = info["AdminEmail1"].split()
	    MailFrom = info["MailFrom"] 
#	    print mailTo, MailFrom
#	    print subject 
#	    print body
            message = """\
From: %s
To: %s
Subject: %scd 

%s
""" % (MailFrom, ", ".join(mailTo),subject, body)

	    print 'The test of the email message'
	    print message
	    smtpObj = smtplib.SMTP('localhost')
	    smtpObj.set_debuglevel(1)
            smtpObj.sendmail(MailFrom, mailTo, message)     
            smtpObj.quit()
        except:
			print "Mail Error"
			
            #logIt(0, "on SendMail: "+ str(sys.exc_info()[1]))    
    
    
    # write data to file     

#    with open(newFileName, 'a') as file_object:
#        file_object.write(emailMessageText)

'''


def sendPhoneHomeMail(subject, body):
    """
    Sends an email notification if configured.
    """

    info = common.DriveProperties().getInfoAll()
#	DELETEME Added by GED
    temp1 = info.get("MailFrom")
    print(temp1)
    temp2 = info.get("AdminEmail1")
    print(temp2)
#        End DELETEME

    if info.get("MailFrom") and info.get("AdminEmail1"):
        try:
            mail_to = [info["AdminEmail1"]]
            if info.get("AdminEmail2") != "none":
                mail_to.append(info["AdminEmail2"])

            smtp_obj = smtplib.SMTP(info.get("MailHost", "localhost"), int(info.get("MailPort", 587)))
            
            message = f"""\
From: {info["MailFrom"]}
To: {", ".join(mail_to)}
Subject: {subject}

{body}
"""
            smtp_obj.sendmail(info["MailFrom"], mail_to, message)
            smtp_obj.quit()

        except Exception as e:
            print(f"Mail Error: {e}")
    else:
        print("EchoLeaf not configured to send email")





# Readability note:  In "message" above, each subsequent %s gets data from the
# % (  after it, comma deliminted.   Each comma separates a %s value.

			
            #logIt(0, "on SendMail: "+ str(sys.exc_info()[1]))    
    
    
    # write data to file     

#    with open(newFileName, 'a') as file_object:
#        file_object.write(emailMessageText)


# unrem below to test module alone        		       
phoneHome() 

   
