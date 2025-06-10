#     15 Nov 2024 -- updated to ELSentry v2.0a beta
"""
EchoLeaf Version 1.5c1
Application: mount.py
Version: 1.0
Release Date: 01 Dec 2016
Description:  Mounts virtual drive.  Enabling and disabling occurs through administrative program.

Change History:

FB 10 Oct 2018
    1. Redirect tempFileCheck to new module CopyNoStub
        Accomodating increasing requirements for files to stay on cache.
        Note this module removes the previous screen for /. hidden files.
        Not sure why we did that before.

    2. Changes the test for directory from "isdir(path) to isdir("/" + path)
       Without that change Hidden Directories are passed over. 

FB  Corrected bug in WriteDelayHours (Was hard-coded to 9)
FB  Added screen for def toTapeQueue

Begin Update for p2 to p3 
Oct 21, 2024   We have a P3 Virtual Drive !!           

Copyright EchoLeaf 2016,2019,2020
"""


#!/usr/bin/env python

# from __future__ import with_statement
# New Above unnecessary with python 3+

import os
import sys
import errno

    #  Added 10 Oct 2018
from CopyNoStub import tempFileCheck
    # remming out old tempFileCheck
    
# using only one decryption routine
from common import load_key, decryptIT

# Testing import routines.  The one below does not work    
#from fusepy import FUSE, FuseOSError, Operations

# This one is recommended by the Coding Assistant
import fuse
from fuse import FuseOSError, Operations

# New from fusepy import FUSE, FuseOSError, Operations -- installed fusepy

from time import time
import stat    # for file properties
import datetime as dt
import time
import smtplib
import shutil
import json
# Old import MySQLdb as mdb
#Old from Crypto.Cipher import AES
from binascii import hexlify, unhexlify
import base64
import mysql.connector as mdb
from cryptography.fernet import Fernet
# import pdb


# def tempFileCheck(checkFile):
#    return checkFile.find("/.") == -1 and not checkFile.endswith("~") and not checkFile.endswith(".swp") and not checkFile.endswith(".swx") and not checkFile.endswith(".vdm") and not checkFile.endswith("_tmp") and not checkFile.endswith(".bin") and not checkFile.endswith("Changer.cfg") and not checkFile.endswith("Folder.cfg")
# now in external module CopyNoStub


def newDateStamp():
    return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S') 


class DataStore:
    """  manages a single open connection """ 
 
    def __init__(self, info):
        self.info = info
        self.conn_status = []
        self.conn_pool = []
        self.cur_pool = []

# Function Below Had errors / rewritten

    def connect(self):
        """
        Gets a connection from the pool. Creates a new connection if needed.
        Returns a valid cursor index or None on error.
        """
        
        j = -1
        if len(self.conn_status) > 0:
            for index, item in enumerate(self.conn_status):
                if self.conn_status[index]:
                    self.conn_status[index] = False
                    try:
                        self.cur_pool[index] = self.conn_pool[index].cursor()
                        return index  # Return the index immediately if successful
                    except Exception as e:
                        print(f"Error creating cursor for existing connection: {e}")
                        self.connect_reset(index)  # Reset and try the next connection

        # If no available connection was found, create a new one
        try:
            conn = mdb.connect(  # Assign to 'conn' for consistency
                host=self.info["host"],
                user=self.info["user"],
                password=self.info["password"],
                database=self.info["database"]
            )
            self.conn_pool.append(conn)
            self.conn_status.append(False)  # Update conn_status
            j = len(self.conn_pool) - 1
            self.cur_pool.append(self.conn_pool[j].cursor())
            return j
        except mdb.Error as e:
            print(f"Error establishing new connection: {e}")
            return None  # Return None to indicate connection failure

    
    def connect_reset(self,cursor):
        cursorReset = 0
        # print "Resetting cursor", cursor
        try:
            self.cur_pool[cursor].close()
        except:
            print('%s|vd|class DataStore|def connect_reset|error reseting cursor|%s' % (newDateStamp(),str(sys.exc_info()[1])))
            cursorReset = 1
        try:
            self.conn_pool[cursor].close()
        except:
            print('%s|vd|class DataStore|def connect_reset|error reseting connection|%s' % (newDateStamp(),str(sys.exc_info()[1])))
            cursorReset = 2
   
        self.conn_pool[cursor] = mdb.connect(
            host=self.info["host"],
            user=self.info["user"],
            password=self.info["password"],
            database=self.info["database"]
         ) 
        self.conn_pool[cursor].autocommit(True)
        self.cur_pool[cursor] = self.conn_pool[cursor].cursor()

 
    def disconnect(self):
        for index, item in enumerate(self.conn_pool):
            try:
                if not self.conn_pool[index].open:
                    self.conn_pool[index].close()
            except:
                print('%s|vd|class DataStore|def disconnect|error closing connection|%s' % (newDateStamp(),str(sys.exc_info()[1])))
 
    def free(self, cursor):
        self.cur_pool[cursor].close()
        self.conn_status[cursor] = True
 
    def write(self, query, values = ''):
        cursor = self.connect()
        try:
            if values != '':
                self.cur_pool[cursor].execute(query, values)
            else:
                self.cur_pool[cursor].execute(query)
            self.conn_pool[cursor].commit()
            self.free(cursor)
        except:
            print('%s|vd|class DataStore|def write|write retry|%s' % (newDateStamp(),str(sys.exc_info()[1])))
            self.connect_reset(cursor)
            if values != '':
                self.cur_pool[cursor].execute(query, values)
            else:
                self.cur_pool[cursor].execute(query)
            self.conn_pool[cursor].commit()
            self.free(cursor)

    def read(self, query, values = ''):
        cursor = self.connect()
        try:
            if values != '':
                self.cur_pool[cursor].execute(query, values)
            else:
               self.cur_pool[cursor].execute(query)
        except:
            print('%s|vd|class DataStore|def read|read retry|%s' % (newDateStamp(),str(sys.exc_info()[1])))
            self.connect_reset(cursor)
            if values != '':
                self.cur_pool[cursor].execute(query, values)
            else:
               self.cur_pool[cursor].execute(query)
        return cursor, self.cur_pool[cursor]
   
