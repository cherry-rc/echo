#     15 Nov 2024 -- updated to ELSentry v2.0a beta
"""
New Test for p2 to P3

EchoLeaf Version 1.5c
Application: createdb.py
Version: 1.0
Release Date: 01 Dec 2016
Description: Intializes data in EchoLeaf database and configuration file.

Change History:

13 Sept 2024:  Swapping out encryption modules

Copyright EchoLeaf 2016

"""


import os, sys, json, base64
import datetime as dt
import MySQLdb as mdb
from Crypto.Cipher import AES
from binascii import hexlify, unhexlify

## Below functions were in this module.  Moved to common.py

from common import load_key, encryptIT, decryptIT

# checks if provided tasks are running in the background

def alive(tasks):
    dict = {'error': 0, 'errormsg': ''}
    linecount = 0
    try:
        lines = os.popen('ps aux').readlines()
        for task in tasks:
            dict[task] = [0,'Down','&nbsp;']
            for line in lines:
                if line.find("python " + task + ".py") >= 0:
                    linecount += 1
                    dict[task][0] = 1
                    dict[task][1] = 'Up'
                    dict[task][2] = os.popen('ps -olstart= ' + line.split()[1]).readlines()[0].rstrip()
                    break
        if linecount == 0 and len(lines) < 4:
            dict['error'] = 2
            dict['errormsg'] = 'Problem with ps aux command' 
            for task in tasks:
                dict[task] = [2,'Unknown','&nbsp;']

    except:
        dict['error'] = 1
        dict['errormsg'] = str(sys.exc_info()[1])     
        for task in tasks:
            dict[task] = [2,'Unknown','&nbsp;']
    return dict

## Below now callable from common.py
"""
def encryptIt(strText):
	BLOCK_SIZE = 16
	PADDING = '{'
	pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
	EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
	DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
	key = "53f7d42cbf4d485b781f818fb9e1cd11"
	cipher = AES.new(unhexlify(key))
	return EncodeAES(cipher, strText)

def decryptIt(strEncoded):
    BLOCK_SIZE = 16
    PADDING = '{'
    pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
    DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
    key = "53f7d42cbf4d485b781f818fb9e1cd11"
    cipher = AES.new(unhexlify(key))
    return DecodeAES(cipher, strEncoded)
"""

# def resetPasswordCheck(strText):
#     result = False
#     key = load_key()
#     if encryptIT(strText, key) == "gAAAAABm6J1ZGE5BV9NHyPLtDtF5TeB45w6sWLDX4x74K_fLjUWrfF5vUsH5uvxlPLiLsn7EQjolSKwIqW--T5yHARG9zsHz6g==":
#         result = True
#     return result




