#     15 Nov 2024 -- updated to ELSentry v2.0a beta
#      FM Timer Project 10 Dec 2024
"""
Application: filemanager.py
Version 1.5c3 # Added Retry on Bad File, Fixed Bad Copy Process Bug
Version 1.5c2 # Added Phone Home (North Belmore) July 2020
Version 1.5c1 # Added Backup Exec Screens April 2020
Version: 1.0    For version 1.3a
Release Date: 01 Dec 2016
Description:  Manages the transfer of files from disk to tape.  Enabling and disabling occurs through administrative program.

Change History:
 May 1, 2018  Fix restore function.  Path was being doubled.  Old code preserved in comments
 July 2019  Fix LTFSAdmintool functions and LTFS Identification
 July 20, 2019 Add function in Class TapeManagement to determine LTOType from Barcode
 
Copyright EchoLeaf 2016 / 2018 / 2020
EchoLeaf Version 1.4c / 1.4d updated process queue for Tape Management

EchoLeaf Version 1.5 / Added Archive Mode for db / cache / software.  Added METADATA_WRITABLE options
"""
#  P2p3 Testing
import os, sys, time, smtplib, shutil, json
# import common
import datetime as dt

import threading  # Add this import

import common

from common import resetFMTimer # Import FMInterrupt

import tempfile

from common import load_key, decryptIT
import mysql.connector as mdb
# import MySQLdb as mdb
import shutil
# from Crypto.Cipher import AES
from cryptography.fernet import Fernet

from binascii import hexlify, unhexlify
import base64
import smtplib
import fcntl
import logging
#  Testing Archive routines for 1.5
from datetime import date
# import ELArchive02
#  Testing Archive routines
from queue import Queue
# Phone Home Routines
from PhoneHomeMaster import phoneHome, sendPhoneHomeMail
# Edit Phone Home functions from above modules

timer = None  # Declare timer outside the main() function

class DataStore:
    """  manages a single open connection """ 

    def __init__(self, info):
        self.info = info
        self.conn_status = []
        self.conn_pool = []
        self.cur_pool = []

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
                            print(f"*** Error connecting after trying to create cursor: {e}")
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


    def connect_reset(self, cursor):
        """
        Resets a connection and its cursor.
        """
        print(f"Resetting cursor {cursor}")
        try:
            if cursor < len(self.conn_pool):
                conn = self.conn_pool[cursor]  # Get the connection object
                if conn.is_connected():
                    try:
                        self.cur_pool[cursor].close()  # Close the cursor first
                    except Exception as e:
                        print(f"Error closing cursor: {e}")
                    try:
                        conn.close()  # Close the connection
                    except Exception as e:
                        print(f"Error closing connection: {e}")
                
                # Create a new connection and cursor
                conn = mdb.connect(  # Assign to 'conn'
                    host=self.info["host"],
                    user=self.info["user"],
                    password=self.info["password"],
                    database=self.info["database"]
                )
                self.conn_pool[cursor] = conn
                self.conn_pool[cursor].autocommit = True
                self.cur_pool[cursor] = self.conn_pool[cursor].cursor()
            else:
                print(f"Invalid cursor index in connect_reset: {cursor}")
        except Exception as e:
            print(f"Error resetting connection {cursor}: {e}")


    def disconnect(self):
        """
        Closes all connections in the pool.
        """
        for index, conn in enumerate(self.conn_pool):  # Using 'conn'
            try:
                if conn.is_connected():
                    conn.close()
            except Exception as e:
                print(f"Error closing connection {index}: {e}")


    def free(self, cursor):
        """
        Releases a connection back to the pool.
        """
        try:
            if 0 <= cursor < len(self.cur_pool):
                conn = self.conn_pool[cursor]  # Assign to 'conn'
                if conn.is_connected():
                    self.cur_pool[cursor].close()
                    self.conn_status[cursor] = True
                else:
                    print(f"Connection {cursor} is already closed.")
            else:
                print(f"Invalid cursor index: {cursor}")
        except Exception as e:
            print(f"Error freeing cursor {cursor}: {e}")


    def write(self, query, values=''):
        """
        Executes a write query (INSERT, UPDATE, DELETE).
        """
        try:
            cursor_index = self.connect()
            if cursor_index is None:
                raise ConnectionError("Failed to get a database connection for write.")

            cursor = self.cur_pool[cursor_index]
            conn = self.conn_pool[cursor_index]  # Assign to 'conn'

            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)
            conn.commit()  # Using 'conn'

        except Exception as e:
            print(f"Error during write operation: {e}")
            # You might want to handle the error more specifically (e.g., retry)

        finally:
            if cursor_index is not None:
                self.free(cursor_index)


    def read(self, query, values=''):
        """
        Executes a read query (SELECT) and returns the cursor and result.
        """
        try:
            cursor_index = self.connect()
            if cursor_index is None:
                raise ConnectionError("Failed to get a database connection for read.")

            cursor = self.cur_pool[cursor_index]
            if values:
                cursor.execute(query, values)
            else:
                cursor.execute(query)
            return cursor_index, cursor  # Return cursor_index for proper freeing

        except Exception as e:
            print(f"Error during read operation: {e}")
            return None, None  # Indicate failure