class FileCacheManager:
    """  manages name of recently accessed files """

    def __init__(self,configCacheMaxSize):
        self.cacheMaxSize = int(configCacheMaxSize)
        self.fileTapes = {}
        self.recentFiles = []

    def addFile(self,fileName,tapeName):
        "add new file tape combination"
        
# has_key depracated        if not self.fileTapes.has_key(fileName):
        if fileName not in self.fileTapes:   
            if len(self.recentFiles) > self.cacheMaxSize:
#                if self.fileTapes.has_key(self.recentFiles[0]):
                if self.recentFiles[0] in self.fileTapes:                                        
                    del self.fileTapes[self.recentFiles[0]]
                self.recentFiles.pop(0)
            self.fileTapes[fileName] = tapeName
            self.recentFiles.append(fileName)

    def inList(self,fileName):
        " look if file in list "
#        return self.fileTapes.has_key(fileName)
        return fileName in self.fileTapes        

    def newRoot(self,fileName):
        " returns tape to create new root for file"
        return self.fileTapes[fileName]

    def deleteFile(self, fileName):
#        if self.fileTapes.has_key(fileName):
        if fileName in self.fileTapes:          
            fileTapes.Remove(c)
            del self.fileTapes[fileName]
            self.recentFiles.remove(fileName)

class DriveProperties:
    
    # Extracts properities from configuration table
    def __init__(self):
        self.info = {'error': 1, 'errormsg': 'Unable to open configuration file'}
        try:
            with open("EchoLeaf.config", "r") as configuration:
				#New fix readline statement / It = IT below
                self.info = json.load(configuration) 
                
                # we need to add loadkey and key to decryptIT calls
            key = load_key()
                
            self.info["sysadminpassword"] = decryptIT(self.info["sysadminpassword"],  key)
            self.info["password"] = decryptIT(self.info["password"],  key)           
            self.info["error"] = 0
            self.info["errormsg"] = ''                 
        except:
            self.info["error"] = 2
            self.info["errormsg"] = "Error opening configuration file: " + str(sys.exc_info()[1]) 
        
        if self.info["error"] == 0:
            try:
                conn = mdb.connect(
                    host=self.info["host"],
                    user=self.info["user"],
                    password=self.info["password"],
                    database=self.info["database"]
                 )
#                self.info["host"], self.info["user"], self.info["password"], self.info["database"]);
                cur = conn.cursor()
                cur.execute("SELECT * FROM Configuration")
                rows = cur.fetchall()
                for row in rows:
                    self.info[str(row[0])] = str(row[1])
                cur.close()
                conn.close()
                programPath =  os.path.abspath('')        
            except:
                self.info["error"] = 2
                self.info["errormsg"] = "Error opening database :" + str(sys.exc_info()[1])  
        
        programPath =  os.path.abspath('')
        self.info["programFolder"] = programPath
        self.info["logFolder"] = os.path.join(programPath, "logfiles")

    def getInfo(self, infoProperty):
        """ Return value of provided property """
        infoValue = ''
#        if self.info.has_key(infoProperty):
        if infoProperty in self.info:            
            
            infoValue = self.info[infoProperty]
        return infoValue

    def getInfoAll(self):
        """ return all properties in dictionary """
        return self.info

    def dbExists():
        return True if self.info["error"] == 0 else False