class SetConfigurationCommandLine:
    """ requests and sets configuration of database """
    
    def __init__(self):
        self.dict = {"error": 0, "errormsg": "", "keepVDProp": False}
        self.config = {}
        self.confirm = "n"
        self.answer = "n"
        self.keepConfig = "n"
        self.__setValue()

    def __setValue(self):
        if os.path.isfile("EchoLeaf.config"):
            print("EchoLeaf configuration exists")
            self.confirm = input('Enter reset password?')
            # if resetPasswordCheck(self.confirm):
            self.answer = input('Keep exiting virtual Drive properties (y-yes n-no)?')
            if self.answer == "y":
                self.dict["keepVDProp"] = True
            self.keepConfig = input('Keep existing EchoLeaf configuration file (y-yes n-no)?')
            self.confirm = input('Existing EchoLeaf tables will be deleted, would like to continue (y-yes n-no)?')
            if self.confirm != "y":
                self.dict["error"] = 1
                self.dict["errormsg"] = "Operation cancelled by user"
            # else: 
            #     self.dict["error"] = 2
            #     self.dict["errormsg"] = "Invalid reset password, operation cancelled"
        if self.dict["error"] == 0 and self.keepConfig == "n":
            self.confirm = "n"     
            while self.confirm  == 'n':
                self.config["host"] = input('Enter Server IP or "localhost": ')
                self.config["database"] = input('Enter name of database: ')
                self.config["user"] = input('Enter database user account: ')
                self.config["password"] = input('Enter database user password: ')
                self.config["sysadmin"] = input('Enter EchoLeaf administrator user name: ')
                self.config["sysadminpassword"] = input('Enter EchoLeaf administrator password: ')

                testHost = self.config["host"].split(".")
                if len(testHost) != 4 and self.config["host"] != 'localhost':
                    self.config["host"] = 'localhost'

                print ("Please review your configuration values below:")
                print
                print ("Host:", self.config["host"])
                print ("Database Name:", self.config["database"])
                print ("DB User Account:", self.config["user"])
                print ("DB Account Password:", self.config["password"])
                print ("EchoLeaf Administrator User Name:", self.config["sysadmin"])
                print ("EchoLeaf Administrator Password:", self.config["sysadminpassword"])
                print (" ")
                self.confirm = input('Confirm entries: y-yes n-no e- exit:')

            if self.confirm == 'y':
                key = load_key()
                self.config["sysadminpassword"] = encryptIT(self.config["sysadminpassword"],key)
                self.config["password"] = encryptIT(self.config["password"],key)           
                fo = open("EchoLeaf.config", "w")
                fo.write( json.dumps(self.config))
                fo.close()
            else:
                self.dict["error"] = 3
                self.dict["errormsg"] = "Operation cancelled"
 
    def getResult(self):
        return self.dict


class DirectorMaintenance:
    """ locate or create working sub folder from program folder

        Program looks for to see if program folders for application have been created.  If not
        program creates folders and the initial database for the application

        logfiles - log file folder
        databases - database folder
    """
    def __init__(self):
        self.dict = {"error": 0, "errormsg": ""}
        self.logfiles = self.__folderExists("logfiles")

    def __folderExists(self,folderName):
        if not os.path.exists(folderName):
            try: 
                os.makedirs(folderName)
                print (folderName, "does not exists, creating folder...")
            except:
                self.dict["error"] = 1
                self.dict["errormsg"] = "Error creating folder " + folderName + ": " + str(sys.exc_info()[1])  
        else:
            self.dict["errormsg"] = folderName + " currently exists"
        return folderName

    def getLogFolder(self):
        return self.logfiles

    def getResult(self):
        return self.dict

 
class LogMaintenance:
    """ creates and allows addtions to log file """
    def __init__(self, logFileLocation):
        self.logFullFileName = logFileLocation + "/ex" + dt.datetime.now().strftime('%Y%m%d') + ".txt"

    def logIt(self,infoType,info):
        try:
            entryType = ["info", "warn", "error"]
            with open(self.logFullFileName, "a") as logFile:
                 logFile.write('%s|createdb|%s|%s\n' % (dt.datetime.now().strftime('%Y%m%d %H:%M:%S'),entryType[infoType],info))
        except:
            print("Error writing to error log: " + str(sys.exc_info()[1]))