class ClearDisKQueue:

    def __init__(self, currentConn, currentLog, currentConfig):
        self.conn = currentConn
        self.log = currentLog
        self.config = currentConfig

    def __zeroFileSize(self, fileName):
        " create file stub of 0 bytes bases on file name "
        zeroed = True
        try:
            fs = open(fileName, 'w+')
            fs.close()  
        except:
            self.log.logIt(1, "ClearDisKQueue Unable to stub cache file " + fileName + ": " + str(sys.exc_info()[1]))
            zeroed = False
        return zeroed

    def processQueue(self):
        fileList = []
        clearWarning = []
        cacheLocation = self.config["CacheLocation"]
        targetFile = ''

        curIndex, cur = self.conn.read("SELECT FullFileName, ClearWarning FROM ClearDiskQueue  WHERE DateToRemove <= %s AND ClearWarning = 0 Order BY DateToRemove ASC",(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
        for row in cur:
            fileList.append(str(row[0]))
            clearWarning.append(row[1])
        self.conn.free(curIndex)

        # move through list and delete files from tape
        for cFile in fileList:
            targetFile = os.path.join(cacheLocation, cFile)
            if os.path.isfile(targetFile):
                if self.__zeroFileSize(targetFile):
                    self.__removeFromQueue(cFile)
                else:
                    self.__updateClearWarning(cFile)
            else:
                self.__removeFromQueue(cFile)

    def __removeFromQueue(self, partialFileName):
        try:
            self.conn.write("DELETE FROM ClearDiskQueue WHERE FullFileName = %s",(partialFileName,))
        except:
            self.log.logIt(1, "class ClearDisKQueue function removeFromQueue program error: "+ str(sys.exc_info()[1]))

    def __updateClearWarning(self, fileNane):
        " change value of ClearWarning on tape to avoid repeated messages going to administrator "
        try:
            self.conn.write("UPDATE ClearDiskQueue SET ClearWarning = 1 WHERE FullFileName = %s",(fileNane,))
        except:
            self.log.logIt(1, "class ClearDisKQueue function updateTapeWarning program error: "+ str(sys.exc_info()[1]))

class ToTapeQueue:

    def __init__(self, currentConn, currentLog, currentConfig):
        self.conn = currentConn
        self.log = currentLog
        self.config = currentConfig
        self.tapeManager = TapeManagement(self.conn, self.config["TapeDrive"], self.log)
        self.listOfTapes = TapeList(self.conn)
        self.tapeUID = "NA"
        self.tapeDupSeq = 0
        self.allowCopy = True
        self.ftool = FileTools(self.conn, self.log)
        self.lastfileMoved = ""
        self.toTapeLog = True # if self.config["ToTapeLog"] == "yes" else False

     
    def __removeFromQueue(self, partialFileName):
        " remove from queue "
        try:
            self.conn.write("DELETE FROM ToTapeQueue WHERE FullFileName = %s",(partialFileName,))
        except:
            self.log.logIt(1, "class ToTapeQueue function removeFromQueue program error: "+ str(sys.exc_info()[1]))

    def __setInProcess(self, partialFileName):
        " set that file is being processed to tape "
        try:
            self.conn.write("UPDATE ToTapeQueue SET InProcess = 1 WHERE FullFileName = %s",(partialFileName,))
        except:
            self.log.logIt(1, "class ToTapeQueue function setInProcess program error: "+ str(sys.exc_info()[1]))

    def __updateEntryIssue(self, partialFileName, issue):
        " update queue priority and issue "
        try:
            self.conn.write("UPDATE ToTapeQueue SET Priority = -1, Issue = %s WHERE FullFileName = %s",(issue, partialFileName))
        except:
            self.log.logIt(1, "class ToTapeQueue function updateEntryIssue program error: "+ str(sys.exc_info()[1]))

    def __zeroFileSize(self, partialFileName):
        " create file stub of 0 bytes bases on file name "
        try:
            fs = open(os.path.join(self.config["CacheLocation"], partialFileName), 'w+')
            fs.close()
        except:
            self.log.logIt(1, "Unable to stub cache file " + partialFileName + ": " + str(sys.exc_info()[1]))

    def __updateCopyCount(self, partialFileName, tapeCopies):
        " update copy count, if count equals number of items in queue "
        copyCount = 0
        fullFileName = ""
        validDirBuild = False
        fileAdded = False

        try:
            self.conn.write("UPDATE ToTapeQueue SET CopyCount = CopyCount + 1 WHERE FullFileName =%s",(partialFileName,))
            curIndex, cur = self.conn.read("SELECT CopyCount FROM ToTapeQueue WHERE FullFileName = %s",(partialFileName,))
            row = cur.fetchone()
            if row != None:
                copyCount = row[0]
            self.conn.free(curIndex)
            if partialFileName != self.lastfileMoved:
                fullFileName = os.path.join(self.config["CacheLocation"], partialFileName)
          
                if not self.ftool.sameAsLastDir(partialFileName):
                    validDirBuild = self.ftool.buildDBDirectory(partialFileName)
                smallFileName = self.ftool.shortFileName(partialFileName)

                if smallFileName != "":
                    if not self.ftool.fileRegistered(smallFileName):
                        fileAdded = self.ftool.addFileToDB(smallFileName, fullFileName)

            self.ftool.addToTapeFiles(self.tapeUID, copyCount - 1)

            if copyCount == tapeCopies:
                self.__zeroFileSize(partialFileName)
                self.__removeFromQueue(partialFileName)
        except:
            self.log.logIt(1, "class ToTapeQueue function updateCopyCount program error: "+ str(sys.exc_info()[1]))
        self.lastfileMoved = partialFileName

    def __getFileList(self, dupSequence):
        " get list in to tape queue "
        fullFileList = []
        finalFileList = []
        listOfTapes = []
        fileTapes = TapeList(self.conn)
        fullFileName = ""

        fileLengthnum = 0

        issue = ""
        cache = self.config["CacheLocation"]

        maxFileSize = int(self.config["MaxFileSizeGB"]) * 1073741824 

        self.log.logIt(1, "--- Entering __getFileList ---")  # Log entry point

        try:
            # Get the current time from the database without microseconds
            self.log.logIt(1, "Getting current time from database...")
            curIndex, cur = self.conn.read("SELECT NOW()")
            current_time_str = cur.fetchone()[0].strftime('%Y-%m-%d %H:%M:%S')
            self.conn.free(curIndex)
            self.log.logIt(1, f"Database server time: {current_time_str}")

            # get raw file list 
            # 15c3 changed Select below to include Priority >= -1 (was >=0) to cover bad copy retries
            # Execute the query, comparing DateToCopy with the current time from the database
            self.log.logIt(1, f"Querying with DateToCopy: {current_time_str}")
            query = ("SELECT FullFileName FROM ToTapeQueue "
                     "WHERE DateToCopy <= %s AND Priority >= -1 AND CopyCount = %s "
                     "ORDER BY Priority DESC, DateQueued ASC")
            self.log.logIt(1, f"Executing query: {query} with parameters: {(current_time_str, dupSequence)}")
            curIndex, cur = self.conn.read(query,(current_time_str, dupSequence))

            if cur:
                results = cur.fetchall()
                self.log.logIt(1, f"Query returned {len(results)} rows")
                for row in results:
                    fullFileName = str(row[0])
                    self.log.logIt(1, f"Found raw file: {fullFileName}")
                    fullFileList.append(fullFileName)
            else:
                self.log.logIt(1, "Query returned no rows")

            self.conn.free(curIndex)

            # go through validity checks
            for fileName in fullFileList:
                copyFile = True
                fullFileName = os.path.join(cache, fileName)
                lastFour = fileName[-4:] # Needed for Backup Exec file screen
                # print("Last Four = " + lastFour) # Diagnostics               

                if not os.path.isfile(fullFileName): # check if file is in cache, if not remove
                    self.__removeFromQueue(fileName)
                    self.log.logIt(1, fileName + " not found in cache")
                    copyFile = False

                # adding  validity check for small Backup Exex files = less than 10K. (Needed metadata)

                if copyFile: # check for small Backup Exec files
                    fileLength =os.path.getsize(fullFileName)
                    if (lastFour == ".bkf" and fileLength <= 10000) or (lastFour == ".lck" and fileLength <= 10000):
                        self.__removeFromQueue(fileName)
                        self.log.logIt(1, fileName + " No transfer. Small Backup Exec Metadata File.")
                        copyFile = False

                if copyFile: # check min and max file size for transfer
                    fileLength =os.path.getsize(fullFileName)
                    if fileLength == 0:
                        self.__removeFromQueue(fileName)
                        self.log.logIt(1, fileName + " not transfer, size of file is 0")
                        copyFile = False
                    else:
                        
                        filelengthnum = int(fileLength)
                        if fileLengthnum > maxFileSize:
                            issue = "file size greater than max size allowed"
                            self.__updateEntryIssue(fileName, issue)
                            self.log.logIt(1, fileName + " " + issue)
                            copyFile = False                                                  

                if copyFile: # check if file exists on one or more tapes
                    listOfTapes = fileTapes.createNewList(fileName)
                    if self.ftool.isFileDupOnTape(fileName, dupSequence):
                        issue = "full file name already exists on tape"
                        self.__updateEntryIssue(fileName, issue)
                        self.log.logIt(1, fileName + " " + issue)
                        copyFile = False

                if copyFile:
                    finalFileList.append(fileName)

        except Exception as e:
            self.log.logIt(1, f"Error in __getFileList: {e}")
        finally:
            self.log.logIt(1, "--- Exiting __getFileList ---")
        return finalFileList
        
        

        
        
        



    def __prepTape(self, fileName, dupSeq):
        " prep tape with correct directory structure "

        if self.tapeUID == "NA" or dupSeq != self.tapeDupSeq: # find an appropriate tape
            self.tapeUID = self.tapeManager.getActiveTape(dupSeq)
        
        for i in range(2):
            if self.tapeUID == "NA":    # unable to find tape, stop copying process
                self.log.logIt(1, "Unable to find tape for duplication sequence " + str(dupSeq))
                self.allowCopy = False
                return False

            if self.ftool.buildDirOnTape(fileName, self.tapeUID, self.config["TapeDrive"]):
                break
            else:
                if i == 0:
                    self.tapeManager.closeActiveTape()
                    self.tapeUID = self.tapeManager.getActiveTape(dupSeq)
                else:
                    self.log.logIt(1, "Unable to build directory structure on tape " + self.tapeUID + " for " + fileName)
                    self.allowCopy = False
                    return False
        self.tapeDupSeq = dupSeq
        return True

    def __copyFile(self, srcFile, destFile, baseFileName):
        " copy file return codes 0-no 1-yes 2-problem "

        fileCopied = 1
        try:
            shutil.copy2(srcFile, destFile)
            self.__toTapeLog(baseFileName, srcFile, destFile)
            self.log.logIt(0,('%s|%s' % ("Disk -> Tape", destFile)))
        except:
            if not "No space left on device" in str(sys.exc_info()[1]): # ********
                self.log.logIt(2, "File Copy Source: " + srcFile + " Destination: " + destFile + " "+ str(sys.exc_info()[1]))
                fileCopied = 2
                # 1.5c3 Above was fileCopied = 1. Created error. And forced a new tape on error.  Bad!! 
            else:
                self.log.logIt(0, "File Copy Source: " + srcFile + " Destination: " + destFile + " tape full switching tapes"+ str(sys.exc_info()[1]))
                fileCopied = 0
                self.__deleteCorruptedFile(destFile)
        return fileCopied

    
    
    def __toTapeLog(self,baseFileName, srcFile, destFile):
        " add file to toTape log "
        if self.toTapeLog:
            try:
                dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # Construct source relative to CacheLocation
                source_relative_path = os.path.relpath(srcFile, self.config["CacheLocation"])
                # Construct destination relative to tape drive
                destination_relative_path = os.path.relpath(destFile, self.config["TapeDrive"])


                self.conn.write("INSERT INTO FileMoveLog (EntryDate, Direction, Source, Destination, FileName) VALUES (%s, 0, %s, %s, %s)",
                                (dateStamp, source_relative_path, destination_relative_path, baseFileName)) # Corrected parameters

            except Exception as e: # Use a more general exception
                self.log.logIt(1, "Class ToTapeQueue function ToTapeLog program error: "+ str(e))
    
        
    
    
    def __deleteCorruptedFile(self, destinationFile):
        " delete corrupted file "
        try:
            if os.path.isfile(destinationFile):
               os.remove(destinationFile)
        except:
            self.log.logIt(1, "Unable to delete corrupted file: " + destinationFile + " from tape"+ str(sys.exc_info()[1]))

    def __copyFileToTape(self, fileName,dupSeq):
        " copy file to tape "
        fileCopied = 0
        srcFile = ""
        destFile = ""
        returnVals = [False, True, False]

        # first try
        if not self.__prepTape(fileName,dupSeq):
            return returnVals[fileCopied]

        srcFile = os.path.join(self.config["CacheLocation"],fileName) # define source and destination locations.
        destFile = os.path.join(os.path.join(self.config["TapeDrive"], self.tapeUID), fileName)
        fileCopied = self.__copyFile(srcFile, destFile, fileName)
        if fileCopied != 0:
            return returnVals[fileCopied]

        self.tapeManager.closeActiveTape()
        self.tapeUID = "NA"
        if not self.__prepTape(fileName,dupSeq):
            return returnVals[fileCopied]
        srcFile = os.path.join(self.config["CacheLocation"],fileName)
        destFile = os.path.join(os.path.join(self.config["TapeDrive"], self.tapeUID), fileName)
        fileCopied = self.__copyFile(srcFile,destFile,fileName)
        if fileCopied != 1:
            self.allowCopy = False
        return returnVals[fileCopied]


    def processQueue(self):
        " copy files from queue "
        filesToProcess = []
        tapeCopies = int(self.config["TapeCopies"])
        for i in range(tapeCopies):
            filesToProcess =  self.__getFileList(i)
            for item in filesToProcess:
                if self.allowCopy:
                    if i == 0:
                        self.__setInProcess(item)
                    if self.__copyFileToTape(item, i):
                        self.__updateCopyCount(item, tapeCopies)
                    else:
                            self.__updateEntryIssue(item, "copy to tape failed")

class FileTools:
    """ General file management tools """

    def __init__(self, currentConn, currentLog):
        self.conn = currentConn
        self.log = currentLog
        self.lastDirectory = ""
        self.lastFileId = 0
        self.lastEndFolderId = 0

    def __disassembleFileName(self,newFile):
        " pulls apart file name "
        return newFile.replace("\\", "/").split('/')

    
    def __cleanFileName(self,fileName):
        " remove / from file name "
        newFileName = fileName
        if len(fileName) > 0:
            if fileName.startswith("\\") or fileName.startswith("/"):
                newFileName = fileName[1:]
        return newFileName

    def buildDirOnTape(self, newFileName, currentTapeUID, tapeDrive):
        " build directory structure on tape if it does not exist "
        currentDirectory = os.path.join(tapeDrive,currentTapeUID)
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName)) # break up full file name into its part
        maxDirParts = len(fileNameParts) - 1
        for i in range(maxDirParts):
          currentDirectory = os.path.join(currentDirectory,fileNameParts[i])
        try:
            if not os.path.exists(currentDirectory):
                os.makedirs(currentDirectory)
            return True
        except:
            self.log.logIt(1, "class FileTools function BuildDirOnTape program error: tape " + currentTapeUID + " "+ str(sys.exc_info()[1]))
            return False

    def sameAsLastDir(self,newFileName):
        currentDirectory = ""
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName))
        maxDirParts = len(fileNameParts) - 1
        for i in range(maxDirParts):
            currentDirectory = fileNameParts[i] if i == 0 else  os.path.join(currentDirectory,fileNameParts[i])
        return currentDirectory == self.lastDirectory

    def getFileId(self, newFileName):
        " returns the file id from the database "
        parentId = 0
        fileId = 0
        lastPartFound = -1
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName)) #break up full file name into its part

        try:
            maxDirParts = len(fileNameParts) - 1
            if len(fileNameParts) > 1:
                for i in range(maxDirParts):
                    curIndex, cur = self.conn.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i],parentId))
                    row = cur.fetchone()
                    if row != None:
                        parentId = row[0]
                        lastPartFound = i
                        self.conn.free(curIndex)
                    else:
                        lastPartFound == -1
                        self.conn.free(curIndex)
                        break
            else:
                lastPartFound = 0

            if lastPartFound != -1:
                curIndex, cur = self.conn.read("SELECT FileId FROM Files where FileName = %s and DirectoryId = %s",(fileNameParts[maxDirParts],parentId))
                row = cur.fetchone()
                if row != None:
                    fileId = row[0]
                self.conn.free(curIndex)
        except:       
            self.log.logIt(2, "class FileTools function getFileId program error: "+ str(sys.exc_info()[1]))
        self.lastFileId = fileId
        return fileId

    def buildDBDirectory(self, newFileName):
        " builds the subfolder structure in the database "
        directoryBuilt = False
        parentId = 0
        lastPartFound = False
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName))
        self.lastDirectory = ""
        fullName = ""
        try:
            if len(fileNameParts) > 1:
                nextFolder = 0
                self.lastDirectory = fileNameParts[0]
                maxDirParts = len(fileNameParts) - 1
                for i in range(maxDirParts):
                    curIndex, cur = self.conn.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i],parentId))
                    row = cur.fetchone()
                    if row != None:
                        lastPartFound = True
                        parentId = row[0]
                        self.lastDirectory = fileNameParts[i] if i == 0 else  os.path.join(self.lastDirectory, fileNameParts[i])
                    else:
                        lastPartFound = False
                    self.conn.free(curIndex)
                    fullName = os.path.join(fullName, fileNameParts[i])
                    if not lastPartFound:
                        self.conn.write("INSERT INTO Directories (ParentId, DirectoryName, FullName, EntryDate) VALUES (%s, %s, %s, %s)",( parentId,fileNameParts[i],fullName,dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        curIndex, cur = self.conn.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i],parentId))
                        row = cur.fetchone()
                        parentId = row[0]
                        self.conn.free(curIndex)
            self.lastEndFolderId = parentId
            directoryBuilt = True
        except:
            self.lastDirectory = ""
            self.log.logIt(2, "class FileTools function buildDBDirectory program error: "+ str(sys.exc_info()[1]))

        return directoryBuilt
    
    def addToTapeFiles(self, tapeUID, dupSequence):
        "  add file file tape folder "
        recAdded = False
        tapeFilefound = False
        try:
            if self.lastFileId != 0:
                curIndex, cur = self.conn.read("SELECT FileId FROM TapeFiles where TapeUID = %s and FileId = %s",(tapeUID, self.lastFileId))
                row = cur.fetchone()
                tapeFilefound = (row != None)
                self.conn.free(curIndex)
                if not tapeFilefound:
                    self.conn.write("INSERT INTO TapeFiles (TapeUID, FileId, DupSequence) VALUES (%s, %s, %s)",(tapeUID, self.lastFileId, dupSequence))
                recAdded = True
        except:
            self.log.logIt(2, "class FileTools function AddToTapeFiles program error: "+ str(sys.exc_info()[1]))
        return recAdded

    def addFileToDB(self, smallFileName, fullFileName):
        " add file to db "
        fileAdded = False
        try:
            fileSize = os.path.getsize(fullFileName)
            createDate = dt.datetime.fromtimestamp(os.path.getmtime(fullFileName)).strftime('%Y-%m-%d %H:%M:%S')
            modifyDate = dt.datetime.fromtimestamp(os.path.getctime(fullFileName)).strftime('%Y-%m-%d %H:%M:%S')
            lastAccess = dt.datetime.fromtimestamp(os.path.getatime(fullFileName)).strftime('%Y-%m-%d %H:%M:%S')
            archiveDate =  dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.conn.write("INSERT INTO Files (FileName, Size, CreateDate, ModifyDate, ArchiveDate, DirectoryId, LastAccess) VALUES (%s, %s, %s, %s, %s, %s, %s)", (smallFileName, fileSize, createDate, modifyDate, archiveDate, self.lastEndFolderId, lastAccess))
            fileAdded = True
            curIndex, cur = self.conn.read("SELECT FileId FROM Files where FileName = %s and DirectoryId = %s",(smallFileName, self.lastEndFolderId))
            row = cur.fetchone()
            if row != None:
                self.lastFileId = row[0]
            self.conn.free(curIndex)
        except:
            self.log.logIt(2,"Unable to add file " + fullFileName + " to database. "+ str(sys.exc_info()[1]))
        return fileAdded

    def isFileDupOnTape(self, newFileName, dupSequence):
        " find is file dup sequence is  on tape "
        parentId = 0
        lastPartFound = -1
        fileId = 0
        fileOnTape = False
        fileNameParts = self.__disassembleFileName(newFileName)
        maxDirParts = len(fileNameParts) - 1

        try:
            if len(fileNameParts) > 1:
                for i in range(maxDirParts):
                    curIndex, cur = self.conn.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s",(fileNameParts[i], parentId))
                    row = cur.fetchone()
                    if row != None:
                        parentId = row[0]
                        lastPartFound = i
                        self.conn.free(curIndex)
                    else:
                        lastPartFound = -1
                        self.conn.free(curIndex)
                        break
            else:
                lastPartFound = 0

            if lastPartFound != -1:
                curIndex, cur = self.conn.read("SELECT FileId FROM Files where FileName = %s and DirectoryId = %s",(fileNameParts[maxDirParts], parentId))
                row = cur.fetchone()
                if row != None:
                    fileId = row[0]
                    self.conn.free(curIndex)
                    curIndex, cur = self.conn.read("SELECT TapeUID FROM TapeFiles WHERE FileId = %s and DupSequence = %s",(fileId, dupSequence))
                    row = cur.fetchone()
                    fileOnTape = (row != None)
                    self.conn.free(curIndex)
                else:
                    self.conn.free(curIndex)  
        except:
            self.log.logIt(2, "class FileTools function isFileDupOnTape program error: "+ str(sys.exc_info()[1]))

        return fileOnTape

    def getLastEndFolderId(self):
        " returns last end folder id of last directory built "
        return self.lastEndFolderId

    def getLastFileId(self):
        " returns Id of last file "
        return self.lastFileId
   
    def fileRegistered(self, smallFileName):
        " check if file is in DB "
        fileFound = False
        try:
            curIndex, cur = self.conn.read("SELECT FileId FROM Files WHERE FileName = %s AND DirectoryId = %s",(smallFileName, self.lastEndFolderId))
            row = cur.fetchone()
            if row != None:
                fileFound = True
                self.lastFileId = row[0]
            else:
                self.lastFileId = 0 
            self.conn.free(curIndex)                  
        except:
            self.log.logIt(2, "class FileTools function fileRegistered program error: "+ str(sys.exc_info()[1]))
        
        return fileFound
    
    def shortFileName(self, newFileName):
        " returns short file name  "
        shortFileName = ""
        fileNameParts = self.__disassembleFileName(self.__cleanFileName(newFileName))
        if len(fileNameParts) == 1:
            shortFileName = fileNameParts[0]
        else:
            shortFileName = fileNameParts[len(fileNameParts) - 1]
        return shortFileName