class LogMaintenance:
    """ creates and allows endtried to log file """
    
    def __init__(self,info):
        self.info = info
        self.mailAvailable = False
        self.logCounter = 0
        if self.info["error"] == 0:
            if self.info["MailFrom"] != "none" and self.info["AdminEmail1"] != "none":
                self.mailAvailable = True

    def __logFullFileName(self):
        return os.path.join(self.info["logFolder"], "ex" + dt.datetime.now().strftime('%Y%m%d') + ".txt")

    def logIt(self,infoType,issue):
        try:
            entryType = ["info", "warn", "error"]
            self.logCounter = self.logCounter + 1
            with open(self.__logFullFileName(), "a") as logFile:
                 logFile.write('%s|vd|%s|%s\n' % (newDateStamp(), entryType[infoType], issue))
        except:
            print('%s|vd|class LogMaintenance|def logIt|error writing to log|%s' % (newDateStamp(),str(sys.exc_info()[1])))
 
        if self.info["NotifyOnWarning"] == "yes" and infoType == 1:
            self.__sendMail(self.info["SubjectWarning"], issue)
        else:
            if self.info["NotifyOnError"] == "yes" and infoType == 2:
                self.__sendMail(self.info["SubjectError"], issue)
    
    def __sendMail(self, subject, body):
        if self.mailAvailable:
            try:
                mailTo = [self.info["AdminEmail1"]]
                if self.info["AdminEmail2"] != "none":
                    mailTo.append(self.info["AdminEmail2"])
                smtpObj = smtplib.SMTP('localhost') 
                if self.info["MailHost"] != "localhost":
                    smtpObj = smtplib.SMTP(self.info["MailHost"], int(self.info["MailPort"]))
                message = """\
From: %s
To: %s
Subject: %s

%s
""" % (self.info["MailFrom"], ", ".join(mailTo), subject, body)
                smtpObj.sendmail(self.info["MailFrom"], mailTo, message)     
                smtpObj.quit()
            except:
                self.logIt(0,('%s|%s|%s|%s' % ("class LogMaintenance", "__sendMail", "error on sending mail",str(sys.exc_info()[1]))))