class DBMaintenance:
    """ creates default EchoLeaf database if it does not exist"""
    def __init__(self, keepVDProp):
        config = {}
        self.dict = {"error": 0, "errormsg": ""}
        try:
            with open("EchoLeaf.config", "r") as configuration:
                config =  json.loads(configuration.readline())  
        except:
            self.dict["error"] = 1
            self.dict["errormsg"] = "Unable to load database configuration: " + str(sys.exc_info()[1])  
        
        if self.dict["error"] == 0:
            try:
                conn = mdb.connect(str(config["host"]), str(config["user"]), decryptIT(str(config["password"])), str(config["database"]));
            except:
                self.dict["error"] = 2
                self.dict["errormsg"] = "Unable to connect to database: " + str(sys.exc_info()[1])                    

        if self.dict["error"] == 0:
            try:
                cur = conn.cursor() 
                cur.execute("SHOW TABLES")
                tables = cur.fetchall() 
                if len(tables) > 0:
                    for table in tables: 
                        if table[0] == 'Configuration':
                            if not keepVDProp:
                                cur.execute("DROP TABLE " + table[0] );
                        else:
                             cur.execute("DROP TABLE " + table[0] );
                    conn.commit() 
                 
                cur.execute("CREATE TABLE Directories (DirectoryId BIGINT PRIMARY KEY  NOT NULL  AUTO_INCREMENT , ParentId BIGINT NOT NULL , DirectoryName VARCHAR(255) NOT NULL , FullName VARCHAR(512)  , EntryDate DATETIME NOT NULL, KEY inx_dir_ParentId (ParentId))")
                cur.execute("CREATE TABLE Files (FileId BIGINT PRIMARY KEY  NOT NULL   AUTO_INCREMENT, FileName VARCHAR(255) NOT NULL , Size BIGINT NOT NULL , CreateDate DATETIME NOT NULL , ModifyDate DATETIME NOT NULL , ArchiveDate DATETIME NOT NULL , DirectoryId BIGINT NOT NULL, LastAccess DATETIME NOT NULL, KEY inx_files_DirectoryId (DirectoryId), KEY inx_files_FileName (FileName))")
                cur.execute("CREATE TABLE LTOTapes (TapeUID CHAR(8) PRIMARY KEY  NOT NULL , Status VARCHAR(8) NOT NULL , DupSequence INT, ActiveStart DATETIME, FullDate DATETIME, TapeType VARCHAR(10) , InLibrary INTEGER NOT NULL )")
                cur.execute("CREATE TABLE TapeFiles (TapeUID CHAR(8) NOT NULL , FileId BIGINT NOT NULL , DupSequence INTEGER NOT NULL , PRIMARY KEY (TapeUID, FileId), KEY inx_tapefil_FileId (FileId))")
                cur.execute("CREATE TABLE ClearDiskQueue (FullFileName VARCHAR(255) PRIMARY KEY  NOT NULL , DateQueued DATETIME NOT NULL , DateToRemove DATETIME NOT NULL , InProcess INTEGER NOT NULL, ClearWarning INTEGER  NOT NULL)")                
                cur.execute("CREATE TABLE RemoveDiskQueue (FullFileName VARCHAR(255) PRIMARY KEY  NOT NULL , DateQueued DATETIME NOT NULL , DateToRemove DATETIME NOT NULL , InProcess INTEGER NOT NULL, NoTapeWarning  INTEGER  NOT NULL, Location VARCHAR(24))")
                cur.execute("CREATE TABLE ToDiskQueue (FileId BIGINT PRIMARY KEY  NOT NULL , DateQueued DATETIME NOT NULL , Priority INTEGER NOT NULL , DateToCopy DATETIME NOT NULL , InProcess INTEGER NOT NULL, Location VARCHAR(24), DiskFullWarning INTEGER NOT NULL )")
                cur.execute("CREATE TABLE ToTapeQueue (FullFileName VARCHAR(255) PRIMARY KEY  NOT NULL , DateQueued DATETIME NOT NULL , Priority INTEGER NOT NULL , DateToCopy DATETIME NOT NULL , InProcess INTEGER NOT NULL , NoTapeWarning INTEGER NOT NULL, CopyCount INTEGER NOT NULL,  Issue VARCHAR(64) )")
                cur.execute("CREATE TABLE ErrorQueue (FullFileName VARCHAR(255) PRIMARY KEY  NOT NULL , DateQueued DATETIME NOT NULL , Issue  VARCHAR(16) NOT NULL )")
                cur.execute("CREATE TABLE DupFailures (FailureId BIGINT PRIMARY KEY  NOT NULL UNIQUE AUTO_INCREMENT, FileName VARCHAR(255) NOT NULL , EntryDate DATETIME NOT NULL , Action VARCHAR(12), NewFileName VARCHAR(255), ErrMsg VARCHAR(255))")
                cur.execute("CREATE TABLE ToTapeLog (EventId BIGINT PRIMARY KEY  NOT NULL  AUTO_INCREMENT , EntryDate DATETIME NOT NULL , TapeUID VARCHAR(8) NOT NULL , FullFileName VARCHAR(255) NOT NULL, KEY inx_totapelog_EntyDate (EntryDate) )")
                cur.execute("CREATE TABLE WinShares (Folder VARCHAR(255) NOT NULL , ShareName VARCHAR(255) NOT NULL , PRIMARY KEY (Folder, ShareName))")    
                cur.execute("CREATE TABLE WinShareUsers (Folder VARCHAR(255) NOT NULL , UserName VARCHAR(255) NOT NULL , PRIMARY KEY (Folder, UserName))")
                cur.execute("CREATE TABLE TapeManagement (RequestId INT(11) NOT NULL AUTO_INCREMENT, TapeId CHAR(8) NOT NULL, Origination VARCHAR(4) DEFAULT NULL, VDStatus VARCHAR(24) DEFAULT NULL, LTFSStatus VARCHAR(24) NOT NULL, Status VARCHAR(16) NOT NULL, EntryDate DATETIME NOT NULL, StatusDate DATETIME NOT NULL, RequestType VARCHAR(64) NOT NULL, ResultText VARCHAR(256) DEFAULT NULL, RequestTypeShort VARCHAR(45) NOT NULL, PRIMARY KEY (RequestId))")  
                cur.execute("CREATE TABLE RestoreManagement (RequestId int(11) NOT NULL AUTO_INCREMENT, FileId bigint(20) NOT NULL, FileName varchar(128) NOT NULL, TapeUID char(8) NOT NULL, Status varchar(16) NOT NULL, EntryDate datetime NOT NULL, StatusDate datetime NOT NULL, RestoreTo varchar(16) NOT NULL, ResultText varchar(256) NOT NULL, PRIMARY KEY (RequestId))") 
                cur.execute("CREATE TABLE FileMoveLog (LogId bigint(20) NOT NULL AUTO_INCREMENT, EntryDate datetime DEFAULT NULL, Direction int(11) DEFAULT NULL, Source varchar(126) DEFAULT NULL, Destination  varchar(126) DEFAULT NULL, FileName varchar(256) DEFAULT NULL, PRIMARY KEY (LogId))")

                if not keepVDProp:
                    cur.execute("CREATE TABLE Configuration (Property VARCHAR(24) PRIMARY KEY  NOT NULL , PropertyValue VARCHAR(96) NOT NULL, Access TINYINT, Header VARCHAR(48), Info VARCHAR(255) )")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('TapeDrive', '/mnt/ltfs', 1, 'Library Mount Point', 'Mount point/ of LTFS Library.') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('TapeVolumeLabel', 'EchoLeaf Virtual Drive', 0, 'Tape Volume Label', 'Tape volume label.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('VDiskVolumeId', '0x12345678', 0, 'Virtual Disk Volume Id', 'Virtual disk windows requirement.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('VDiskMountPoint', '/home/echoleaf/vd', 1, 'Virtual Disk Mount Point', 'Folder location where virtual disk is to be mounted. Location should not contain any files.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('CacheLocation', '/home/echoleaf/cache', 1, 'Cache Location', 'Folder location where files should be actually written when using the virtual drive.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('DuplicationDrive', 'none', 1, 'Duplication Drive Mount Point', 'Folder location/ device mount point to duplicate files that are being written to disk. Set to none if location does not exist.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('MailRelay', 'none', 0, 'Mail Relay', 'Email server to use to route mail if local SMTP is not available.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('MailHost', 'localhost', 1, 'Mail Host', 'This is the host running your SMTP server. You can specifiy IP address of the host or a domain name. Use localhost if running on local machine.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('MailPort', '25', 1, 'Mail Port', 'Port where SMTP server is listening.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('MailFrom', 'none', 1, 'From Email Address', 'From email address, for the EchoLeaf system. Set to none if email services are not being used.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('AdminEmail1', 'none', 1, 'System Admin Email', 'Email address of Echo Leaf administrator who will be receiving notifications. Set to none if not applicable')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('AdminEmail2', 'none', 1, 'System Admin Email 2', 'Email address of secondary EchoLeaf Administrator. Set to none if not applicable')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('NotifyOnWarning', 'no', 1, 'Notify on Warning', 'Send administrator emails about system warnings. Set to yes or no.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('SubjectWarning', 'EchoLeaf Warning', 1, 'Subject Warning', 'Subject line for warning emails.') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('NotifyOnError', 'yes', 1, 'Notify on Error', 'Send administrator emails about system errors. Set to yes or no.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('SubjectError', 'EchoLeaf Error', 1, 'Subject Error', 'Subject line for error emails.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('NotifyOnLowCache', 'yes', 1, 'Notify on Low Cache', 'Send out notification when disk cache is below set minimum. Set to yes or no.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('SubjectLowCache', 'EchoLeaf Warning Low Cache', 1, 'Subject Low Cache ', 'Subject line for low cache error emails.') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('MinCacheGB', '10', 1,'Minimum Cache (GB)', 'Minimum value in GB for cache warning.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('WriteDelayHours', '1', 1, 'Write Delay (hrs)', 'Write delay to move files from cache to tape in hours.') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('NewFileHoldHours', '16', 0, ' ', ' ') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('MaxFileSizeGB', '20', 1, 'Max File Size (GB)', 'Maximum file size accepted for archiving in GB.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('TapeCopies', '1', 1, 'Tape Copies', 'Number of copies to be moved to different tapes.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('HDTransfer', 'active', 0, ' ',' ')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('FileManagerCachSize', '50', 1, 'File Manger Cache Size', 'Number of file names to retain in memory to speed access to files.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('ToTapeLog', 'no', 0, ' ', ' ') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('AllowTapeDelete', 'no', 1, 'Allow Tape Delete', 'Allow files to be deleted once written to tape.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('CopyBackRemoveDelay', '1', 1, 'Copyback Remove Delay (hrs)', 'When a file is retreived from tape to cache, the amount of time to wait before stubbing the file in cache.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('FileManagerStart', '6', 1, 'File Manager Start of Day', 'Starting time within the day when the file manager should be working.') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('FileManagerEnd', '23', 1, 'File Manager End of Day', 'End time within the day when the file manager should be stopped.') ")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('FileManagerInterval', '1', 1, 'File Manager Interval (min)', 'Sleep interval once the File Manager has completed a full maintenance cycle.') ")              
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('SoftwareLocation', '/home/echoleaf/ui', 1, 'EchoLeaf Software Install', 'Folder location of EchoLeaf software.') ")                                   
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('RestoreAlternate', '/home/echoleaf/restore', 1, 'Restore Alternate', 'Alternate restore folder different from the Cache for moving files from tape to disk.')")
                    cur.execute("INSERT INTO Configuration (Property, PropertyValue, Access, Header, Info) VALUES ('ProductionEnv', 'yes', 1, 'Production Environment', 'Impacts the logging of the virtual drive. Extensive logging occurs in a non-production environment.')")
                    conn.commit()
                conn.close()
                self.dict["errormsg"] = "New EchoLeaf database tables created"
            except:
                self.dict["error"] = 3
                self.dict["errormsg"] = "Unable to create tables: " + str(sys.exc_info()[1])                    

    def getResult(self):
        return self.dict


def main():
        print ("createdb started...")
        result = alive(['mount'])
        if result['mount'][0] == 1:
            print ("Virtual drive is currently running, please stop before continuing!")
        else:
            buildConfig = SetConfigurationCommandLine();
            if buildConfig.getResult()["error"] == 0:
                folder = DirectorMaintenance();
                if folder.getResult()["error"] == 0:
                    log = LogMaintenance(folder.getLogFolder())
                    log.logIt(0, "createdb started");
                    db = DBMaintenance(buildConfig.getResult()["keepVDProp"])
                    log.logIt(0, buildConfig.getResult()["errormsg"]); 
                    print(db.getResult()["errormsg"])
                else:
                    print (folder.getResult()["errormsg"])
            else:     
                print (buildConfig.getResult()["errormsg"])
        print ("createdb finished!")

if __name__ == "__main__":
    main()