class TapeManagement:
    """ class for tape management function  tapes status: active, full, new """ 
        
    def __init__(self, currentConn, currentTapeLibrary, currentLog):
        self.conn = currentConn
        self.tapeLibrary = currentTapeLibrary + "/"
        self.log = currentLog
        self.tapeUID = "NA"
        self.__reconcileInLibrary()

         
    def closeActiveTape(self):
        "  close current tape and mark as full "
        try:
            if self.tapeUID != "NA":
                self.conn.write("UPDATE LTOTapes SET Status = 'full', FullDate = %s WHERE TapeUID = %s",(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),self.tapeUID))
        except:
            self.log.logIt(2, "class TapeManagement function CloseActiveTape program error: "+ str(sys.exc_info()[1]))

    def getTapeUID(self):
        # return current working TapeUId
        return self.tapeUID
    
        #     Function to determine LTO Type from TapeID Number
        #     July 2018
   
    def get_lto_type(self,tape_id):
		
        target_barcode = tape_id
        
        # Take last two characters from barcode
        # Barcodes are always 8 characters in our system

        lto_code = target_barcode[6:9]
        
        # Note LTO10,11,12 not yet officially specified June 2018

        lto_code_translator = {
            'L4': 'LTO4',
            'L5': 'LTO5',
            'L6': 'LTO6',
            'L7': 'LTO7',
            'L8': 'LTO8',
            'M8': 'LTo7M',            
            'L9': 'LTO9',
            'LA': 'LTO10',
            'LB': 'LTO11',
            'LC': 'LTO12',           
         # IBM Enterprise Cartridges       
            'JJ': '3592J',
            'JR': '3592R',
            'JA': '3592A',
            'JW': '3592W',
            'JB': '3592B',
            'JX': '3592X',
            'JK': '3592K',
            'JC': '3592C',
            'JY': '3592Y',
            'JD': '3592D',
            'JZ': '3592Z',
            'JL': '3592L',        
       }

        # pulls lto_type from dictionary

        lto_type = lto_code_translator[lto_code]

        return lto_type



    
    def getActiveTape(self, dupSequence):
        # get active tape based on duplication sequeunce
        inLibrary = 0
        currentStatus = 0
        foundTape = False
        self.tapeUID = "NA"
        statusValue = ["active", "used", "new"]

        try:
            for i in range(len(statusValue)):
                currentStatus = i
                curIndex, cur = self.conn.read("SELECT TapeUID, InLibrary FROM LTOTapes WHERE Status = %s and DupSequence = %s ORDER BY InLibrary, TapeUID ASC",(statusValue[i],-1 if i == 2 else dupSequence))
                for row in cur:
                    if os.path.isdir(os.path.join(self.tapeLibrary, str(row[0]))):
                        self.tapeUID = row[0]
                        inLibrary = row[1]
# 1.4 Check to determine if tape is WRITABLE                        
                        if common.isThisTapeWritable(self.tapeUID) == True:
                            foundTape = True
                            break
#  end Check                            
                self.conn.free(curIndex)
    
                if foundTape:
                    break

            if self.tapeUID != "NA": # update active tape information
                if currentStatus != 0 or inLibrary != 1:
                    self.conn.write("UPDATE LTOTapes SET Status = 'active', ActiveStart = %s, InLibrary = 1, DupSequence = %s WHERE TapeUID = %s",(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),dupSequence,self.tapeUID)) #  if no more references exist remove file 
 
                # ensure that that an active tape out of library is not available
                self.conn.write("UPDATE LTOTapes SET Status = 'used'  WHERE Status = 'active' and  DupSequence = %s and TapeUID <> %s",(dupSequence,self.tapeUID))
        except:
            self.log.logIt(2, "class TapeManagement function GetActiveTape program error: "+ str(sys.exc_info()[1]))

        return self.tapeUID

    def __reconcileInLibrary(self):
        " this routine reconciles the tapes in a tape library to ensure that what is in the library matches what is in the database "
        isFolder = []
        notInLibrary = {}
        addToDB = []
        updateDB = []
        dirParts = []
        holdTapeName = ''
        try:
            self.log.logIt(0, "Begin library reconciliation.")
            # get all tapes in library based on directory search command
            dirs = os.listdir(self.tapeLibrary)
            for dir in dirs:
                if os.path.isdir(os.path.join(self.tapeLibrary,dir)) and len(dir) ==  8:
                    isFolder.append(dir)
            # find all tapes listed in the database that indicate that they are currently in the library. Separate tapes that are indicated to be in tape library but are not
            curIndex, cur = self.conn.read("SELECT TapeUID, Status FROM LTOTapes WHERE InLibrary = 1")
            for row in cur:
                if str(row[0]) in isFolder:
                    for i in range(len(isFolder)-1, -1, -1):
                        if str(row[0]) == isFolder[i]:
                            del isFolder[i]
                else:
                    notInLibrary[str(row[0])] = row[1]
            self.conn.free(curIndex)
            # update db tape information to indicate that it is not in the library
            if len(notInLibrary) > 0:
                for key in notInLibrary:
                    self.conn.write("UPDATE LTOTapes SET InLibrary = 0, status = %s WHERE TapeUID = %s",("used" if notInLibrary[key] == "active" else notInLibrary[key],key))

            #  check for unaccounted for tapes in library
            if len(isFolder) > 0:
                for currentTape in isFolder:
                    curIndex, cur = self.conn.read("SELECT TapeUID, InLibrary FROM LTOTapes WHERE TapeUID = %s",(currentTape,))
                    foundTape = False
                    for row in cur:
                        foundTape = True
                        break
                    self.conn.free(curIndex)
                    if not foundTape:
                        addToDB.append(currentTape)
                    else:
                        updateDB.append(currentTape)

            # add all tapes in library that are not accounted for in db          
            if len(addToDB) > 0:
               for currentTape in addToDB:
				   