class VirtualDrive(Operations):
    def __init__(self, configInfo):

        self.mInfo = configInfo
        self.root = self.mInfo["CacheLocation"].replace("\\", "/")
        self.mRootPath = self.mInfo["CacheLocation"].replace("\\", "/")
        self.fileOp = {}
        self.fileMo = {}
        self.basePath = self.mRootPath
        self.log = LogMaintenance(self.mInfo)
        self.ds = DataStore(self.mInfo)
        self.fileList = FileCacheManager(self.mInfo["FileManagerCachSize"])
        self.emptyCache = os.path.join(self.mRootPath, "tmsemptycache")
        self.minCacheMsgSent = False
        self.dupDrive = False
        self.dupWarning = False
        self.lastCreateDate = dt.datetime.now()
        self.lastModifyDate = dt.datetime.now()
        self.lastLength = 0
        self.lastFileName = ""
        self.dPath = self.mInfo["DuplicationDrive"]

        self.attrDir = ""
        self.attrParentId = 0
        self.attrFileName = ""
        self.attrFileLength = 0
        self.inRelease = False
        self.releasePath = ""
        self.lastPath = ""
        self.lastPathTime = dt.datetime.now()
        self.lastItemCheck = True

        if self.dPath != "none" and self.dPath != "":
            self.dupDrive = True
 
        if not os.path.exists(self.emptyCache):
            os.makedirs(self.emptyCache)

    def checkAttrOnTape(self, newFileName):
        " get file length"
        
        fileLength = 0
        parentId = 0
        lastPartFound = -1
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName))
        maxDirParts = len(fileNameParts) - 1
        tempDir = ""

        try:
            if self.attrFileName == newFileName:
                fileLength  =  self.attrFileLength
            else:
                if maxDirParts > 0:
                    tempDir = newFileName.replace(newFileName,"/" + fileNameParts[maxDirParts])
                    if tempDir == self.attrDir:
                        parentId = self.attrParentId
                        lastPartFound = 0
                    else:
                        for i in range(maxDirParts): # cycle through directory parts to find file
                            curIndex, cur = self.ds.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i],parentId))
                            row = cur.fetchone()
                            if row != None:
                                parentId = row[0]
                                lastPartFound = i
                                self.ds.free(curIndex)
                            else:
                                lastPartFound = -1
                                self.ds.free(curIndex)                        
                                break
                else:
                    lastPartFound = 0
                if lastPartFound != -1:
                    curIndex, cur = self.ds.read("SELECT Size FROM Files where FileName = %s and DirectoryId = %s",(fileNameParts[maxDirParts],parentId))
                    row = cur.fetchone()
                    if (row != None):
                        fileLength =  row[0]
                        self.attrFileLength  =  fileLength
                        self.attrFileName = newFileName
                        self.attrParentId = parentId
                        self.attrDir = tempDir
                    self.ds.free(curIndex)

        except:
            fileLength = 0
            self.log.logIt(1,('%s|%s|%s|%s' % ("class VirtualDrive", "def checkAttrOnTape", "program error",str(sys.exc_info()[1]))))
        return fileLength


    def __cleanFileName(self, fileName):
        " remove / from file name "
        newFileName = fileName
        if len(fileName) > 0:
            if fileName.startswith("\\") or  fileName.startswith("/"):
                newFileName = fileName[1:]
        return newFileName                       

    def moveFromTape(self, tapeRootPath, newFile):
        " on file open move file from tape to cache "
        moveCompleted = True
        fileQueued = False
        direction = 1
        try:
            fileName = self.__cleanFileName(newFile)
            if tapeRootPath.find("tmsemptycache") == -1:
                shutil.copy2(os.path.join(tapeRootPath,fileName), os.path.join(self.mRootPath,fileName))
                # add entry in clear queue
                copyDelayHours = float(self.mInfo["CopyBackRemoveDelay"])
                curIndex, cur = self.ds.read("SELECT FullFileName FROM ClearDiskQueue where FullFileName = %s",(fileName,))
                row = cur.fetchone()
                fileQueued = (row != None)
                self.ds.free(curIndex)
                dateQueued = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                dateToRemove = (dt.datetime.now() + dt.timedelta(hours=copyDelayHours)).strftime('%Y-%m-%d %H:%M:%S')
                if fileQueued:
                    self.ds.write("UPDATE ClearDiskQueue SET DateQueued = %s, DateToRemove = %s, InProcess = 0, ClearWarning = 0 where FullFilename = %s",(dateQueued ,dateToRemove, fileName))
                else:
                    self.ds.write("INSERT INTO ClearDiskQueue (FullFileName, DateQueued, DateToRemove, InProcess, ClearWarning) VALUES (%s, %s,%s, 0,0)",(fileName,dateQueued,dateToRemove))   
                self.ds.write("INSERT INTO FileMoveLog (EntryDate, Direction, Source, Destination, FileName) VALUES (%s, 1, %s, %s, %s)",(dateQueued, tapeRootPath, self.mRootPath, fileName))              
                self.log.logIt(0,('%s|%s|%s' % ("class VirtualDrive", "def moveFromTape",  newFile + " added ClearDiskQueue")))
                self.log.logIt(0,('%s|%s' % ("Tape -> Disk", os.path.join(self.mRootPath,fileName))))
        except:
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def moveFromTape", "error",str(sys.exc_info()[1]))))

        return moveCompleted

    def __disassembleFileName(self, newFile):
        fileName = newFile.replace("\\", "/")
        return fileName.split('/')


    def itemOnTape(self, newFileName):
        " search for directory, if exist on tape ensure built out on cache, if file on tape make root point to tape. "

        rootPath = self.mRootPath
        parentId = 0
        lastPartFound = -1
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName))
        maxDirParts = len(fileNameParts) - 1

        try:
            if len(fileNameParts) > 1:
                for i in range(maxDirParts): # cycle through directory parts to find file
                    curIndex, cur = self.ds.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i],parentId))
                    row = cur.fetchone()
                    if row != None:
                        parentId = row[0]
                        lastPartFound = i
                        self.ds.free(curIndex)
                    else:
                        lastPartFound = -1
                        self.ds.free(curIndex)
                        break                  
            else:
                lastPartFound = 0

            if lastPartFound != -1:
                curIndex, cur = self.ds.read("SELECT FileId FROM Files where FileName = %s and DirectoryId = %s",(fileNameParts[len(fileNameParts) - 1],parentId))
                row = cur.fetchone()
                if row != None:
                    fileId = row[0]
                    keepLooping = True
                    self.ds.free(curIndex)
                    curIndex, cur = self.ds.read("SELECT TapeFiles.TapeUID FROM TapeFiles INNER JOIN LTOTapes ON TapeFiles.TapeUID = LTOTapes.TapeUID WHERE (TapeFiles.FileId = %s) AND (LTOTapes.InLibrary = 1) ORDER BY LTOTapes.DupSequence",(fileId,))
                    for row in cur:
                         tempRootPath = os.path.join(self.mInfo["TapeDrive"], self.__cleanFileName(str(row[0])))
                         if os.path.isdir("/" + tempRootPath):
                            rootPath = tempRootPath
                            keepLooping = False
                            break
                    self.ds.free(curIndex)
                    if keepLooping:
                        rootPath = os.path.join(self.mInfo["TapeDrive"], "tmsemptycache")
                else:
                    self.ds.free(curIndex)
        except:
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def itemOnTape", "error",str(sys.exc_info()[1]))))
        return rootPath

    def actualRootPath(self, dirFile):
        " return full directory name of file to use "
        newRootPath = self.mRootPath
        if dirFile != "/":
            tempStructure = os.path.join(self.mRootPath, self.__cleanFileName(dirFile))
            if os.path.isfile(tempStructure): # check for file or stub
                if os.path.getsize(tempStructure) == 0: # if stub lookup actual path
                    if self.fileList.inList(dirFile):  # check for previous look up to avoid DB look up (efficiency)
                        newRootPath = self.fileList.newRoot(dirFile)
                        if not os.path.isdir("/" + newRootPath):
                            newRootPath = self.itemOnTape(dirFile)
                            if newRootPath.find("tmsemptycache") == -1 and newRootPath != self.mRootPath:
                                self.fileList.addFile(dirFile, newRootPath)
                    else:
                        newRootPath = self.itemOnTape(dirFile) # first look up, search database
                        if (newRootPath.find("tmsemptycache") == -1 and newRootPath != self.mRootPath):
                            self.fileList.addFile(dirFile, newRootPath) # add file name to quick look up list.
        return newRootPath

    def __addDupFailure(self, fileName, newFileName, action, errMsg):
        " record to dup failure table "
 
        try:
            self.ds.write("INSERT INTO DupFailures (FileName, EntryDate, Action, NewFileName, ErrMsg) VALUES (%s, %s, %s, %s, %s)",(fileName,dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),action,newFileName,errMsg))
        except:
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def __addDupFailure", "error", str(sys.exc_info()[1]))))

    def __dupDriveExists(self, fileName, newfileName, action):
        " checks if program should write to duplicate drive and whether the drive actual exists (Q/A)"
        foundDrive = False
        if self.dupDrive:
            try:
                if os.path.isdir("/" + self.dPath):
                    foundDrive = True
                    self.dupWarning = False
                else:
                    if not self.dupWarning:
                        errMsg = "Duplication drive location not found"
                        self.log.logIt(2,('%s|%s|%s' % ("class VirtualDrive", "def __dupDriveExists", errMsg)))
                        self.dupWarning = True
                        self.__addDupFailure(fileName, newfileName, action, errMsg)
            except:
                if not self.dupWarning:
                    self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def __dupDriveExists", "error", str(sys.exc_info()[1]))))
                    self.dupWarning = True
                    self.__addDupFailure(fileName, "", action, str(sys.exc_info()[1]))
        return foundDrive

    def dupFileCreate(self, newFileName):
        " duplicate file to alternate drive "
        if self.__dupDriveExists(newFileName, "", "create"):
            try:
                cleanFileName = self.__cleanFileName(newFileName)
                tempStruct = os.path.join(self.mRootPath, cleanFileName)
                if os.path.isdir("/" + tempStruct):
                    tempDirName = os.path.join(self.dPath, cleanFileName)
                    if not os.path.exists(tempDirName):
                         os.makedirs(tempDirName)
                else:
                    if os.path.isfile(tempStruct):
                        fileNameParts = self.__disassembleFileName(cleanFileName)
                        if len(fileNameParts) > 1:
                            tempDir = os.path.join(self.dPath, self.__cleanFileName(newFileName.replace("/" + fileNameParts[len(fileNameParts) - 1], "")))
                            if not os.path.exists(tempDir):
                                os.makedirs(tempDir)
                        shutil.copy2(os.path.join(self.mRootPath, cleanFileName),os.path.join(self.dPath,cleanFileName))
            except:
                self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def dupFileCreate", "error", str(sys.exc_info()[1]))))
                self.__addDupFailure(newFileName, "", "create", str(err))
        else:
            if self.dupDrive:
                self.__addDupFailure(newFileName, "", "create", "Duplication drive location not found")

    def dupFileDelete(self, newFileName):
        " delete file or folder on alternate drive "
        cleanFileName = self.__cleanFileName(newFileName)
        if self.__dupDriveExists(newFileName, "", "delete"):
            try:
                tempDir = os.path.join(self.dPath,cleanFileName)
                if os.path.isdir("/" + os.path.join(self.mRootPath, cleanFileName)):
                    if os.path.isdir("/" + tempDir):
                        os.rmdir(tempDir)
                else:
                    if os.path.isfile(tempDir):
                        os.remove(tempDir)
            except:
                self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def dupFileDelete", "error", str(sys.exc_info()[1]))))
                self.__addDupFailure(newFileName, "", "delete", sr(err))
        else:
            if self.dupDrive:
                self.__addDupFailure(newFileName, "", "delete", "Duplication drive location not found")

    def dupFileRename(self, currentFile, newfile):
        " rename a directory "
        if self.__dupDriveExists(currentFile, newfile, "rename"):
            try:
                tempStruct1 = os.path.join(self.dPath, self.__cleanFileName(currentFile))
                tempStruct2 = os.path.join(self.dPath, self.__cleanFileName(newfile))
                if os.path.isdir("/" + tempStruct1):
                    if not os.path.exists(tempStruct2):
                        os.rename(tempStruct1,tempStruct2)
                else:
                    if os.path.isfile(tempStruct1):
                        if not os.path.isfile(tempStruct2):
                            os.rename(tempStruct1,tempStruct2)
            except:
                self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def dupFileRename", "error", str(sys.exc_info()[1]))))
                self.__addDupFailure(currentFile, newfile, "rename", str(sys.exc_info()[1]))
        else:
            if self.dupDrive:
                self.__addDupFailure(currentFile, newfile, "rename", "Duplication drive location not found")

    def checkItemOnTape(self, newFileName):
        " search for directory, if exist on tape ensure built out on cache, if file on tape make root point to tape. (Q/A)"
        
        onTape = False
        parentId = 0
        lastPartFound = -1
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName))
        maxDirParts = len(fileNameParts) - 1

        try:
            if len(fileNameParts) > 1:
                for i in range(maxDirParts): # cycle through directory parts to find file
                    curIndex, cur = self.ds.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i],parentId))
                    row = cur.fetchone()
                    if row != None:
                        parentId = row[0]
                        lastPartFound = i
                        self.ds.free(curIndex)
                    else:
                        lastPartFound = -1
                        self.ds.free(curIndex)
                        break
            else:
                lastPartFound = 0

            if lastPartFound != -1:
                curIndex, cur = self.ds.read("SELECT FileId FROM Files where FileName = %s and DirectoryId = %s",(fileNameParts[len(fileNameParts) - 1],parentId))
                row = cur.fetchone()
                onTape = (row != None)
                self.ds.free(curIndex)
        except:
            onTape = True
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def checkItemOnTape", "error", str(sys.exc_info()[1]))))
        return onTape

    def removeDiskQueue(self, newFile):
        "  log move to tape "

        fileName = self.__cleanFileName(newFile)
        fileQueued = False

        try:
            curIndex, cur = self.ds.read("SELECT FullFileName FROM RemoveDiskQueue where FullFileName = %s",(fileName,))
            row = cur.fetchone()
            fileQueued = (row != None)
            self.ds.free(curIndex)
            dateNow =dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if fileQueued:
                self.ds.write("UPDATE RemoveDiskQueue SET DateQueued =%s, DateToRemove = %s, InProcess = 0, NoTapeWarning  = 0 where FullFilename = %s",(dateNow,dateNow,fileName))
            else:
                self.ds.write("INSERT INTO RemoveDiskQueue (FullFileName, DateQueued, DateToRemove, InProcess,NoTapeWarning) VALUES (%s,%s,%s, 0,0)",(fileName,dateNow,dateNow))
            self.ds.write("DELETE FROM ClearDiskQueue WHERE FullFileName = %s",(fileName,))
            self.log.logIt(0,('%s|%s|%s' % ("class VirtualDrive", "def removeDiskQueue",  newFile + " added to RemoveDiskQueue")))
        except:
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def removeDiskQueue", "error", str(sys.exc_info()[1]))))


    def toTapeQueue(self, newFile):
        " log move to tape "
        try:
            fileName = self.__cleanFileName(newFile)
            tempfile = os.path.join(self.mRootPath, fileName)
            if os.path.isfile(tempfile):
                fileLength = os.path.getsize(tempfile)               
                if fileLength > 0:
                    if self.checkItemOnTape(newFile):
                        self.removeDiskQueue(newFile)
                    fileQueued = False
                    copyDelayHours = float(self.mInfo["WriteDelayHours"])
                    curIndex, cur = self.ds.read("SELECT FullFileName FROM ToTapeQueue where FullFileName = %s",(fileName,))
                    row = cur.fetchone()
                    fileQueued = (row != None)
                    self.ds.free(curIndex)
                    dateQueued = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if copyDelayHours < 1.0:
                        dateToCopy = (dt.datetime.now() + dt.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        dateToCopy = (dt.datetime.now() + dt.timedelta(hours=copyDelayHours)).strftime('%Y-%m-%d %H:%M:%S')
                    if fileQueued:
                        self.ds.write("UPDATE ToTapeQueue SET DateQueued = %s, DateToCopy = %s, InProcess = 0, CopyCount = 0 where FullFilename = %s",(dateQueued,dateToCopy,fileName))
                    else:
                        self.ds.write("INSERT INTO ToTapeQueue (FullFileName, DateQueued, DateToCopy, Priority, InProcess, NoTapeWarning,CopyCount) VALUES ( %s, %s, %s, 0, 0, 0,0)",(fileName,dateQueued,dateToCopy))
                    self.log.logIt(0,('%s|%s|%s' % ("class VirtualDrive", "def toTapeQueue",  newFile + " added to ToTapeQueue")))

                    return newFile, dt.datetime.now() + dt.timedelta(hours=copyDelayHours) - dt.timedelta(minutes=float(self.mInfo["FileManagerInterval"]))
        except:
             self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def toTapeQueue", "error", str(sys.exc_info()[1]))))

    def fileBeingTranfered(self, newFile):
        " check if file is being processed by transfer to tape task "
        fileName = self.__cleanFileName(newFile)
        processing = False

        try:
            curIndex, cur = self.ds.read("SELECT FullFileName FROM ToTapeQueue where FullFileName = %s AND InProcess = 1",(fileName,))
            row = cur.fetchone()
            processing = (row != None)
            self.ds.free(curIndex)
        except:
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def fileBeingTranfered", "error", str(sys.exc_info()[1]))))
        return processing

    def removeFromToTapeQueue(self, newFile):
        " remove entry from ToTapeQueue "
        try:
            self.ds.write("DELETE FROM ToTapeQueue WHERE FullFileName = %s",(self.__cleanFileName(newFile),))
        except:
            self.log.logIt(2,('%s|%s|%s|%s' % ("class VirtualDrive", "def removeFromToTapeQueue", "error", str(sys.exc_info()[1]))))

    def checkCacheSpace(self):
        " checks amount of free space is cache "
        s = os.statvfs(self.mInfo["CacheLocation"])
        availableFreeSpace = (s.f_bavail * s.f_frsize) / (1024 * 1024 * 1024)
        if int(self.mInfo["MinCacheGB"]) >= availableFreeSpace:
            if not self.minCacheMsgSent and self.mInfo["NotifyOnLowCache"] == "yes":
                msg =  "Current available space is " + availableFreeSpace + "GB, minimun space warning set at " + self.mInfo["MinCacheGB"] + "GB."
                self.log.logIt(2,('%s|%s|%s' % ("class VirtualDrive", "def checkCacheSpace",  msg)))
                self.minCacheMsgSent = True
        else:
            self.minCacheMsgSent = False

#   --------------------------------------------

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.basePath, partial)
        return path

    def access(self, path, mode):
 #       print '*** access', path
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            self.log.logIt(0,"FUSE method access on " + path + " permission denied")            
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        # print '*** chmod', path
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        # print '*** chown', path
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
#        print "*** getattr *** ", path
        tempFullName = self._full_path(path)
        ht = os.lstat(tempFullName)
        st = dict((key, getattr(ht, key)) for key in ('st_atime', 'st_ctime', 'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
        if tempFileCheck(path) and os.path.isfile(tempFullName) and ht.st_size == 0:
           st["st_size"] = self.checkAttrOnTape(path)
#           print "*** getattr on tape *** ", path, st["st_size"]
        return st   

    def readdir(self, path, fh):
 #       print "*** readdir *** ", self.basePath + path
        full_path = self._full_path(path)
        dirents = ['.', '..']
        if os.path.isdir("/" + full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        # print '*** readlink', path
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        # print '*** mknod', path        
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir ( self, path ):
        # print '*** rmdir', path
        try:
            osHandle = os.rmdir(self._full_path(path))
            self.fileList.deleteFile(path)
            self.dupFileDelete(path)
            return osHandle
        except:
            print (str(sys.exc_info()[1]))
            self.log.logIt(0,"FUSE method rmdir on " + path + " " + str(sys.exc_info()[1]))            
            raise FuseOSError(errno.EPERM)

    def mkdir(self, path, mode):
        # print "**** mkdir", path
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
#        print '*** statfs', path
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))
    
    def checkItemOnTapeFast(self,path):
        onTape = False
        if self.lastPath != path or self.lastPathTime < dt.datetime.now():
            onTape = self.checkItemOnTape(path)
        return onTape


    def canUnlink(self, path):
        canBeDeleted = True
        if path.find("/.") == -1 and path.find("~") == -1:  
            if self.fileBeingTranfered(path) or (self.mInfo["AllowTapeDelete"] == "no" and self.checkItemOnTapeFast(path)):
                canBeDeleted = False;
        return canBeDeleted

    def unlink ( self, path ):
        # print '*** unlink', path
        if self.canUnlink(path):
            if tempFileCheck(path):
                if self.checkItemOnTapeFast(path):
                    self.removeDiskQueue(path)
                else:
                    self.removeFromToTapeQueue(path);
                self.dupFileDelete(path);
            return os.unlink(self._full_path(path))
        else:
            self.log.logIt(0,"FUSE method unlink on " + path + " not permitted")            
            raise FuseOSError(errno.EPERM)


    def symlink(self, target, name):
#        print '*** symlink', target, name
        return os.symlink(self._full_path(target), self._full_path(name))

    def rename ( self, oldPath, newPath  ):
        # print '*** rename', oldPath, newPath
        rename = False
        renameHandle = 0
        tempFileNameOld = self._full_path(oldPath)
        tempFileNameNew = self._full_path(newPath)
        if os.path.isfile(tempFileNameOld) and not os.path.isfile(tempFileNameNew):
            if not self.checkItemOnTapeFast(oldPath) and not self.checkItemOnTape(newPath):
                renameHandle = os.rename(tempFileNameOld ,tempFileNameNew)
                if tempFileCheck(oldPath):
                    self.removeFromToTapeQueue(oldPath)
                    if tempFileCheck(newPath):
                        self.dupFileRename(oldPath, newPath)
                        self.toTapeQueue(newPath)
                rename = True
        else:
            if os.path.isdir("/" + tempFileNameOld) and not os.path.isdir("/" + tempFileNameNew) and  len(os.listdir(tempFileNameOld)) == 0:
                renameHandle = os.rename(tempFileNameOld ,tempFileNameNew)
                rename = True
        if not rename:
                self.log.logIt(0,"FUSE method rename on " + oldPath + " not permitted")            
                raise FuseOSError(errno.EPERM)
        else:
            return renameHandle


    def link(self, target, name):
        # print '*** link', target, name
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
 #       print '*** utimens', path
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open ( self, path, flags ):
        tempFullName = self._full_path(path)
        # while self.fileMo.has_key(tempFullName):
        while tempFullName in self.fileMo:             
            time.sleep(0.001)
        self.fileMo[tempFullName] = 1
        # print '*** open', path, flags
        errorConditions = ["file locked by another application!", "unable to move file from tape!", "file does not exist!","unable to open file"]
        currentCondition = -1
        if os.path.isfile(tempFullName) == False: # check if file exists as a stub or actual file
                currentCondition = 2
               #  if self.fileMo.has_key(tempFullName):
                if tempFullName in self.fileMo:                    
                    del self.fileMo[tempFullName] 
        else:
            try:
                cRootPath = self.actualRootPath(path)
 #               print "*** paths", cRootPath, self.basePath
                if cRootPath != self.basePath:
                    if self.moveFromTape(cRootPath, path) == False: # check if file can be moved from tape to cache
                            currentCondition = 1
                # if self.fileMo.has_key(tempFullName):
                if tempFullName in self.fileMo:                    
                    del self.fileMo[tempFullName] 
            except:
               # if self.fileMo.has_key(tempFullName):
                if tempFullName in self.fileMo:                    
                    del self.fileMo[tempFullName] 
        if currentCondition != -1:
            self.log.logIt(0,"FUSE method open on " + path + " " + errorConditions[currentCondition])            
            raise FuseOSError(errno.EPERM)
        else:
            return os.open(tempFullName, flags)


    def create(self, path, mode, fi=None):
        # print '*** create', path ,mode 
        errorConditions = ["file open with same name!", "file already exists!","unable to create file","unable to create file!"]
        currentCondition = -1
        tempFullName = self._full_path(path)
        if os.path.isfile(tempFullName) == True: # check if file exists as a stub or actual file
            currentCondition = 1
        if currentCondition != -1:
            self.log.logIt(0,"FUSE method create on " + path + " " + errorConditions[currentCondition])            
            raise FuseOSError(errno.EPERM)
        else:
            try:
                return os.open(tempFullName, os.O_WRONLY | os.O_CREAT, mode) 
            except:
                self.log.logIt(1,"FUSE method create on " + path + " " + str(sys.exc_info()[1]))            
                raise FuseOSError(errno.EPERM)


    def read(self, path, length, offset, fh):
#        print '*** read', path, length, offset
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
 #       print '*** write', path, self.checkItemOnTape(path)
        # if not self.fileOp.has_key(fh):

        if fh not in self.fileOp:            
            if self.checkItemOnTapeFast(path):
                self.log.logIt(0,"FUSE method write on " + path + " not permitted")            
                raise FuseOSError(errno.EPERM)
            else:
                if tempFileCheck(path):
                    self.fileOp[fh] = 'w'
                else:
                    self.fileOp[fh] = 't'
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        # print '*** truncate', path, self.checkItemOnTapeFast(path)
        if self.checkItemOnTapeFast(path):
            self.log.logIt(0,"FUSE method truncate on " + path + " not permitted")            
            raise FuseOSError(errno.EPERM)
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
#        print '*** flush', path
        return os.fsync(fh)

    def release(self, path, fh):
        # print '*** release', path
        fileOp = ""
        # if self.fileOp.has_key(fh):
        if fh in self.fileOp:            
            fileOp = self.fileOp[fh]
            del self.fileOp[fh]
        closeHandle = os.close(fh)
        if fileOp == "w":
            self.lastPath, self.lastPathTime = self.toTapeQueue(path)
            self.dupFileCreate(path)        
        return closeHandle


    def fsync(self, path, fdatasync, fh):
#        print '*** fsync', path
        return self.flush(path, fh)

def alive(tasks):
    dict = {'error': 0, 'errormsg': ''}
    linecount = 0
    try:
        lines = os.popen('ps aux').readlines()
        for task in tasks:
            dict[task] = [0,'Down','&nbsp;']
            for line in lines:
                if line.find("python " + task + ".py") >= 0:
                    print(line)
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

def validateConfig():
    dict = {"error": 0, "errormsg": ""}
    if os.path.isfile("EchoLeaf.config"):
        configInfo = DriveProperties().getInfoAll()
        if configInfo["error"] == 0:
            if os.path.exists(configInfo["VDiskMountPoint"]):
                if os.path.exists(configInfo["CacheLocation"]):
                    if os.path.exists(configInfo["TapeDrive"]):
                        if sum(1 for item in os.listdir(configInfo["VDiskMountPoint"])) > 0:
                            dict["error"] = 5
                            dict["errormsg"] = "Virtual drive mount point contains files or folder."
                    else:
                        dict["error"] = 4
                        dict["errormsg"] = "LTFS Library Location " + configInfo["TapeDrive"] + " does not exist."
                else:
                    dict["error"] = 3
                    dict["errormsg"] = "Cache Location " + configInfo["CacheLocation"] + " does not exist."
            else:
                dict["error"] = 2
                dict["errormsg"] = "Virtual disk mount point " + configInfo["VDiskMountPoint"] + " does not exist."
        else:
            dict["error"] = configInfo["error"] 
            dict["errormsg"] = configInfo["errormsg"]
    else:
        dict["error"] = 1 
        dict["errormsg"] = "Echoleaf configuration file does not exist."
    if dict["error"] == 0:
        return configInfo
    else:
        return dict
        
"""
Now deprecated.  In common module

def decryptIt(strEncoded):
	BLOCK_SIZE = 16
	PADDING = '{'
	pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
	DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
	key = "53f7d42cbf4d485b781f818fb9e1cd11"
	cipher = AES.new(unhexlify(key))
	return DecodeAES(cipher, strEncoded)
"""

def main():   
    configInfo = validateConfig()
    if configInfo["error"] == 0:
        fuse.FUSE(VirtualDrive(configInfo),  configInfo["VDiskMountPoint"], foreground=True, allow_other=True, nothreads=True)
    else:
	    print("oh mama") 
		
# print(configInfo["errormsg"])

if __name__ == '__main__':
    main()