#				   Add find tape type code
                   new_tape_num = currentTape
                   newtapetype = self.get_lto_type(new_tape_num)
                   
                   self.conn.write("INSERT INTO LTOTapes (TapeUID, Status, TapeType, Inlibrary, DupSequence) VALUES (%s, 'new', %s, 1, -1)",(currentTape,newtapetype))

            if len(updateDB) > 0:
                for currentTape in updateDB:
                    self.conn.write("UPDATE LTOTapes SET InLibrary = 1 WHERE TapeUID = %s",(currentTape,))
        except:
            self.log.logIt(2, "class TapeManagement function reconcileInLibrary program error: "+ str(sys.exc_info()[1]))
        self.log.logIt(0, "End library reconciliation.")


class RemoveDiskQueue:
    """ checks remove disk queue to remove files from tapes """

    def __init__(self, currentConn, currentLog, currentTapeDrive):
            self.conn = currentConn
            self.log = currentLog
            self.tapeDrive = currentTapeDrive + "/"
            self.tapes = TapeList(currentConn)
            self.missingTapeList =[]
        
    def __cleanFileName(self, fileName):
        "  remove / from beginning of file name "
        newFileName = fileName
        if len(fileName) > 0:
            if fileName.startswith("\\") or fileName.startswith("/"):
                    newFileName = fileName[1:]
        return newFileName

    def __deleteFile(self,fullfileName,partialFileName,fileId,tapeUID,notify):
        " delete file from tapes and clean up entries in database "
        fileDeleted = True

        try:
            if os.path.isfile(fullfileName):
                os.remove(fullfileName) # remove file from tape
            self.conn.write("DELETE FROM TapeFiles WHERE TapeUID = %s AND FileId = %s",(tapeUID,fileId)) # remove file tape reference from DB
            self.log.logIt(0, fullfileName + " has been deleted")

            copyExists = False
            curIndex, cur = self.conn.read("SELECT FileId FROM TapeFiles where FileId = %s",(fileId,))
            for row in cur:
                copyExists = True
                break
            self.conn.free(curIndex)
            if (not copyExists):
                self.conn.write("DELETE FROM Files WHERE FileId = %s",(fileId,)) #  if no more references exist remove file 
                self.__removeFromQueue(partialFileName)
        except:
            if notify == 0:
                self.log.logIt(2, "class RemoveDiskQueue function deleteFile program error: "+ str(sys.exc_info()[1]))
            fileDeleted = False
        return fileDeleted

    def __removeFromQueue(self, partialFileName):
        " remove entry from disk queue "

        try:
            self.conn.write("DELETE FROM RemoveDiskQueue WHERE FullFileName = %s",(partialFileName,))  
        except:
            doNothing = True
        
    def __updateTapeWarning(self,fileNane,warning):
        " change value of tapewarning on tape to avoid repeated messages going to administrator "
        try:
            self.conn.write("UPDATE RemoveDiskQueue SET NoTapeWarning = %s WHERE FullFileName = %s",(warning,fileNane))  
        except:
            self.log.logIt(2, "class RemoveDiskQueue function UpdateTapeWarning program error: "+ str(sys.exc_info()[1]))

    def processQueue(self):
        " cycle through delete queue and remove files "
        fileList = []
        tapeWarnings = []
        currentTapeList = []

        srcWorkFile = ''
        srcDirectory = ''
        notification = 0
  
        # get list of files to remove 
        curIndex, cur = self.conn.read("SELECT FullFileName, NoTapeWarning FROM RemoveDiskQueue WHERE DateToRemove <= %s Order BY DateToRemove ASC",(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
        for row in cur:
            fileList.append(str(row[0]))
            tapeWarnings.append(row[1])
        self.conn.free(curIndex)
        # move through list and delete files from tape
        for cFile in range(len(fileList)):
            currentTapeList = self.tapes.createNewList(fileList[cFile])  # return list of tapes where file exists
            if len(currentTapeList) > 0: # check for at least one tape, if on no tapes remvove delete entry
                for cTape in range(len(currentTapeList)): # cycle throgh tapes to delete file copies
                    notification = tapeWarnings[cFile]
                    srcDirectory = self.tapeDrive  + currentTapeList[cTape]
                    srcWorkFile = os.path.join(srcDirectory, fileList[cFile])
                    if  os.path.isdir(srcDirectory): # check if tape is in library, if so attempt to delete file or add to missing tape list and notify administrator.
                        if not self.__deleteFile(srcWorkFile, fileList[cFile], self.tapes.getFileId(), currentTapeList[cTape], notification):
                            if notification == 0:
                                self.log.logIt(1, "Issues deleting " + srcWorkFile + " from tape " + currentTapeList[cTape])
                                notification = 1
                                self.__updateTapeWarning(fileList[cFile], notification)
                    else:
                        if not self.missingTapeList.Contains(currentTapeList[cTape]):
                            self.missingTapeList.append(currentTapeList[cTape])
                            log.logIt(2, "Tape " + currentTapeList[cTape] + " not in library")
            else:
                self.__removeFromQueue(fileList[cFile])


class TapeList:
    """ create list of new tapes """

    def __init__(self,currentConn):
        self.listOfTapes = []       
        self.conn = currentConn
        self.fileId = 0

    def createNewList(self,newFileName):
        " create a list of tapes to remove files "
        parentId = 0
        lastPartFound = -1
        fileNameParts = self.__disassembleFileName(newFileName) #break up full file name into its part
        maxDirParts = len(fileNameParts) - 1
        if len(self.listOfTapes) > 0:
            self.listOfTapes[:] = []
                        
        try:
            if len(fileNameParts) > 1:
                for i in range(maxDirParts):
                    curIndex, cur = self.conn.read("SELECT DirectoryId FROM Directories where DirectoryName = %s and ParentId = %s", (fileNameParts[i],parentId))
                    row = cur.fetchone()
                    if not row == None:
                            parentId = row[0]
                            lastPartFound = i
                            self.conn.free(curIndex)
                    else:
                        lastPartFound = -1
                        self.conn.free(curIndex)
                        break
            else:
                lastPartFound = 0

            if lastPartFound != -1:
                curIndex, cur = self.conn.read("SELECT FileId FROM Files where FileName = %s and DirectoryId = %s", (fileNameParts[maxDirParts],parentId))
                row = cur.fetchone()
                if not row == None:
                    self.fileId =row[0]
                    self.conn.free(curIndex)
                    curIndex, cur = self.conn.read("SELECT TapeFiles.TapeUID FROM TapeFiles INNER JOIN LTOTapes ON TapeFiles.TapeUID = LTOTapes.TapeUID WHERE (TapeFiles.FileId = %s) AND (LTOTapes.InLibrary = 1) ORDER BY LTOTapes.DupSequence", (self.fileId,))
                    rows = cur.fetchall()
                    for row in rows:
                        self.listOfTapes.append(str(row[0]))
                    self.conn.free(curIndex)
                else:
                    self.conn.free(curIndex)
        except:
            print (str(sys.exc_info()[1]))
        return self.listOfTapes

    def getFileId(self):
        " return current file id "
        return self.fileId

    def __disassembleFileName(self,newFile):
        " disassembles file name into it's parts "
        return newFile.replace("\\", "/").split('/')

class FileCacheManager:
    """  manages name of recently accessed files """

    def __init__(self,configCacheMaxSize):
        self.cacheMaxSize = int(configCacheMaxSize)
        self.fileTapes = {}
        self.recentFiles = []

    def addFile(self,fileName,tapeName):
        "add new file tape combination"
        if fileName not in self.fileTapes:      
        
# deprecated in 3.11        if not self.fileTapes.has_key(fileName):

            if len(self.recentFiles) > self.cacheMaxSize:
# deprecated                if self.fileTapes.has_key(self.recentFiles[0]):
					
                if self.recentFiles[0] in self.fileTapes:	
					
					
                    del self.fileTapes[self.recentFiles[0]]
                self.recentFiles.pop(0)
            self.fileTapes[fileName] = tapeName
            self.recentFiles.append(fileName)

    def inList(self,fileName):
        " look if file in list "
# deprecated        return self.fileTapes.has_key(fileName)
        
        return fileName in self.fileTapes

    def newRoot(self,fileName):
        " returns tape to create new root for file"
        return self.fileTapes[fileName]


# open config file get to get virtual drive properties
class DriveProperties:
 
    # Extracts properities from configuration table
    def __init__(self):
        self.info = {'error': 1, 'errormsg': 'Unable to open configuration file'}
        try:
            with open("EchoLeaf.config", "r") as configuration:
                self.info =  json.load(configuration)                
            key = load_key()               
            self.info["sysadminpassword"] = decryptIT(self.info["sysadminpassword"],  key)
            self.info["password"] = decryptIT(self.info["password"],  key)
            # adding below
            self.info["error"] = 0                  
            self.info["errormsg"] = ''                 
        except:
            self.info["error"] = 2
            self.info["errormsg"] = str(sys.exc_info()[1]) 
        
        if self.info["error"] == 0:
            try:
                                
                conn = mdb.connect(
                    host=self.info["host"],
                    user=self.info["user"],
                    password=self.info["password"],
                    database=self.info["database"]
                ) 

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
                self.info["errormsg"] = str(sys.exc_info()[1])  
        
        programPath =  os.path.abspath('')
        self.info["programFolder"] = programPath
        self.info["logFolder"] = os.path.join(programPath, "logfiles")

    def getInfo(self, infoProperty):
        """ Return value of provided property """
        infoValue = '' 
# deprecated        if self.info.has_key(infoProperty):		
        if infoProperty in self.info: 						
            infoValue = self.info[infoProperty]
        return infoValue

    def getInfoAll(self):
        """ return all properties in dictionary """
        return self.info

    def dbExists():
        return True if self.info["error"] == 0 else False

         

# create and write to log file / revised March 2025



import os
import datetime as dt
import sys
import smtplib  # Keep smtplib, but don't use it in __init__
import traceback

class LogMaintenance:
    """ creates and allows entries to log file """

    def __init__(self, info):
        self.info = info
        self.mailAvailable = False  # Assume mail is NOT available initially
        self.logCounter = 0
        self.error = 0        # Add error flag
        self.error_message = ""

        # --- Minimal Configuration Check ---
        if self.info.get("MailFrom") == "none" or self.info.get("AdminEmail1") == "none":
            self.error = 1
            self.error_message = "Mail is not configured."
            print(self.error_message)
        # --- NO SMTP CONNECTION ATTEMPT HERE ---

    def __logFullFileName(self):
        return os.path.join(self.info.get("logFolder", "."), "ex" + dt.datetime.now().strftime('%Y%m%d') + ".txt")  # Use .get()

    def logIt(self, infoType, issue):
        try:
            entryType = ["info", "warn", "error"]
            self.logCounter += 1
            log_message = f'{dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}|vitualdrive|{entryType[infoType]}|{issue}\n'
            with open(self.__logFullFileName(), "a") as logFile:
                logFile.write(log_message)
            print(log_message, end="")  # Print without extra newline

        except Exception as e:
            print(f"Error writing to log file: {e}")
            print(traceback.format_exc())  # Use traceback

        # --- Conditional Mail Sending (Still Here, But Only If Configured) ---
        if self.error == 0: # only send mail if there is no error
            if self.info.get("NotifyOnWarning") == "yes" and infoType == 1:
                self.__sendMail(self.info.get("SubjectWarning", "File Manager Warning"), issue)  # Use .get()
            elif self.info.get("NotifyOnError") == "yes" and infoType == 2:
                self.__sendMail(self.info.get("SubjectError", "File Manager Error"), issue)  # Use .get()

    def __sendMail(self, subject, body):
        # --- Lazy Initialization of SMTP Connection ---
        if self.error == 0: # only try if no errors
            try:
                mailTo = [self.info["AdminEmail1"]]
                if self.info.get("AdminEmail2") != "none":  # Use .get()
                    mailTo.append(self.info["AdminEmail2"])

                # --- Connection Attempt INSIDE __sendMail ---
                smtpObj = None  # Initialize smtpObj
                try:
                    if self.info.get("MailHost") != "localhost": # Use .get()
                        smtpObj = smtplib.SMTP(self.info["MailHost"], int(self.info.get("MailPort", 25))) # Use get and default port
                    else:
                        smtpObj = smtplib.SMTP('localhost')

                    message = f"""\
From: {self.info.get("MailFrom")}
To: {", ".join(mailTo)}
Subject: {subject}

{body}
"""
                    smtpObj.sendmail(self.info.get("MailFrom"), mailTo, message)
                    self.mailAvailable = True #set if it works.
                except Exception as e:
                    print(f"Error sending mail: {e}")
                    print(traceback.format_exc())
                    self.mailAvailable = False # if it does not work.
                    self.error = 3
                    self.error_message = "Mail server unavailable."
                finally:  # Ensure smtpObj is cleaned up
                    if smtpObj:
                        try:
                            smtpObj.quit()
                        except:
                            pass #ignore errors during cleanup

            except Exception as e: # Catching all
                print("Exception in sendMail:", e)
                print(traceback.format_exc()) # More data if possible.      


                  
                
# Depracated now in common
def decryptIt(strEncoded):
	BLOCK_SIZE = 16
	PADDING = '{'
	pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
	DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
	key = "53f7d42cbf4d485b781f818fb9e1cd11"
	cipher = AES.new(unhexlify(key))
	return DecodeAES(cipher, strEncoded)

def fileManagerStarted(host, user, password, database):
    dict = {"error": 0, "errormsg": "filemanager run marker added"}
    try:
        
        conn = mdb.connect(host=host, user=user, password=password, database=database)       

        
        cur = conn.cursor() 
        cur.execute("DELETE FROM Configuration WHERE Property = 'FileManagerStatus'")
        cur.execute("INSERT INTO Configuration (Property, PropertyValue) VALUES ('FileManagerStatus', 'UP') ")
        conn.commit()
        cur.close()
        conn.close()
    except:
        dict["error"] = 1
        dict["errormsg"] = "Attempt to add filemanager start marker: " + str(sys.exc_info()[1])  
    return dict

def fileManagerCheck(host, user, password, database):
    result = {"error": 0, "errormsg": "filemanager marker found"}
    try:
        conn = mdb.connect(host=host, user=user, password=password, database=database)
        cur = conn.cursor()
        cur.execute("SELECT PropertyValue FROM Configuration WHERE Property = 'FileManagerStatus'")
        row = cur.fetchone()
        if row is None:  # Use 'is None' for comparison with None
            result["error"] = 1
            result["errormsg"] = "filemanager up marker does not exist"

    except mdb.Error as err:  # Catch specific MySQL errors
        result["error"] = 2
        result["errormsg"] = f"Error on filemanager marker check: {err}"

    finally:  # Ensure connections are closed
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

    return result


 
def validateConfig():
    dict = {"error": 0, "errormsg": ""}
    if os.path.isfile("EchoLeaf.config"):
        configInfo = DriveProperties().getInfoAll()
        if configInfo["error"] == 0:
            if os.path.exists(configInfo["CacheLocation"]):
                if not os.path.exists(configInfo["TapeDrive"]):
                    dict["error"] = 4
                    dict["errormsg"] = "LTFS Library Location " + configInfo["TapeDrive"] + " does not exist."
            else:
                dict["error"] = 3
                dict["errormsg"] = "Cache Location " + configInfo["CacheLocation"] + " does not exist."
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

# Archive Tool
# The EchoLeaf Archive Tool runs once daily.   It  starts with each run of filemanager, but stops if
# a file with today's date exists in the hidden system folder .ELSystem/archive

def runELArchive():
	
    # test = True will skip over the os.system commands
    test = False
    newinfo = DriveProperties()
    mount = newinfo.getInfo("VDiskMountPoint")
    cachefolder = newinfo.getInfo("CacheLocation")
    softwarefolder = newinfo.getInfo("SoftwareLocation")
    print(mount)
    print(cachefolder)
    print(softwarefolder)
    
    # tmsemptycache exists when Virtual Drive is running    
    newmount = mount + '/tmsemptycache'
    print(newmount)
    
    # checks if VD is running, otherwise abort loop
    testMount = os.path.isdir(newmount)
    print(testMount)    # true or false
    if testMount == False:  # Stop because Mount.py is not running
        print("Archive activity stopped.  Must run Mount.")
    else:    # Proceed to all archive processes.
        print("go") 

    # Now that we know Mount.py is running, we test for the .ELSystem folder
    #  .ELSystem is a hidden folder used for EchoLeaf System functions
        archmount = mount + "/.ELSystem"
        print(archmount)  # Hidden folder for EchoLeaf Archive Files
        testarchmount = os.path.isdir(archmount)  # True or False
        print(testarchmount)

    # If it doesn't exist, we create it.   Note this is a hidden folder        
        if testarchmount == False:			
            os.mkdir(archmount)
            archmount = archmount + "/archive"
            os.mkdir(archmount)
            print(archmount + ' created!')
        else:
            archmount = archmount + "/archive"
            print(archmount + ' Exists')
        target = archmount
        command = "ls -l -R " + target

    # Read contents of hidden folder .ELArchive into a list called lines        
        lines = os.popen(command).readlines()

    # We use this date string to test to see if an archive file has been written today      

        now = date.today()
        todaydatestr = now.strftime("%Y%m%d")
        print(todaydatestr)
        didItAlready = False
        for line in lines:
            if todaydatestr in line:
                didItAlready = True
                print ("stop")
                break
                
    # If the file structure exists but IF there is any file in .ELSystem.archive with todays date, end operation 
               
        print(didItAlready)
                    
        if didItAlready == False:     #i.e. there is no file in .archive with todays date.
            print ("Let's go")  
                        
            #  Create EchoLeaf DataBase Dump file, archive to zip, place in archive folder archmount
            #  Below we use Cache as a working folder, because it is part of a big-ass file system.

            targetfile = cachefolder + "/ELDbsFiles" + todaydatestr + ".sql"

            #   Note:  This command runs becasue of information held in the mysql configuration file            

            cmnd = "/bin/mysqldump --all-databases > " + targetfile
            
            #debug 
            print("Target File = ")
            print(targetfile)
            print("Dump Command = ")
            print(cmnd)
            #debug
            
            if test == False:
                os.system(cmnd)
            
            newZipFileTarget = archmount + "/ELDbsFile" + todaydatestr + ".zip"
            
            #debug
            print("NewZipFileTarget =")
            print(newZipFileTarget)
            #debug
            
            fileToZip = targetfile  # just created with mysqldump

            #debug
            print("File To Zip = ")
            print(fileToZip)
            #debug
            
            createzipcmnd = "zip " + newZipFileTarget + " " +  fileToZip
            
            #debug
            print("Zip Command = ")
            print(createzipcmnd)
            #debug

            #    Create zip file in archive folder           

            if test == False:            
                os.system(createzipcmnd)
            
            # Housekeeping to remove original dumpfile after zipping it to a new location
            
            removedumpcmd = "rm " + fileToZip
            
            #debug
            print("Remove Dump File Command")
            print(removedumpcmd)
            #debug

            if test == False:            
                os.system(removedumpcmd)
 

            #  Create Roll up of EchoLeaf Cache.  archive to zip, place in archive folder archmount
            #  Create temp folder (in cache subdirectory) to store the EchoLeaf Cache rollup
        
            tempCacheFolder = cachefolder + "/tempCacheFolder"
            print("Temp Cache Folder")
            print(tempCacheFolder)
            makeTempFolderCmd = "mkdir -p " + tempCacheFolder
            print("Make Temp Folder Cmnd")
            print(makeTempFolderCmd)
            
            if test == False:            
                os.system(makeTempFolderCmd)
            
            #  Set up rsync to duplicate EchoLeaf Cache.  No big files.  Exclude temp folder.            
            copyCacheFolderCmnd = "rsync -r --max-size=1M --exclude 'tempCacheFolder' " + cachefolder + " " + tempCacheFolder 
            print("Copy CacheFolder Command")
            print(copyCacheFolderCmnd)
            
            if test == False:            
                os.system(copyCacheFolderCmnd)
            
            newZipFileTarget2 = archmount + "/ELCache" + todaydatestr + ".zip"
            print("New ZipFile Target 2")
            print(newZipFileTarget2)
             
            filesToZip = tempCacheFolder  # just created with rsync
            print("Files To Zip with -r")
            print(filesToZip)
                                   
            createzipcmnd2 = "zip -rq " + newZipFileTarget2 + " " +  filesToZip 
            print("Create zipfile command line")
            print(createzipcmnd2)
                
            #    Create zip file in archive folder           

            if test == False:
                os.system(createzipcmnd2)
            
            # Housekeeping to remove cachefile after zipping it to a new location
            
            removeTempCache = "rm -fr " + tempCacheFolder          
            print("Remove Temp Cache Command")
            print(removeTempCache)
            
            if test == False:
                os.system(removeTempCache)


            #  Create zip file of Software folder and subdirectories, place in archive folder archmount.		    	 
 
            #   Zip up all of the files in the EchoLeaf Software folder

            newZipFileTarget3 = archmount + "/ELSoftLogs" + todaydatestr + ".zip"
            print("New ZipFile Target 3")
            print(newZipFileTarget3)
             
            filesToZip3 = softwarefolder  # Current Software plus log files
            print("Files To Zip with -r")
            print(filesToZip3)
                                   
            createzipcmnd3 = "zip -rq " + newZipFileTarget3 + " " +  filesToZip3 
            print("Create zipfile command line")
            print(createzipcmnd3)
                
            #    Create zip file in archive folder           

            if test == False:
                os.system(createzipcmnd3)
            

            # Housekeeping // None needed.  We zipped up existing files to a new location on the VD.
            

            #   All of EchoLeaf Cache has now been duplicated, files under 1MB, not including the tempCacheFolder

            #   Zip up all of the files in the EchoLeaf Cache

#  End of Archive Routines.   NOTE -- Any other processes that need to run once daily can go here

#  From imported module. Collects system data and emails to admin contacts in configuration.
#  
            if test == False:
                phoneHome()
                

def getTapeAttributes():	
    objectType = 'cartridge'
    adminCmd = 'leadm tape list -o xml'   
    dict = common.ltfsAdminCmd(objectType,adminCmd)
    # dict is the data object derived from the leadm tape list -o xml command

# Below routine checks for tapes in and DRIVE and moves them to a home slot
    ctr = 0
    for data in dict['data']:
  
        test = "DRIVE"
        target = data[12]  # SLOT TYPE
        cmnd1 = "leadm tape move "
        if target.find(test) >= 0:
            ctr = ctr + 1 
            print("We Have A Winner!!  Tape Number " + data[0] + " Needs To Move To A Home Slot!")
            cmnd2 = cmnd1 + data[0]
            os.system(cmnd2)
            print("Move Completed for Tape " + data[0])
    
    strctr = str(ctr)    
    print("Move To Home Slot Cycle Finished -- " + strctr + " Moves Completed.")	

# Below routing checks for tapes needing recovery, and executes a recover process

    ctr = 0    
    for data in dict['data']:
   
        test = "RECOVER"
        target = data[1]  # status
        cmnd3 = "leadm tape recover "
        if target.find(test) >= 0:
            ctr = ctr + 1
            print("We Have A Winner!!  Tape Number " + data[0] + " Needs Recovery!")
            cmnd4 = cmnd3 + data[0]
            os.system(cmnd4)
            print("Recovery Completed for Tape " + data[0]) 
            
    strctr = str(ctr)         
    print("Tape Recovery Cycle Finished -- " + strctr + " Recoveries Completed.")
    
#Assignment   Must first move from ie slot
    
    ctr = 0    
    for data in dict['data']:
   
        test = "ASSIGN"
        target = data[1]  # status
        cmnd5 = "leadm tape assign "
        if target.find(test) >= 0:
            ctr = ctr + 1
            print("We Have A Winner!!  Tape Number " + data[0] + " Needs Assignment!")
            cmnd6 = cmnd5 + data[0]
            cmnd7 = "leadm tape move " + data[0]
            os.system(cmnd7)  # if tape is in ieslot, it must be moved to a normal slot
            os.system(cmnd6)  # then we can do the tape assignment
            print("Assignment Completed for Tape " + data[0]) 
            
    strctr = str(ctr)         
    print("Tape Assignment Cycle Finished -- " + strctr + " Assignments Completed.") 
    
## Mount unmounted // To Mount unmounted tapes, they need to be recovered (go figure.)
    
    ctr = 0    
    for data in dict['data']:
   
        test = "NOT_MOUNTED"
        target = data[1]  # status
        cmnd8 = "leadm tape recover "
        if target.find(test) >= 0:
            ctr = ctr + 1
            print("We Have A Winner!!  Tape Number " + data[0] + " Needs Mounting!")
            cmnd9 = cmnd8 + data[0]
            os.system(cmnd9)  
            print("Mounting Completed for Tape " + data[0]) 
            
    strctr = str(ctr)         
    print("Tape Munting Cycle Finished -- " + strctr + " Mountings Completed.")     
    

import os
import sys
import shutil
import datetime as dt
import time

# manage restore items in queue

class RestoreManagementQueue:

    def __init__(self, currentConn, tapeDrive, restoreAtlernate, vDiskMountPoint, copyBackRemoveDelay, currentLog, cacheLocation):  # Add cacheLocation
        self.conn = currentConn
        self.tapeDrive = tapeDrive
        self.vDiskMountPoint = vDiskMountPoint
        self.copyBackRemoveDelay = copyBackRemoveDelay
        self.restoreTo = {'RestoreAlternate': restoreAtlernate, 'VDiskMountPoint': vDiskMountPoint};
        self.dirHistory = {}
        self.log = currentLog  # Use the passed logger instance (currentLog)
        self.cacheLocation = cacheLocation # Store cacheLocation
        self.log.logIt(0, f"--- Initializing RestoreManagementQueue ---")


#revised


    def processQueue(self):
        self.log.logIt(0, "--- Entering RestoreManagementQueue.processQueue ---")
        start_time = time.time()
        try:
            # get raw file list
            curIndex, cur = self.conn.read("SELECT RestoreManagement.RequestId, RestoreManagement.FileId, RestoreManagement.FileName, RestoreManagement.TapeUID, RestoreManagement.RestoreTo FROM RestoreManagement INNER JOIN Files ON RestoreManagement.FileId = Files.FileId WHERE RestoreManagement.Status = 'Queued' ORDER BY Files.ArchiveDate ASC")
            workList = {}

            for row in cur:
                workList[str(row[0])] = [str(row[1]), str(row[2]),str(row[3]),str(row[4])]
            self.conn.free(curIndex)
            self.log.logIt(0, f"RestoreManagementQueue.processQueue: Retrieved {len(workList)} items for processing")
            self.dirHistory.clear()
            self.log.logIt(0, f"RestoreManagementQueue.processQueue: dirHistory cleared")

            for item in workList:
                # found = False  <-- REMOVE THIS
                # curIndex, cur = self.conn.read("SELECT RequestId FROM RestoreManagement where RequestId = %s AND Status = 'Queued'",(int(item),)) <-- REMOVE THIS
                # row = cur.fetchone()  <-- REMOVE THIS
                # if row != None:      <-- REMOVE THIS
                #     found = True     <-- REMOVE THIS
                # self.conn.free(curIndex) <-- REMOVE THIS
                # if found:  <-- REMOVE THIS, and unindent the rest

                self.log.logIt(0, f"RestoreManagementQueue.processQueue: Processing request ID {item}")
                item_start_time = time.time()
                error, path = self.__buildPath(workList[item])
                if error == 0:
                    if workList[item][3] == 'RestoreAlternate':
                        self.log.logIt(0, f"RestoreManagementQueue.processQueue: Calling __restoreAlternate for request ID {item}")
                        self.__restoreAlternate(workList[item], path, item)
                    else:
                        if alive(['mount'])['error'] == 0:
                            self.log.logIt(0, f"RestoreManagementQueue.processQueue: Calling __cacheLocation for request ID {item}")
                            self.__cacheLocation(workList[item], path, item)
                        else:
                            dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            self.conn.write("UPDATE RestoreManagement SET Status = 'Cancelled', StatusDate = %s, ResultText = 'Unable to create valid directory path for copy.' WHERE RequestId = %s",(dateStamp, int(item)))
                            self.log.logIt(1, f"RestoreManagementQueue.processQueue: Request ID {item} - Unable to create directory path")
                else:
                    self.log.logIt(1, f"RestoreManagementQueue.processQueue: Error building path for request ID {item}")
                item_end_time = time.time()
                duration = item_end_time - item_start_time
                self.log.logIt(0, f"RestoreManagementQueue.processQueue: Request ID {item} processed in {duration:.2f} seconds")
                # else:  <-- REMOVE THIS
                #    self.log.logIt(0, f"RestoreManagementQueue.processQueue: Skipping request ID {item} - not found in 'Queued' status")  <-- REMOVE THIS
        except Exception as e:
            self.log.logIt(1, f"RestoreManagementQueue.processQueue: Error during processing: {e}")
        finally:
            end_time = time.time()
            total_duration = end_time - start_time
            self.log.logIt(0, f"--- Exiting RestoreManagementQueue.processQueue (total time: {total_duration:.2f} seconds) ---")
            
            
# revised

    def __cacheLocation(self, request, path, item):
        start_time = time.time()
        self.log.logIt(0, f"--- Entering RestoreManagementQueue.__cacheLocation for request ID {item}, path: {path} ---")
        try:
            # Construct the tapeFile path (this is always correct)
            tapeFile = os.path.join(self.tapeDrive, os.path.join(request[2], os.path.join(request[1])))

            # --- CORRECT: Construct diskFile using self.cacheLocation ---
            # diskFile = os.path.join(self.cacheLocation, request[1])  # Use self.cacheLocation!  <-- OLD, REDUNDANT
            # --- END CORRECTION ---

            # Construct the destination path directly (absolute path)
            destinationFile = os.path.join(self.cacheLocation, request[1])

            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: tapeFile: {tapeFile}, destinationFile: {destinationFile}")

            # --- Use shutil.copy2 for direct copy to the Cache ---
            shutil.copy2(tapeFile, destinationFile)
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: Request ID {item} - Copied file from {tapeFile} to {destinationFile}")

            dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # --- ClearDiskQueue INSERT ---
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: Adding entry to ClearDiskQueue for: {destinationFile}")
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: self.copyBackRemoveDelay = {self.copyBackRemoveDelay}")  # Keep this log line for now
            dateToRemove = (dt.datetime.now() + dt.timedelta(days=int(self.copyBackRemoveDelay))).strftime('%Y-%m-%d %H:%M:%S')
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: dateToRemove = {dateToRemove}")  # Keep this log line for now
            try:
                self.conn.write("INSERT INTO ClearDiskQueue (FullFileName, DateQueued, DateToRemove, InProcess, ClearWarning) VALUES (%s, %s, %s, 0, 0)", (destinationFile, dateStamp, dateToRemove)) # Use destinationFile
                self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: ClearDiskQueue entry added.")
            except Exception as e:
                self.log.logIt(1, f"RestoreManagementQueue.__cacheLocation: ERROR inserting into ClearDiskQueue: {e}")

            # --- FileMoveLog INSERT ---
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: About to insert into FileMoveLog:")
            self.log.logIt(0, f"  dateStamp: {dateStamp}")
            self.log.logIt(0, f"  tapeFile: {tapeFile}")
            self.log.logIt(0, f"  destinationFile: {destinationFile}")
            self.log.logIt(0, f"  request[1]: {request[1]}")  #This might be redundant now.
            self.conn.write("INSERT INTO FileMoveLog (EntryDate, Direction, Source, Destination, FileName) VALUES (%s, 1, %s, %s, %s)", (dateStamp, tapeFile, destinationFile, request[1]))
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: Request ID {item} - Added entry to FileMoveLog")

            # --- Update RestoreManagement (AFTER FileMoveLog insert)---
            self.conn.write("UPDATE RestoreManagement SET Status = 'Completed', StatusDate = %s, ResultText = 'Copy completed.' WHERE RequestId = %s",(dateStamp, int(item)))
            self.log.logIt(0, f"RestoreManagementQueue.__cacheLocation: Request ID {item} - Status updated to Completed")

        except Exception as e:
            dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.conn.write("UPDATE RestoreManagement SET Status = 'Cancelled', StatusDate = %s, ResultText = %s WHERE RequestId = %s",(dateStamp, str(sys.exc_info()[1]), int(item)))
            self.log.logIt(1, f"RestoreManagementQueue.__cacheLocation: Request ID {item} - Error: {e}")
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.log.logIt(0, f"--- Exiting RestoreManagementQueue.__cacheLocation for request ID {item} (time: {duration:.2f} seconds) ---")
            


    def __restoreAlternate(self, request, path, item):
        start_time = time.time()
        self.log.logIt(0, f"--- Entering RestoreManagementQueue.__restoreAlternate for request ID {item}, path: {path} ---")
        try:
            tapeFile = os.path.join(self.tapeDrive,os.path.join(request[2],os.path.join(request[1])))
            diskFile = os.path.join(self.restoreTo[request[3]],os.path.join(request[1]))
            self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: tapeFile: {tapeFile}, diskFile: {diskFile}")

            if path != '':
                pathList = path.split('/')
                base = self.restoreTo[request[3]]
                for subDir in pathList:
                    base = os.path.join(base,subDir)
                    if not os.path.exists(base):
                        os.makedirs(base)
                        self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: Created directory: {base}")
            if not os.path.exists(diskFile):
                shutil.copy2(tapeFile,diskFile)
                self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: Request ID {item} - Copied file from {tapeFile} to {diskFile}")
                dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # --- FileMoveLog INSERT ---
                self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: About to insert into FileMoveLog:")
                self.log.logIt(0, f"  dateStamp: {dateStamp}")
                self.log.logIt(0, f"  tapeFile: {tapeFile}")
                self.log.logIt(0, f"  diskFile: {diskFile}")
                self.log.logIt(0, f"  request[1]: {request[1]}")
                self.conn.write("INSERT INTO FileMoveLog (EntryDate, Direction, Source, Destination, FileName) VALUES (%s, 1, %s, %s, %s)", (dateStamp, tapeFile, diskFile, request[1]))
                self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: Request ID {item} - Added entry to FileMoveLog")
                # --- Update RestoreManagement ---
                self.conn.write("UPDATE RestoreManagement SET Status = 'Completed', StatusDate = %s, ResultText = 'Copy completed.' WHERE RequestId = %s",(dateStamp, int(item)))
                self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: Request ID {item} - Status updated to Completed")

            else:
                dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.conn.write("UPDATE RestoreManagement SET Status = 'Completed', StatusDate = %s, ResultText = 'Copy not necessary, file already exists.' WHERE RequestId = %s",(dateStamp, int(item)))
                self.log.logIt(0, f"RestoreManagementQueue.__restoreAlternate: Request ID {item} - File already exists, copy skipped")
        except Exception as e:
            dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.conn.write("UPDATE RestoreManagement SET Status = 'Cancelled', StatusDate = %s, ResultText = %s WHERE RequestId = %s",(dateStamp, str(sys.exc_info()[1]), int(item)))
            self.log.logIt(1, f"RestoreManagementQueue.__restoreAlternate: Request ID {item} - Error: {e}")
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.log.logIt(0, f"--- Exiting RestoreManagementQueue.__restoreAlternate for request ID {item} (time: {duration:.2f} seconds) ---")
              
     

    def __buildPath(self, request):
        start_time = time.time()
        self.log.logIt(0, f"--- Entering RestoreManagementQueue.__buildPath for request: {request} ---")
        error = 0
        path = ''
        try:
            curIndex, cur = self.conn.read("SELECT DirectoryId FROM Files WHERE FileId = %s",(request[0],))
            row = cur.fetchone()
            if row != None:
                firstdir = int(row[0])
                dirId = firstdir
                self.conn.free(curIndex)
                self.log.logIt(0, f"RestoreManagementQueue.__buildPath: Initial Directory ID: {dirId}")
                if dirId > 0:
                    if str(dirId) in self.dirHistory:
                        path = self.dirHistory[str(dirId)]
                        self.log.logIt(0, f"RestoreManagementQueue.__buildPath: Found path in history: {path}")
                        dirId = 0
                    else:
                        while dirId > 0:
                            curIndex, cur = self.conn.read("SELECT ParentId, DirectoryName FROM Directories WHERE (DirectoryId = %s)",(dirId,))
                            row = cur.fetchone()
                            if row != None:
                                if path == '':
                                    path = row[1]
                                else:
                                    path = os.path.join(row[1], path)
                                self.log.logIt(0, f"RestoreManagementQueue.__buildPath: Current path being built: {path}")
                                dirId = int(row[0])
                            else:
                                dirId = 0
                                error = 1
                                self.log.logIt(1, f"RestoreManagementQueue.__buildPath: Invalid directory ID encountered: {dirId}")
                            self.conn.free(curIndex)
                        if error == 0:
                            self.dirHistory[str(firstdir)] = path
                            self.log.logIt(0, f"RestoreManagementQueue.__buildPath: Built path: {path}, storing in history")
            else:
                error = 1
                self.log.logIt(1, f"RestoreManagementQueue.__buildPath: File ID {request[0]} not found in Files table")
        except Exception as e:
            error = 1
            self.log.logIt(1, f"RestoreManagementQueue.__buildPath: Error building path: {e}")
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self.log.logIt(0, f"--- Exiting RestoreManagementQueue.__buildPath with error status {error} (time: {duration:.2f} seconds) ---")
        return error, path
        
        
        
           
 

# manage tape items in queue
class TapeManagementQueue:

    def __init__(self, currentConn, tapeDrive):
        self.conn = currentConn
        self.tapeDrive = tapeDrive
        self.ltfsCmd = {}
        self.ltfsCmd['Valid LTFS'] = {'x': '%s -t %s -f -- -f', 'r': '%s -t %s -r', 'm': '%s -t %s -r -m ieslot'}  #['x', 'r', 'm']  
        self.ltfsCmd['Unknown'] = {'i':  'ls %s/%s', 'r': '%s -t %s -r', 'm': '%s -t %s -r -m ieslot' } # ['i', 'r', 'm'] 
        self.ltfsCmd['Write protected'] = {'r': '%s -t %s -r', 'm': '%s -t %s -r -m ieslot'} # ['r', 'm'] 
        self.ltfsCmd['Warning'] = { 'r': '%s -t %s -r','m': '%s -t %s -r -m ieslot'} # ['r', 'm'] 
        self.ltfsCmd['Critical'] = { 'r': '%s -t %s -r','m': '%s -t %s -r -m ieslot'} # ['r', 'm'] 
        self.ltfsCmd['Unavailable'] = {'a': '%s -t %s -a', 'm': '%s -t %s -m ieslot'} # ['a', 'm'] 
        self.ltfsCmd['Invalid LTFS'] = {'c': '%s -t %s -c', 'm': '%s -t %s -m ieslot' } # ['c',  'm'] 
        self.ltfsCmd['Unformatted'] = {'f': '%s -t %s -f', 'm': '%s -t %s -m ieslot'} # ['f', 'm'] 
        self.ltfsCmd['Error'] = {'m': '%s -t %s -m ieslot'} # ['m'] 
        self.ltfsCmd['Non-supported'] = {'m': '%s -t %s -m ieslot'} # ['m'] 
        self.ltfsCmd['Cleaning'] = {'m': '%s -t %s -m ieslot'} # ['m'] 
        # New with LTFS 2.4 and leadm
        self.ltfsCmd['WRITABLE'] = {'tape unassign': '%s tape unassign %s'}  #['tape format', unassign, ]  
        self.ltfsCmd['NOT_MOUNTED_YET'] = {'tape recover': '%s tape recover %s', 'tape unassign': '%s tape unassign %s'  } # ['i', 'recover', 'unassign] 
        self.ltfsCmd['WRITE_PROTECTED'] = {'tape unassign': '%s tape unassign %s', 'tape move -L ieslot': '%s tape move -L ieslot %s'} # ['tape unassign', 'tape move'] 
        self.ltfsCmd['READ_ERROR'] = { 'tape recover': '%s tape recover %s','tape unassign': '%s tape unassign %s' } # ['tape unassign', 'tape move'] 
        self.ltfsCmd['WRITE_ERROR'] = { 'tape recover': '%s tape recover %s','tape move -L ieslot': '%s tape move -L ieslot %s'} # ['tape unassign', 'tape move'] 
        self.ltfsCmd['NEED_ASSIGN'] = {'tape assign': '%s tape assign %s', 'tape move -L ieslot': '%s tape move -L ieslot %s'} # ['a', 'tape move'] 
        self.ltfsCmd['NEED_RECOVERY'] = {'tape recover': '%s tape recover %s', 'tape move -L ieslot': '%s -t %s -m ieslot' } # ['tape recover',  'tape move'] 
        self.ltfsCmd['NEED_FORMAT'] = {'tape format': '%s tape format -f %s', 'tape move -L ieslot': '%s tape move -L ieslot %s'} # ['tape format', 'tape move'] 
        self.ltfsCmd['INACCESSIBLE'] = {'tape move -L ieslot': '%s tape move -L ieslot %s'} # ['tape move'] 
        self.ltfsCmd['NON_SUPPORTED_TAPE'] = {'tape move -L ieslot': '%s tape move -L ieslot %s'} # ['tape move'] 
        self.ltfsCmd['FULL'] = {'tape move -L ieslot': '%s tape move -L ieslot %s'} # ['tape move']
        self.ltfsCmd['METADATA_WRITABLE'] = {'tape unassign': '%s tape unassign %s'} # ['tape unassign'] 


#   Missing  Duplicated, Label Mismatch,  Write Fenced, Undecryptable, Need HBA Check, Need Unlock
#	Add later or ignore for now.  Unlikely circumstances. Deal with outside of UI
#   Note:  First %s = tool (leadm), specific command,  Second %s = TapeID     
              

    def processQueue(self):
        # get raw file list 
        curIndex, cur = self.conn.read("SELECT RequestId, TapeId, LTFSStatus, RequestTypeShort FROM TapeManagement WHERE Status = 'Queued' ORDER BY EntryDate ASC")
        workList = {}
        for row in cur:
            workList[str(row[0])] = [str(row[1]), str(row[2]),str(row[3])]
        self.conn.free(curIndex)

        for item in workList:
            dateStamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # confirms tape from db list is in library to process.  [1] = tape id number
            result = self.__getTapeStaus(workList[item][0])
            if result['error'] == 0:
				# confirms status of tape in db and in library are the same.
                if result['ltfsStatus'] == workList[item][1]:
                    self.conn.write("UPDATE TapeManagement SET Status = 'In Progress', StatusDate = %s WHERE RequestId = %s",(dateStamp, int(item)))
                    commandResult = self.__executeTapeCmd(workList[item][0],  workList[item][1], workList[item][2])
                    result = self.__getTapeStaus(workList[item][0])
                    if commandResult['error'] == 0:
                        ltfsStatus =  workList[item][1]
                        if result['error'] == 0:
                            ltfsStatus =  result['ltfsStatus']
                        self.conn.write("UPDATE TapeManagement SET Status = 'Completed', StatusDate = %s, LTFSStatus = %s, ResultText = %s WHERE RequestId = %s",(dateStamp, ltfsStatus, commandResult['errormsg'], int(item)))

# Add v1.4 // Covers error condition when there is no result data       
# Indicates a problem with the process.  In our case, usually File Manager is not running

                        if commandResult['errormsg'] == " ":
                            A = B
                            ltfsStatus =  workList[item][1]
                            if result['error'] == 0:
                                ltfsStatus =  result['ltfsStatus']
                            commandResult = "Warning. Possible problem executing Tape Managment instructions. Is File Manager running?  It should be."
                            self.conn.write("UPDATE TapeManagement SET Status = 'Completed', StatusDate = %s, LTFSStatus = %s, ResultText = %s WHERE RequestId = %s",(dateStamp, ltfsStatus, commandResult, int(item)))
# End error condition
                else:    
                    self.conn.write("UPDATE TapeManagement SET Status = 'Cancelled', StatusDate = %s, ResultText = 'Tape LTFS status changed since queued request, request cancelled.'  WHERE RequestId = %s",(dateStamp, int(item)))
            elif result['error'] == 1:
                self.conn.write("UPDATE TapeManagement SET Status = 'Cancelled', StatusDate = %s, ResultText = 'Tape  not found in library.' WHERE RequestId = %s",(dateStamp, int(item)))
            elif result['error'] == 2:
                self.conn.write("UPDATE TapeManagement SET Status = 'Cancelled', StatusDate = %s, ResultText = %s WHERE RequestId = %s",(dateStamp, result['errormsg'], int(item)))
# Added condition error 3 for new leadm errors
            elif result['error'] == 3:
                self.conn.write("UPDATE TapeManagement SET Status = 'Error Condition', StatusDate = %s, ResultText = %s WHERE RequestId = %s",(dateStamp, result['errormsg'], int(item)))


    def __executeTapeCmd(self, tapeId, status, command):
        dict = {'error': 0, 'errormsg': ''}
        tool = 'leadm'       
        try:
            if (command == 'i'):
                os.listdir(os.path.join(self.tapeDrive, tapeId))
                dict['errormsg'] =  'Attempted to read  tape directory.'
            else:  
                lines = os.popen(self.ltfsCmd[status][command] % (tool, tapeId)).readlines()
                lineCount = len(lines)
                for pos in range(0,lineCount):
                    lines[pos] =  lines[pos].strip()
                dict['errormsg'] = (' '.join(lines))[:256]
                
                if "Error" in dict['errormsg']:
                    dict['error'] = 3
					
                elif "error" in dict['errormsg']:
                     dict['error'] = 3	                
                
        except:
            dict['error'] = 1
            dict['errormsg'] = str(sys.exc_info()[1]) 
        return dict                       

# should be updated to leadm tape show / legacy from ltfsadmintool
# ltfs Status = WRITABLE etc.  [1] 

    def __getTapeStaus(self, tapeId):
        dict = {'error': 1, 'errormsg' : 'Tape Not found', 'ltfsStatus': '', 'tapeid': ''}
        tapeBreakout = '<object type="cartridge" id="'
        attrBreakout = '<attribute name="'
        valueBreakout = '<value>'
        rowCount = 0
        ltfsStatus = 'na'
        lookUpId = 'xxxxxxxx'
        try:
            lines = os.popen('leadm tape list -o xml').readlines()
            lineCount = len(lines)
            linePos = 0
            found = False
            first = True
            while (linePos < lineCount):
                if lines[linePos].find(tapeBreakout) >= 0:
                    lookUpId = lines[linePos].split(tapeBreakout)[1].split('">')[0]
                    first = True
                    linePos += 1
                    while (linePos < lineCount):
                        if lines[linePos].find(attrBreakout) >= 0:
                            linePos += 1
                            if first:
                                first = False
                                ltfsStatus = lines[linePos].split(valueBreakout)[1].split('</value>')[0]							
                            linePos += 2
                        else:
                            break
                    rowCount += 1
                else:
                    linePos += 1
                if (lookUpId == tapeId):
                    dict['tapeid'] = tapeId
                    dict['ltfsStatus'] = ltfsStatus
                    dict['error'] = 0
                    dict['errormsg'] = 'Tape found'
                    break
        except:
            dict['error'] = 2
            dict['errormsg'] = str(sys.exc_info()[1]) 
        return dict 
 
 

# import datetime as dt
# import fcntl
# import json
# import os
# import time
# import threading
# import sys

# ... (Your other classes: ConfigCheck, DriveProperties, LogMaintenance, DataStore,
#      RemoveDiskQueue, ToTapeQueue, ClearDisKQueue, TapeManagementQueue,
#      RestoreManagementQueue, etc. - make sure they are defined here) ...



# ... (Other imports and functions: validateConfig, DriveProperties, LogMaintenance, DataStore, etc.)




# ... (Other imports and functions: validateConfig, DriveProperties, LogMaintenance, DataStore, etc.)



logger = logging.getLogger(__name__)  # Set up logger

# ... (Your other classes and functions: TapeList, DataStore, RemoveDiskQueue, ToTapeQueue, etc.)

def manage_timer(prop, log):
    """
    Manages the timer, using fmdat.json for external communication.
    Deletes fmdat.json on expiration or reset.
    Returns True if the timer expired or was reset, False otherwise.
    """
    pauseInterval = float(prop.getInfo("FileManagerInterval")) * 60.0  # in seconds
    json_file_path = "views/fmdat.json"
    timer_expired = False  # Flag to indicate timer expiration or reset

    if not os.path.exists(json_file_path):
        create_fmdat(prop, log)

    wait_end_time = dt.datetime.now() + dt.timedelta(seconds=pauseInterval)

    while dt.datetime.now() < wait_end_time:
        try:
            with open(json_file_path, "r+") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    log.logIt(2, "manage_timer: Error decoding fmdat.json. Recreating the file.")
                    create_fmdat(prop, log)
                    continue

                if data.get("waitTry", 1) == 0:  # External reset detected
                    log.logIt(0, "manage_timer: Reset signal detected (waitTry = 0).")
                    timer_expired = True  # Set flag for external reset
                    break # Exit inner loop

                # Calculate remaining time
                remaining_time = int((wait_end_time - dt.datetime.now()).total_seconds())
                if remaining_time < 0:
                    remaining_time = 0

                # Update data for JSON file
                data["timer"] = str(dt.timedelta(seconds=remaining_time))
                data["waitTry"] = remaining_time // 10  # Update waitTry based on remaining time
                # Convert pauseInterval to HH:MM:SS for storage
                data["pauseInterval"] = str(dt.timedelta(seconds=pauseInterval))

                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f, fcntl.LOCK_UN)

        except (FileNotFoundError, Exception) as e:
            log.logIt(2, f"manage_timer: Error managing fmdat.json: {e}")

        time.sleep(10)  # Check every 10 seconds

    # Timer expired normally or was reset
    if timer_expired:
        try:
            if os.path.exists(json_file_path):
                os.remove(json_file_path)  # Remove the file to signal completion
        except:
            log.logIt(2, f"manage_timer: Error removing fmdat.json")
    else:
        if os.path.exists(json_file_path):
            try:
                with open(json_file_path, "r+") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    data = json.load(f)
                    data["status"] = "expired"
                    f.seek(0)
                    json.dump(data, f, indent=4)
                    f.truncate()
                    f.flush()
                    os.fsync(f.fileno())
                    fcntl.flock(f, fcntl.LOCK_UN)
                os.remove(json_file_path) # Remove the file to signal completion
            except:
                log.logIt(2, f"manage_timer: Error managing fmdat.json")

    return timer_expired

def create_fmdat(prop, log):
    """Creates the fmdat.json file with initial values."""
    pauseInterval = float(prop.getInfo("FileManagerInterval")) * 60.0  # in seconds
    try:
        with open("views/fmdat.json", "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            fmdat = {
                "timer": str(dt.timedelta(seconds=pauseInterval)),  # HH:MM:SS format
                "waitTry": int(pauseInterval / 10),  # Number of 10-second intervals
                "pauseInterval": str(dt.timedelta(seconds=pauseInterval)),  # Store as HH:MM:SS
                "status": "running"
            }
            json.dump(fmdat, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)
        log.logIt(0, f"create_fmdat: fmdat.json created with new countdown: {fmdat['timer']} (HH:MM:SS).")

    except Exception as e:
        log.logIt(2, f"create_fmdat: Error creating fmdat.json: {e}")

# ... (Your other classes and functions: TapeList, DataStore, RemoveDiskQueue, ToTapeQueue, etc.)



def main():
    configCheck = validateConfig()
    if configCheck["error"] == 0:
        prop = DriveProperties()
        if prop.getInfo("error") == 0:
            log = LogMaintenance(prop.getInfoAll())
            if prop.getInfo("error") == 0:
                loopApp = True
                startHour = int(prop.getInfo("FileManagerStart"))
                endHour = int(prop.getInfo("FileManagerEnd"))
                theClock = []

                # Initialize theClock with all True values
                for i in range(24):
                    theClock.append(True)

                if startHour == endHour == 0:
                    # Special case: StartTime and EndTime are both 0 (run continuously)
                    pass
                else:
                    # Normal case: Different StartTime and EndTime
                    startClock = startHour
                    startProcess = True
                    for i in range(24):
                        theClock[startClock] = startProcess
                        startClock = (startClock + 1) % 24  # Wrap around 24 hours
                        if startClock == endHour:
                            startProcess = False  # Stop setting to True when endHour is reached

                ds = DataStore(prop.getInfoAll())
                removal = RemoveDiskQueue(ds, log, prop.getInfo("TapeDrive"))
                tapeCopy = ToTapeQueue(ds, log, prop.getInfoAll())
                zeroFiles = ClearDisKQueue(ds, log, prop.getInfoAll())
                manage = TapeManagementQueue(ds, prop.getInfo("TapeDrive"))
                
                restoreFiles = RestoreManagementQueue(ds, prop.getInfo("TapeDrive"), prop.getInfo("RestoreAlternate"), prop.getInfo("VDiskMountPoint"), prop.getInfo("CopyBackRemoveDelay"), log, prop.getInfo("CacheLocation"))
                
                # restoreFiles = RestoreManagementQueue(ds, prop.getInfo("TapeDrive"), prop.getInfo("RestoreAlternate"), prop.getInfo("VDiskMountPoint"), prop.getInfo("CopyBackRemoveDelay"), log)                
                # restoreFiles = RestoreManagementQueue(ds, prop.getInfo("TapeDrive"), prop.getInfo("RestoreAlternate"), prop.getInfo("VDiskMountPoint"), prop.getInfo("CopyBackRemoveDelay"))

                log.logIt(0, "Starting File Manager")

                # --- Task list defined once ---
                # --- Remming out getTapeAttributes (house keeping) to speed demos
                task_list = [
                    ("removeDiskQueue", removal.processQueue),
                    ("toTapeQueue", tapeCopy.processQueue),
                    ("clearDiskQueue", zeroFiles.processQueue),
                    #("getTapeAttributes", getTapeAttributes),
                    ("tapeManagementQueue", manage.processQueue),
                    ("restoreManagementQueue", restoreFiles.processQueue),
                    ("runELArchive", runELArchive),
                    #("getTapeAttributes (second call)", getTapeAttributes)
                ]

                # Run tasks immediately at startup
                log.logIt(0, "main: Running initial File Manager tasks...")
                log.logIt(0, "main: **** File Manager tasks running! ****")

                for task_name, task_func in task_list:
                    start_time = time.time()
                    try:
                        task_func()  # No arguments needed for the initial run.
                        elapsed_time = time.time() - start_time
                        log.logIt(0, f"main: {task_name} completed in {elapsed_time:.2f} seconds")

                    except Exception as e:
                        log.logIt(2, f"main: Error in {task_name}: {e}")

                if fileManagerStarted(prop.getInfo("host"), prop.getInfo("user"), prop.getInfo("password"), prop.getInfo("database"))["error"] == 0:
                    while loopApp:
                        if fileManagerCheck(prop.getInfo("host"), prop.getInfo("user"), prop.getInfo("password"), prop.getInfo("database"))["error"] == 0:
                            log.logIt(0, "main: Starting File Manager task loop...")
                            try:
                                # --- Task Execution with Centralized Error Handling ---
                                log.logIt(0, "main: **** File Manager tasks running! ****")

                                hourOfDay = dt.datetime.now().hour
                                if theClock[hourOfDay]:
                                    for task_name, task_func in task_list:
                                        start_time = time.time()
                                        try:
                                            task_func() # No arguments needed
                                            elapsed_time = time.time() - start_time
                                            log.logIt(0, f"main: {task_name} completed in {elapsed_time:.2f} seconds")
                                        except Exception as e:
                                            log.logIt(2, f"main: Error in {task_name}: {e}")

                                # Call manage_timer (this will now block until the timer is complete)
                                print("main: Calling manage_timer (blocking until timer completion)")
                                manage_timer(prop, log)
                                print("main: manage_timer completed, proceeding with next loop.")

                            except Exception as e:
                                log.logIt(2, f"main: General error running tasks: {e}")

                        else:
                            loopApp = False
                        ds.disconnect()
                    else:
                        log.logIt(2, "Unable to find/open database")
                        print("Unable to find/open database")
                    log.logIt(0, "Stopping File Manager")
                    print("File Manager stopped!")
                else:
                    print(prop.getInfo("errormsg"))
        else:
            print(configCheck["errormsg"])

if __name__ == "__main__":
    main()


