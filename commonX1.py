#     15 Nov 2024 -- updated to ELSentry v2.0a beta
#      fmTimer project 10 Dec 2024
"""
New for P3 / Under construction / lives ptest02 for now / Now in Beta
In this version undere ptest02 we are updating MySQL code to comply with the new connector
updated the configProperties function (multiline JSON, name of decryptIT/decryptIt module
EchoLeaf Version 1.5c / p3

Application: common.py
Version: 1.1
Release Date: 01 Dec 2016
Description:  Common classes and functions used by other EchoLeaf programs.

Change History:
	17 Jan 2017 - Update to work with latest version of LTFS LE
	1 Oct 2019 -  Update to work with latest ltfs-LE  Leadm utility
	12 Nov 2019 -- Update so sort tapes in Volser Order
	5 June 2024 -- MySQL to p3 mysql-connector-python
	5 June 2024 -- updated cryptography from Crypto.Cipher to cryptography
    15 Nov 2024 -- updated to ELSentry v2.0a beta
    16 Jan 2025 -- updated filesearch()

Copyright EchoLeaf 2016. 2024
EchoLeaf Version 1.4c



Enhancing for P3 Sept 2024

"""
import logging
import os, sys
import datetime as dt
import subprocess
import json
# p2.7 import MySQLdb as mdb
# new
import mysql.connector as mdb
# new
# from Crypto.Cipher import AES
import fcntl

# New Crypto Modules
from cryptography.fernet import Fernet
# End New Crypto Modules

from binascii import hexlify, unhexlify
import base64
import smtplib


import threading
import time
import tempfile
# return contents of FileMoveLog
# added 06 June 2017

logging.basicConfig(filename='fm_reset_timer.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


def fileMoveLog():
    dict = {'error': 0, 'errormsg': '', 'data': []}
    info = DriveProperties().getInfoAll()
    if info["error"] == 0:
        try:
            arrayHeader = ['Transfer Date', 'Source', 'Destination', 'File Name']
            conn = mdb.connect(
                host=info["host"],
                user=info["user"],
                password=info["password"],
                database=info["database"]
            )
            cur = conn.cursor()
            cur.execute("DELETE FROM FileMoveLog WHERE EntryDate < (NOW() - INTERVAL 1 DAY)")
            conn.commit()
            cur.execute(
                "SELECT  EntryDate, Source, Destination, FileName FROM FileMoveLog \
                 ORDER BY EntryDate DESC  LIMIT 0, 100")
            rows = cur.fetchall()
            for row in rows:
                inProcess = 'No' if row[3] == 0 else 'Yes'
                dict['data'].append([str(row[0]), str(row[1]), str(row[2]), str(row[3])])
            cur.close()
            conn.close
            dict['header'] = arrayHeader
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': info['error'], 'errormsg': info['errormsg']}
    return dict


# folder copy info

def getFolderCopyInfo(dirId):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            dict = {"error": 0, "errormsg": "", "dir": [], "dirName": [], "files": [], "inLib": [], "outLib": []}
            dict['dir'].append(dirId)
            dirPos = 0
            while dirPos < len(dict['dir']):
                cur.execute("SELECT FullName FROM Directories WHERE DirectoryId = %s ", (dict['dir'][dirPos],))
                row = cur.fetchone()
                dict['dirName'].append(str(row[0]))
                cur.execute("SELECT DirectoryId FROM Directories WHERE ParentId = %s ", (dict['dir'][dirPos],))
                rows = cur.fetchall()
                for row in rows:
                    dict['dir'].append(int(row[0]))
                dirPos = dirPos + 1
            dirLen = len(dict['dir'])
            for i in range(dirLen):
                lastId = -1
                found = True
                hold = []
                cur.execute(
                    """SELECT Files.FileId, Files.FileName, LTOTapes.TapeUID, LTOTapes.InLibrary
                    FROM EchoLeaf.Files 
                    INNER JOIN EchoLeaf.TapeFiles ON (Files.FileId = TapeFiles.FileId) 
                    INNER JOIN EchoLeaf.LTOTapes ON (TapeFiles.TapeUID = LTOTapes.TapeUID) 
                    WHERE (Files.DirectoryId = %s) 
                    ORDER BY Files.FileName, Files.FileId, TapeFiles.DupSequence ASC, LTOTapes.InLibrary DESC""",
                    (dict['dir'][i],)
                )
                rows = cur.fetchall()
                for row in rows:
                    if lastId == int(row[0]):
                        if not found:
                            if int(row[3]) == 1:
                                dict['files'].append([int(row[0]), str(row[1]), str(row[2]), int(row[3]), i])
                                if str(row[2]) not in dict['inLib']:
                                    dict['inLib'].append(str(row[2]))
                                found = True
                            else:
                                hold = [int(row[0]), str(row[1]), str(row[2]), int(row[3]), i]
                                found = False
                    else:
                        if not found:
                            dict['files'].append(hold)
                            hold = []
                            if hold[2] not in dict['inLib']:
                                dict['outLib'].append(hold[2])
                        if int(row[3]) == 1:
                            dict['files'].append([int(row[0]), str(row[1]), str(row[2]), int(row[3]), i])
                            if str(row[2]) not in dict['inLib']:
                                dict['inLib'].append(str(row[2]))
                            found = True
                        else:
                            hold = [int(row[0]), str(row[1]), str(row[2]), int(row[3]), i]
                            found = False
                        lastId = int(row[0])
            cur.close()
            conn.close()
            if not found and len(hold) > 0:
                dict['files'].append(hold)
                if hold[2] not in dict['inLib']:
                    dict['outLib'].append(hold[2])
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)
    return dict
    
    

# return contents of toTapeQueue, file to be returned to disk
# added 28 Jan 2017
def toTapeQueue():
    dict = {'error': 0, 'errormsg': '', 'data': []}
    info = DriveProperties().getInfoAll()
    if info["error"] == 0:
        try:
            inProcess = 'Yes'
            arrayHeader = ['File', 'Date Queued', 'Archive to Tape', 'In Process', 'Issue']
            conn = mdb.connect(
                host=info["host"],
                user=info["user"],
                password=info["password"],
                database=info["database"]
            )
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 
                    FullFileName, 
                    DateQueued, 
                    DateToCopy, 
                    InProcess, 
                    IFNULL(Issue, ' ') AS Issue 
                FROM 
                    ToTapeQueue 
                ORDER BY 
                    FullFileName
                """              
                )
            rows = cur.fetchall()
            for row in rows:
                inProcess = 'No' if row[3] == 0 else 'Yes'
                dict['data'].append([str(row[0]), str(row[1]), str(row[2]), inProcess, str(row[4])])
            cur.close()
            conn.close
            dict['header'] = arrayHeader
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': info['error'], 'errormsg': info['errormsg']}
    return dict


# return contents of ClearDiskQueue, file to be returned to disk
# added 28 Jan 2017

def clearDiskQueue():
    dict = {'error': 0, 'errormsg': '', 'data': []}
    info = DriveProperties().getInfoAll()
    if info["error"] == 0:
        try:
            inProcess = 'Yes'
            arrayHeader = ['File', 'Date Queued', 'Date to Re-stub', 'In Process']
            conn = mdb.connect(
                host=info["host"],
                user=info["user"],
                password=info["password"],
                database=info["database"]
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT FullFileName, DateQueued, DateToRemove, InProcess FROM ClearDiskQueue  ORDER BY FullFileName")
            rows = cur.fetchall()
            for row in rows:
                inProcess = 'No' if row[3] == 0 else 'Yes'
                dict['data'].append([str(row[0]), str(row[1]), str(row[2]), inProcess])
            cur.close()
            conn.close
            dict['header'] = arrayHeader
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': info['error'], 'errormsg': info['errormsg']}
    return dict


# look for number of files to be moved to tape, fast track files
def fastTrackfiles():
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            dict = {"error": 0, "errormsg": "", 'filesTracked': 0}
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ToTapeQueue WHERE InProcess = 0")
            row = cur.fetchone()
            dict['filesTracked'] = str(row[0])
            if dict['filesTracked'] != "0":
                now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                inProcess = 0
                cur.execute("UPDATE ToTapeQueue SET DateToCopy = %s WHERE InProcess = %s", (now, inProcess))
                conn.commit()
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    return dict


# determine whether to use production or test virtual drive program
def getMountName():
    mountName = "mounttest"
    dict = {"error": 0, "errormsg": ""}
    if os.path.isfile("EchoLeaf.config"):
        configInfo = DriveProperties().getInfoAll()
        if configInfo["error"] == 0:
            if configInfo["ProductionEnv"] == "yes":
                mountName = "mount"
    return mountName


#file copy info / revised SQL


#cancel tape queue requests.
def cancelRestoreCmds(changes):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            status = 'Queued'
            dict = {'error': 0, 'errormsg': 'Selected restore management requests have been completed'}
            for item in changes['data']:
                cur.execute("DELETE FROM RestoreManagement WHERE RequestId = %s AND Status = %s", (item, status))
            conn.commit()
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': 1, 'errormsg': 'Problem removing restore management requests.'}
    return dict


# get retore  queue list
def restoreQueueList(queueStatus):
    dict = {'error': 0, 'errormsg': '', 'data': []}
    info = DriveProperties().getInfoAll()
    if info["error"] == 0:
        try:
            arrayHeader = ['File', 'Tape', 'Status', 'Status Date', 'Restore To', 'Result']

            conn = mdb.connect(
                host=info["host"],
                user=info["user"],
                password=info["password"],
                database=info["database"]
            )
            cur = conn.cursor()
            now = (dt.datetime.now() + dt.timedelta(days=-7)).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("DELETE FROM RestoreManagement WHERE StatusDate <  %s", (now,))
            conn.commit()
            if queueStatus == 'Queued':
                cur.execute(
                    "SELECT FileName, TapeUId, Status, StatusDate, RestoreTo, ResultText, RequestId FROM RestoreManagement WHERE Status = 'Queued' OR Status = 'In Progress' ORDER BY StatusDate DESC")
            else:
                cur.execute(
                    "SELECT FileName, TapeUId, Status, StatusDate, RestoreTo, ResultText, RequestId FROM RestoreManagement WHERE Status = %s ORDER BY StatusDate DESC",
                    (queueStatus,))
            rows = cur.fetchall()
            for row in rows:
                dict['data'].append(
                    [str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), int(row[6])])
            cur.close()
            conn.close
            dict['header'] = arrayHeader
            dict['VDiskMountPoint'] = info["VDiskMountPoint"]
            dict['RestoreAlternate'] = info["RestoreAlternate"]
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': info['error'], 'errormsg': info['errormsg']}
    return dict


#populate restore queue
def restoreFiles(fileList):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            dict = {'error': 0, 'errormsg': 'Requested files to restore  have been queued.'}
            status = 'Queued'
            resultText = " "
            conn.commit()
            entryDate = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for item in fileList:
                fileInfo = item.split('|')
                cur.execute(
                    "INSERT INTO RestoreManagement (FileId, FileName, TapeUID, RestoreTo, Status, EntryDate, StatusDate, ResultText)  VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
                    (int(fileInfo[0]), fileInfo[1], fileInfo[2], fileInfo[3], status, entryDate, entryDate, resultText))
            conn.commit()
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': 1, 'errormsg': 'Problem queuing file restore changes.'}
    return dict


#file copy info
def getFileCopyInfo(fileId):
    restore = 0
    directoryId = 0
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            dict = {"error": 0, "errormsg": "", }
            rowCount = 0
            cur = conn.cursor()
            cur.execute(
                "SELECT Files.FileName , LTOTapes.TapeUID, LTOTapes.InLibrary, DirectoryId FROM EchoLeaf.Files INNER JOIN EchoLeaf.TapeFiles ON (Files.FileId = TapeFiles.FileId) INNER JOIN EchoLeaf.LTOTapes ON (TapeFiles.TapeUID = LTOTapes.TapeUID) WHERE (Files.FileId = %s) ORDER BY TapeFiles.DupSequence ASC, LTOTapes.InLibrary DESC ",
                (fileId,))
            rows = cur.fetchall()
            found = False
            hold = []
            for row in rows:
                directoryId = int(row[3])
                if not found:
                    hold = [fileId, str(row[0]), str(row[1]), int(row[2]), restore]
                    found = True
                if int(row[2]) == 1:
                    dict['data'] = [fileId, str(row[0]), str(row[1]), int(row[2]), restore]
                    break
            if found and 'data' not in dict:
                dict['data'] = hold
            if 'data' in dict:
                cur.execute("SELECT FullName FROM Directories WHERE DirectoryId = %s ", (directoryId,))
                row = cur.fetchone()
                if row != None:
                    dict['data'][1] = str(row[0]) + "/" + dict['data'][1]
            if 'data' not in dict:
                dict["error"] = 2
                dict["errormsg"] = "File id is not properly entered in database.  Missing entry in TapeFile table."
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    return dict


#directory search
def directoryList(parentId):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            dict = {"error": 0, "errormsg": "", "data": []}
            rowCount = 0
            cur = conn.cursor()
            cur.execute("SELECT DirectoryID, DirectoryName FROM Directories WHERE ParentId = %s", (parentId,))
            rows = cur.fetchall()
            for row in rows:
                dict['data'].append([0, int(row[0]), str(row[1])])
            cur.execute("SELECT FileId, FileName, ArchiveDate FROM Files WHERE DirectoryId = %s", (parentId,))
            rows = cur.fetchall()
            for row in rows:
                ext = " "
                parts = str(row[1]).split('.')
                if len(parts) > 1:
                    ext = parts[len(parts) - 1]
                dict['data'].append([1, int(row[0]), ext, str(row[1]) + " (" + str(row[2]).split(' ')[0] + ")"])
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    return dict


# get cache free space
def cacheFreespace():
    dict = DriveProperties().getInfoAll()
    diskFree = -1
    if dict["error"] == 0:
        try:
            stat = os.statvfs(dict["CacheLocation"])
            diskFree = stat.f_frsize * stat.f_bavail / 1000000
        except:
            diskFree = -1
    return diskFree


#cancel tape queue requests.
def cancelTapeCmds(changes):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            status = 'Queued'
            dict = {'error': 0, 'errormsg': 'Selected tape management requests have been completed'}
            for item in changes['data']:
                cur.execute("DELETE FROM TapeManagement WHERE RequestId = %s AND Status = %s", (item, status))
            conn.commit()
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': 1, 'errormsg': 'Problem removing tape management requests.'}
    return dict


#get tape queue list
def tapeQueueList(queueStatus):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            arrayHeader = ['Tape', 'Request Type', 'Status', 'Request Status Date', 'Result']
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            now = (dt.datetime.now() + dt.timedelta(days=-7)).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("DELETE FROM TapeManagement WHERE StatusDate <  %s", (now,))
            conn.commit()
            if queueStatus == 'Queued':
                cur.execute(
                    "SELECT TapeId, RequestType, Status, StatusDate, ResultText, RequestId FROM TapeManagement WHERE Status = 'Queued' OR Status = 'In Progress' ORDER BY StatusDate DESC")
            else:
                cur.execute(
                    "SELECT TapeId, RequestType, Status, StatusDate, ResultText, RequestId  FROM TapeManagement WHERE Status = %s ORDER BY StatusDate DESC",
                    (queueStatus,))
            rows = cur.fetchall()
            dict = {'error': 0, 'errormsg': '', 'header': arrayHeader, 'data': []}
            for row in rows:
                dict['data'].append([str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), int(row[5])])
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    return dict


#populate tape queue
def addTapeCmdsToQueue(changes):
    dict = configProperties()
    if dict["error"] == 0:
        # New commands added for leadm
        tapeCmds = {'tape assign': 'Add to Library', 'tape format': 'Format', 'tape format -f': 'Forced Format',
                    'tape unassign': 'Remove', 'tape move -L ieslot': 'Move to I/O Slot', 'tape sync': 'Read Index',
                    'tape recover': 'Recover'}

        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            dict = {'error': 0, 'errormsg': 'Requested tape changes have been queued.'}
            status = 'Queued'
            origination = changes['source']
            for item in changes['data']:
                cur.execute("DELETE FROM TapeManagement WHERE TapeId = %s AND Status = %s", (item[1], status))
            conn.commit()
            resulText = ' '
            vdStatus = ' '
            entryDate = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for item in changes['data']:
                if changes['source'] == 'vd':
                    vdStatus = item[3]
                cur.execute(
                    "INSERT INTO TapeManagement (TapeId, Origination, VDStatus, LTFSStatus, Status, EntryDate, StatusDate, RequestType, RequestTypeShort, ResultText) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (item[1], origination, vdStatus, item[2], status, entryDate, entryDate, tapeCmds[item[0]], item[0],
                     resulText))
            conn.commit()
            cur.close()
            conn.close()
        except mdb.Error as err:
           dict["error"] = 1
           dict["errormsg"] = str(err)
           print(err)           
    else:
        dict = {'error': 1, 'errormsg': 'Problem queuing tape changes.'}
    return dict


# add Echo Leaf status column to library data
def addEchoLeafStatus():
    dict = ltfsAdminCmd('cartridge', 'leadm tape list -o xml')
    if dict["error"] == 0:
        # Volser Sort Begin
        newdict = dict
        newsort = sorted(newdict['data'],
                         key=lambda x: x[0])  # outputs ONLY the "data" list from dict, but in Volser order
        del dict["data"]  # delete the old data
        dict["data"] = newsort  #insert the sorted data
        # Volser Sort End
        dict2 = readVDTapeProperties()
        if dict2["error"] == 0:
            tapeList = []
            for info in dict2["data"]:
                tapeList.append(info[0])
            listLen = len(dict["data"])
            counter = 0
            for info in dict["data"]:
                try:
                    pos = tapeList.index(info[0])
                    dict["data"][counter].append(dict2["data"][pos][2])
                except:
                    dict["data"][counter].append('rogue')
                counter += 1
    return dict


# read editable data properties
def readVDTapeProperties():
    dict = configProperties()
    if dict["error"] == 0:
        try:
            arrayHeader = ['Tape Id', 'LTO Version', 'Status', 'Duplication Sequence', 'In Library']
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            cur.execute("SELECT TapeUID, TapeType, Status, DupSequence, Inlibrary FROM LTOTapes ORDER BY TapeUID")
            rows = cur.fetchall()
            dict = {'error': 0, 'errormsg': '', 'header': arrayHeader, 'data': []}
            rowCount = 0
            colLength = len(arrayHeader)
            for row in rows:
                dict['data'].append([])
                for num in range(0, colLength - 1):
                    dict['data'][rowCount].append(str(row[num]))
                dict['data'][rowCount].append('yes' if row[4] == 1 else 'no')
                rowCount += 1
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    return dict


# update changed table properties
def updateProperties(data):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            dict = {'error': 0, 'errormsg': 'Selected properties have been updated.'}
            for item in data:
                cur.execute("UPDATE Configuration SET PropertyValue = %s WHERE Property = %s", (item[1], item[0]))
            conn.commit()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    else:
        dict = {'error': 1, 'errormsg': 'Problems reading configuration file.'}
    return dict


# check if system is live before properties
def propertiesSystemLiveCheck(tableFields, arrayHeader, sortField):
    strMount = getMountName()
    dict = alive([strMount, 'filemanager'])
    if dict["error"] == 0:
        if dict[strMount][0] == 1 or dict['filemanager'][0] == 1:
            dict['error'] = 11
            dict[
                'errormsg'] = 'Both the File Manager and Virtual Drive need to be down to update the EchoLeaf system properties.'
        else:
            dict = readProperties(tableFields, arrayHeader, sortField)
    return dict


# read editable data properties 
def readProperties(tableFields, arrayHeader, sortField):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            cur.execute(
                "SELECT " + tableFields + " FROM Configuration WHERE Access = 1 ORDER BY " + tableFields.split(',')[
                    sortField])
            rows = cur.fetchall()
            dict = {'error': 0, 'errormsg': '', 'header': arrayHeader, 'data': []}
            rowCount = 0
            colLength = len(arrayHeader)
            for row in rows:
                dict['data'].append([])
                for num in range(0, colLength):
                    dict['data'][rowCount].append(str(row[num]))
                rowCount += 1
            cur.close()
            conn.close()
        except mdb.Error as err:
            dict["error"] = 1
            dict["errormsg"] = str(err)
            print(err)            
    return dict


#check if file manager up market exists
def fileManagerCheck():
    try:
        dict = configProperties()
        if dict["error"] == 0:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            dict = {"error": 1, "errormsg": "filemanager marker found"}
            cur = conn.cursor()
            cur.execute("SELECT PropertyValue FROM Configuration WHERE Property = 'FileManagerStatus'")
            row = cur.fetchone()
            if row == None:
                dict["error"] = 0
                dict["errormsg"] = "File Manager up marker does not exist."
            cur.close()
            conn.close()
    except:
        dict["error"] = 2
        dict["errormsg"] = "Error on filemanager marker check: " + str(sys.exc_info()[1])
    return dict


#remove file manager marker
def removeFileManagerMarker():
    try:
        dict = configProperties()
        if dict["error"] == 0:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            dict = {"error": 0, "errormsg": "File manager marker removed."}
            cur = conn.cursor()
            cur.execute("DELETE FROM Configuration WHERE Property = 'FileManagerStatus'")
            conn.commit()
            cur.close()
            conn.close()
    except:
        dict["error"] = 2
        dict["errormsg"] = "Error on File Manager marker delete: " + str(sys.exc_info()[1])
    return dict


# attemot to dismount virutal drive
def dismountVirtualDrive():
    strMount = getMountName()
    dict = alive([strMount])
    if dict["error"] == 0:
        if dict[strMount][0] == 1:
            info = DriveProperties().getInfoAll()
            dict["error"] = info["error"]
            dict["errormsg"] = info["errormsg"]
            if dict["error"] == 0:
                log = LogMaintenance(info)
                dict = folderInUse(info["VDiskMountPoint"], "Virtual drive is in use")
                if dict["error"] == 0:
                    try:
                        retcode = subprocess.call(["fusermount", "-u", info["VDiskMountPoint"]])
                        if retcode == 0:
                            dict = {'error': 0, 'errormsg': 'Dismount succeeded'}
                            log.logIt(1, "Dismount succeeded")
                        else:
                            dict = {'error': 1, 'errormsg': 'Dismount attempt failed'}
                            log.logIt(1, "Dismount attempt failed")

                    except:
                        dict = {'error': 2, 'errormsg': "Dismount failed: " + str(sys.exc_info()[1])}
                        log.logIt(2, "Dismount failed: " + str(sys.exc_info()[1]))
        else:
            dict = {'error': 1, 'errormsg': 'Virtual drive background task is down, nothing to dismount'}
    return dict


# submit background job
def submitApp(strApp):
    dict = {'error': 0, 'errmsg': ''}
    try:
        lines = subprocess.Popen(["nohup", "python", strApp, "&"])

    except:
        dict['error'] = 1
        dict['errormsg'] = str(sys.exc_info()[1])
    return dict


def validateConfigFilemanager():
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


# validation for starting virtual drive mount task
def validateConfigMount():
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


# validate login credentials
def validateLogin(userName, password):
#    print("Username")
#    sys.stdout.flush()
#    print(userName)
#    sys.stdout.flush()
#    print("password")
#    sys.stdout.flush()
#    print(password)
#    sys.stdout.flush()
    info = configProperties()
#    print(info)
#    sys.stdout.flush()
    dict = {}
    dict["error"] = info["error"]
    dict["errormsg"] = info["errormsg"]
    if info["error"] == 0:
        if info["sysadmin"] == userName and info["sysadminpassword"] == password:
            dict = {"error": 0, "errormsg": "valid com credentials"}
        else:
            dict = {"error": 2, "errormsg": "invalid credentials"}
    return dict


# get properties in configuration file
# revised for new EchoLeaf.config and p3

def configProperties():
    info = {'error': 1, 'errormsg': 'Unable to open configuration file'}
    key = load_key()
    
    try:
        with open("EchoLeaf.config", "r") as configuration:
             info = json.load(configuration)  # Parse the JSON object          
        info["sysadminpassword"] = decryptIT(info["sysadminpassword"],key)
        info["password"] = decryptIT(info["password"],key)
        info["error"] = 0
        info["errormsg"] = ''
    except:
        info["error"] = 2
        info["errormsg"] = str(sys.exc_info()[1])
     
    return info



"""
old
changes:  1) Read multiline json  2) decryptIt now decryptIT  (case)

def configProperties():
    info = {'error': 1, 'errormsg': 'Unable to open configuration file'}
    try:
        with open("EchoLeaf.config", "r") as configuration:
            info = json.loads(configuration.readline())
        info["sysadminpassword"] = decryptIt(info["sysadminpassword"])
        info["password"] = decryptIt(info["password"])
        info["error"] = 0
        info["errormsg"] = ''
    except:
        info["error"] = 2
        info["errormsg"] = str(sys.exc_info()[1])
    return info

"""
# open config file get to get virtual drive properties
class DriveProperties:

    # Extracts properities from configuration table
    def __init__(self):
        self.info = configProperties()
        try:
            with open("EchoLeaf.config", "r") as configuration:
                self.info = json.load(configuration)
                
            key = load_key()    
            self.info["sysadminpassword"] = decryptIT(self.info["sysadminpassword"],  key)
            self.info["password"] = decryptIT(self.info["password"],  key)      
            self.info["error"] = 0
            self.info["errormsg"] = ''
            
            # print("Decrypted info:", self.info)  # Print the decrypted info
            
        except:
            self.info["error"] = 2
            self.info["errormsg"] = str(sys.exc_info()[1])

        if self.info["error"] == 0:
            try:
                # print("Attempting Database Connection . . . ")
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
                programPath = os.path.abspath('')
            except:
                self.info["error"] = 2
                self.info["errormsg"] = str(sys.exc_info()[1])

        programPath = os.path.abspath('')
        self.info["programFolder"] = programPath
        self.info["logFolder"] = os.path.join(programPath, "logfiles")

    def getInfo(self, infoProperty):
        """ Return value of provided property """
        infoValue = ''
        if self.info.has_key(infoProperty):
            infoValue = self.info[infoProperty]
        return infoValue

    def getInfoAll(self):
        """ return all properties in dictionary """
        return self.info

    # discovered error below.  def within class needs self -- probably a bug for years
    # updated June 5, 2024

    def dbExists(self):
        return True if self.info["error"] == 0 else False


# check if mount point or folder is in use
def folderInUse(strFolder, strError):
    dict = {'error': 0, 'errormsg': ''}
    try:
        lines = os.popen('lsof ' + strFolder).readlines()
        if len(lines) > 1:
            dict["error"] = 1
            dict["errormsg"] = strError
    except:
        dict['error'] = 2
        dict['errormsg'] = str(sys.exc_info()[1])
    return dict


# create and write to log file
class LogMaintenance:
    """ creates and allows endtried to log file """

    def __init__(self, info):
        self.info = info
        self.mailAvailable = False
        self.logCounter = 0
        if self.info["error"] == 0:
            if self.info["MailFrom"] != "none" and self.info["AdminEmail1"] != "none":
                self.mailAvailable = True

    def __logFullFileName(self):
        return os.path.join(self.info["logFolder"], "ex" + dt.datetime.now().strftime('%Y%m%d') + ".txt")

    def logIt(self, infoType, issue):
        try:
            entryType = ["info", "warn", "error"]
            self.logCounter = self.logCounter + 1
            with open(self.__logFullFileName(), "a") as logFile:
                logFile.write('%s|vitualdrive|%s|%s\n' % (
                    dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), entryType[infoType], issue))
        except:
            print("Error writing to error log: " + str(sys.exc_info()[1]))

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
Subject: %scd 

%s
""" % (self.info["MailFrom"], ", ".join(mailTo), subject, body)
                smtpObj.sendmail(self.info["MailFrom"], mailTo, message)
                smtpObj.quit()
            except:
                self.logIt(0, "on SendMail: " + str(sys.exc_info()[1]))


# checks if EchoLeaf background tasks are currently running
# returns dictionary of task, status and when it was started
def alive(tasks):
    dict = {'error': 0, 'errormsg': ''}
    linecount = 0
    format1 = '%m/%d/%y %H:%M:%S'
    format2 = '%a %b %d %H:%M:%S %Y'
    try:
        lines = os.popen('ps aux').readlines()
        for task in tasks:
            dict[task] = [0, 'Down', '&nbsp;']
            for line in lines:
                if line.find("python " + task + ".py") >= 0:
                    linecount += 1
                    dict[task][0] = 1
                    dict[task][1] = 'Up'
                    startDate = os.popen('ps -olstart= ' + line.split()[1]).readlines()[0].rstrip()
                    startDateTime = dt.datetime.strptime(startDate, format2)
                    endDateTime = dt.datetime.strptime(dt.datetime.now().strftime(format1), format1)
                    dict[task][2] = str(endDateTime - startDateTime)
                    break
        if linecount == 0 and len(lines) < 4:
            dict['error'] = 2
            dict['errormsg'] = 'Problem with ps aux command'
            for task in tasks:
                dict[task] = [2, 'Unknown', '&nbsp;']

    except:
        dict['error'] = 1
        dict['errormsg'] = str(sys.exc_info()[1])
        for task in tasks:
            dict[task] = [2, 'Unknown', '&nbsp;']
    return dict


# encrypts a clear text string
# OLD p2 crypto code

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


# decrypts an encoded string
def decryptIt(strEncoded):
    BLOCK_SIZE = 16
    PADDING = '{'
    pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
    DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
    key = "53f7d42cbf4d485b781f818fb9e1cd11"
    cipher = AES.new(unhexlify(key))
    return DecodeAES(cipher, strEncoded)


# system reset check, user has to supply reset password.  returns True or False
def resetPasswordCheck(strText):
    result = False
    if encryptIt(strText) == "X39zVo00ek0OuaxkLj7Grw==":
        result = True
    return result

# Old p2 crypto code
"""


# New code for p3 using cryptography module
# New code for p3 using cryptography module

#def encrypt_It(str_Text):

"""Encrypts a string using AES-128 in CBC mode with PKCS#7 padding.

    Args:
        str_Text (str): The string to encrypt.

    Returns:
        bytes: The base64-encoded ciphertext.
"""

# Note Load_key() and generate_key() are new in P3 upgrade
# We are moving the key to an external file





def load_key():
    """Loads the encryption key from ElkeSummer.dat."""
    try:
        with open("ElkeSummer.dat", "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        generate_key()
        return load_key()

#old 

def generate_key():
    """Generates a new encryption key and saves it to ElkeSummer.dat."""
    key = Fernet.generate_key()
    with open("ElkeSummer.dat", "wb") as key_file:
        key_file.write(key)

def encryptIT(password, key):
    """Encrypts a password using the provided key."""
    f = Fernet(key)
    encrypted_password = f.encrypt(password.encode())
    return encrypted_password.decode()


def decryptIT(encrypted_password_bytes, key):
 #Decrypts an encrypted password (in bytes) using the provided key."""
    f = Fernet(key)
    decrypted_password = f.decrypt(encrypted_password_bytes)  # Directly decrypt the bytes
    return decrypted_password.decode()  # Decode the decrypted bytes to a string


def reset_Password_Check(str_text):
    """Checks if the provided string matches a predetermined encrypted value.
    Args:
        str_Text (str): The string to check.
    Returns:
        bool: True if the string matches, False otherwise.
    """

    try:
        with open("NewPassPhrase.dat", "r") as f:
            expected_encrypted = f.read().strip() 
    except FileNotFoundError:
        print("Error: 'NewPassPhrase.dat' file not found. Please ensure it exists.")
        return False 

    return encrypt_IT(str_text) == expected_encrypted




# End New code for p3 using cryptography module
# End New code for p3 using cryptography module

# ltfsadmin handling table output
def ltfsAdminCmd(objectType, adminCmd):
    dict = {'error': 0, 'errmsg': ''}
    objectBreakOut = '<object type="' + objectType + '" id="'
    attrBreakout = '<attribute name="'
    valueBreakout = '<value>'
    noValue = '<value/>'
    foundObject = False
    firstRow = False
    rowCount = 0
    try:
        lines = os.popen(adminCmd).readlines()
        lineCount = len(lines)
        linePos = 0
        dict["header"] = []
        dict["header"].append(objectType.replace("_", " ").title())
        dict["data"] = []
        while (linePos < lineCount):
            if lines[linePos].find(objectBreakOut) >= 0:
                dict["data"].append([])
                dict["data"][rowCount].append(lines[linePos].split(objectBreakOut)[1].split('">')[0])
                linePos += 1
                while (linePos < lineCount):
                    if lines[linePos].find(attrBreakout) >= 0:
                        if rowCount == 0:
                            dict["header"].append(
                                lines[linePos].split(attrBreakout)[1].split('">')[0].replace("_", " ").title())
                        linePos += 1
                        if lines[linePos].find(noValue) >= 0:
                            dict["data"][rowCount].append("")
                        else:
                            dict["data"][rowCount].append(lines[linePos].split(valueBreakout)[1].split('</value>')[0])
                        linePos += 2
                    else:
                        break
                rowCount += 1
            else:
                linePos += 1
        if rowCount == 0:
            dict["error"] = 2
            dict["errmsg"] = "Unable to find cartridge attributes."
    except:
        dict['error'] = 1
        dict['errormsg'] = str(sys.exc_info()[1])
    return dict


# update changed table properties
def updateProperties(data):
    dict = configProperties()
    if dict["error"] == 0:
        try:
            conn = mdb.connect(
                host=dict["host"],
                user=dict["user"],
                password=dict["password"],
                database=dict["database"]
            )
            cur = conn.cursor()
            dict = {'error': 0, 'errormsg': 'Selected properties have been updated.'}
            for item in data:
                cur.execute("UPDATE Configuration SET PropertyValue = %s WHERE Property = %s", (item[1], item[0]))
            conn.commit()
        except:
            dict["error"] = 1
            dict["errormsg"] = str(sys.exc_info()[1])
    else:
        dict = {'error': 1, 'errormsg': 'Problems reading configuration file.'}
    return dict


# checks if File Manager is running
# Simple Test

def filemanageralive():
    filemanageryes = "Down"
    linecount = -1
    lines = os.popen('ps aux').readlines()
    for line in lines:
        linecount = linecount + 1
        # test        print line
        if line.find("python filemanager.py &") >= 0:
            #            print line
            filemanageryes = "Up"
        elif linecount == 0 and len(lines) < 4:
            filemanageryes = "Error"  #os error
    return filemanageryes


# Checks if a particular tapeID is listed as WRITABLE from LTFS

def isThisTapeWritable(TapeID):
    testMyTapeID = TapeID
    objectType = 'cartridge'
    adminCmd = 'leadm tape list -o xml'
    isTapeWritable = False

    dict = ltfsAdminCmd(objectType, adminCmd)

    # dict is the data object derived from the leadm tape list command
    # We can test any value based on a particular TapeUID
    # In this case we are screening for a WRITABLE tape (the old ValidLTFS) to determine Active Tape

    for data in dict['data']:
        if data[1] == "WRITABLE" and data[0] == testMyTapeID:
            isTapeWritable = True

    return isTapeWritable


# FMTimer stuff

#class FMInterrupt(Exception):  # Define the custom exception
#$    pass

# Configure logging (old)
# logging.basicConfig(filename='fm_reset_timer.log', level=logging.DEBUG, 
#                      format='%(asctime)s - %(levelname)s - %(message)s')

# Configure logging with a specific logger name
logger = logging.getLogger("filemanager_reset")  # Create a dedicated logger
logger.setLevel(logging.DEBUG)

# Create a file handler and set the logging level
handler = logging.FileHandler('fm_reset_timer.log')
handler.setLevel(logging.DEBUG)

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)



# Configure logging (you can adjust the logger name and file as needed)
logger = logging.getLogger("filemanager_reset")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('fm_reset_timer.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


logger = logging.getLogger(__name__)



def resetFMTimer(json_file_path="views/fmdat.json"):
    """Resets the wait timer in fmdat.json by setting 'waitTry' to 0."""
    try:
        with open(json_file_path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                data = json.load(f)
                data["waitTry"] = 0
                data["status"] = "expired"
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                f.flush()
                os.fsync(f.fileno())
                logger.info("Successfully set waitTry to 0 in %s", json_file_path)
                return 1
            except json.JSONDecodeError:
                logger.error("Error decoding JSON from %s. File might be corrupted.", json_file_path)
                return -1
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except FileNotFoundError:
        logger.warning("%s not found.", json_file_path)
        return 0
    except Exception as e:
        logger.exception("An unexpected error of type %s occurred: %s", type(e).__name__, e)
        return -1
        


# generates a target demo structure for a demo.

def generateDemo1(orgName, targetDirName):
    """
    Generates a demonstration folder structure with test files.

    Args:
        orgName (str): The name of the organization (top-level folder).
        targetDirName (str): The path to the directory where the 
                             structure will be created.
    """

    # Create the main company directory (if it doesn't exist)
    company_dir = os.path.join(targetDirName, orgName)
    try:
        os.makedirs(company_dir)
        print(f"Created directory: {company_dir}")
    except FileExistsError:
        print(f"Directory already exists: {company_dir}")

    # Define the department folders with their subfolders
    departments = {
        "Personnel": ["Employee_Info", "Payroll", "Time_Sheets", "Onboarding", "Training"],
        "Finance": ["General_Ledger", "Payables", "Cash", "Financial_Reports", "Taxes"],
        "Customers": ["CRM", "Sales_Info", "Marketing", "Help_Desk", "Customer_Feedback"],
        "Factory": ["Production", "Warehouse", "Supply_Chain", "Deliveries", "Quality_Control"],
        "Vault": ["Documents", "Product_Content", "Media_Archive", "Code_Base", "Data"]
    }

    # Create the department and subfolders (if they don't exist)
    for dept_name, subfolders in departments.items():
        dept_dir = os.path.join(company_dir, dept_name)
        try:
            os.makedirs(dept_dir)
            print(f"Created directory: {dept_dir}")
        except FileExistsError:
            print(f"Directory already exists: {dept_dir}")
        for subfolder in subfolders:
            subfolder_dir = os.path.join(dept_dir, subfolder)
            try:
                os.makedirs(subfolder_dir)
                print(f"Created directory: {subfolder_dir}")
            except FileExistsError:
                print(f"Directory already exists: {subfolder_dir}")

    # Function to create a test file of a specified size
    def create_test_file(filepath, size_in_gb):
        """Creates a file with the given filepath and size (in GB)."""
        with open(filepath, "wb") as f:
            f.seek(int(size_in_gb * 1024 * 1024 * 1024 / 4) - 1)
            # f.seek(size_in_gb * 1024 * 1024 * 1024 - 1)  # Seek to the desired size - 1 byte
            f.write(b"\0")  # Write a single byte to ensure the file size

    # Create test files in each subfolder
    for dept_name, subfolders in departments.items():
        dept_dir = os.path.join(company_dir, dept_name)
        for subfolder in subfolders:
            subfolder_dir = os.path.join(dept_dir, subfolder)

            # Create two test files
            create_test_file(os.path.join(subfolder_dir, f"{subfolder}_T1"), 1)
            create_test_file(os.path.join(subfolder_dir, f"{subfolder}_T2"), 1)

    print("Test files created successfully.")


import os
import datetime
import json
import logging
import string
import fcntl

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_recent_logs(log_dir_name="logfiles", views_dir_name="views", json_filename="fmlog.json", max_entries=20, max_message_length=80):
    """
    Processes the most recent log file, extracts entries, formats them, and saves them to a JSON file.
    Uses file locking and more robust error handling.

    Returns:
        "success": If the log file was processed and JSON data was written successfully.
        "log_file_not_found": If the log file does not exist.
        "error_reading_log": If there was an error reading the log file.
        "error_parsing_log": If there was an error parsing a log entry.
        "error_writing_json": If there was an error writing to the JSON file.
        "error_creating_json": If there is an error creating an empty json file.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, log_dir_name)
    json_output_path = os.path.join(script_dir, views_dir_name, json_filename)

    today = datetime.date.today()
    log_filename = f"ex{today.strftime('%Y%m%d')}.txt"
    log_filepath = os.path.join(log_dir, log_filename)

    logger.info(f"Log file path: {log_filepath}")

    if not os.path.exists(log_filepath):
        logging.warning(f"Log file not found: {log_filepath}")
        try:
            os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
            with open(json_output_path, "w") as f:
                json.dump([], f)
                return "success"
        except OSError as e:
            logger.error(f"Error creating empty JSON file: {e}")
            return "error_creating_json"
        

    try:
        with open(log_filepath, "r") as f:
            lines = f.readlines()
        logger.info(f"Read {len(lines)} lines from log file")
    except FileNotFoundError:
        logger.error(f"Error: Log file not found: {log_filepath}")
        return "log_file_not_found"
    except IOError as e:
        logger.error(f"Error reading log file {log_filepath}: {e}")
        return "error_reading_log"

    recent_entries = lines[-max_entries:]
    logger.info(f"Recent entries: {recent_entries}")

    json_data = []
    for i, entry in enumerate(recent_entries):
        try:
            first_pipe_index = entry.find("|")
            message = entry[first_pipe_index + 1:].strip()

            # Sanitize: Remove control characters
            message = ''.join(char for char in message if char in string.printable)

            # Truncate
            if len(message) > max_message_length:
                message = message[:max_message_length] + "..."

            json_data.append({"entryNumber": i + 1, "message": message})
        except Exception as e:
            logger.error(f"Error parsing log entry: {entry} - Error: {e}")
            return "error_parsing_log"

    logger.info(f"JSON data: {json_data}")

    try:
        with open(json_output_path, "r+") as f:  # Open for reading and writing
            fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
            try:
                f.seek(0)  # Go to the beginning of the file
                f.truncate(0)
                json.dump(json_data, f, indent=4)
                f.flush()  # Flush the buffer
                os.fsync(f.fileno())  # Ensure data is written to disk
                logger.info(f"Successfully wrote JSON data to {json_output_path}")
            except Exception as e:
                logger.exception(f"An unexpected error occurred while writing to {json_output_path}: {e}")
                return "error_writing_json"
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)  # Unlock
    except (IOError, OSError) as e:
        logger.error(f"Error writing to JSON file {json_output_path}: {e}")
        return "error_writing_json"

    return "success"


def resetFMTimer(json_file_path="views/fmdat.json"):
    """Resets the wait timer in fmdat.json by setting 'waitTry' to 0."""
    try:
        with open(json_file_path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                data = json.load(f)
                data["waitTry"] = 0
                data["status"] = "expired"
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
                f.flush()
                os.fsync(f.fileno())
                logger.info("Successfully set waitTry to 0 in %s", json_file_path)
                return 1
            except json.JSONDecodeError:
                logger.error("Error decoding JSON from %s. File might be corrupted.", json_file_path)
                return -1
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except FileNotFoundError:
        logger.warning("%s not found.", json_file_path)
        return 0
    except Exception as e:
        logger.exception("An unexpected error of type %s occurred: %s", type(e).__name__, e)
        return -1


# filesearch with dates

import mysql.connector as mdb
from datetime import datetime

def fileSearchDates(searchCriteria):
    """
    Searches for files based on filename, start date, and end date,
    returning data compatible with validateFileSearch.
    """
    result = {"error": 0, "errormsg": "", "data": []}
    conn = None
    cursor = None

    try:
        conn = mdb.connect(
            host=configProperties()["host"],
            user=configProperties()["user"],
            password=configProperties()["password"],
            database=configProperties()["database"]
        )
        cursor = conn.cursor()

        where_clauses = []
        parameters = []

        if searchCriteria['filename']:
            where_clauses.append("Files.FileName LIKE %s")
            parameters.append('%' + searchCriteria['filename'] + '%')
        if searchCriteria['start_date']:
            where_clauses.append("Files.ArchiveDate >= %s")
            parameters.append(searchCriteria['start_date'])
        if searchCriteria['end_date']:
            where_clauses.append("Files.ArchiveDate <= %s")
            parameters.append(searchCriteria['end_date'])

        sql = """
            SELECT Files.FileId, Files.FileName, LTOTapes.TapeUID, LTOTapes.InLibrary,
                   CONCAT(Directories.FullName, '/', Files.FileName) as FullFilePath, Files.ArchiveDate
            FROM Files
            INNER JOIN Directories ON (Files.DirectoryId = Directories.DirectoryId)
            INNER JOIN TapeFiles ON (Files.FileId = TapeFiles.FileId)
            INNER JOIN LTOTapes ON (TapeFiles.TapeUID = LTOTapes.TapeUID)
        """  # Construct the full file path
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY Files.FileName ASC, Directories.FullName ASC, LTOTapes.InLibrary DESC"

        cursor.execute(sql, tuple(parameters))
        rows = cursor.fetchall()

        holdPrior = [0, 0, "xxxxx"]
        for row in rows:
            file_id, file_name, tape_uid, in_library, full_file_path, archive_date = row  # Unpack *correct* number of values
            if not (holdPrior[1] == 1 and int(file_id) == holdPrior[0] and str(full_file_path) == holdPrior[2]):

                result['data'].append([
                    int(file_id),  # FileId
                    str(file_name),  # FileName
                    str(tape_uid),  # TapeUID
                    int(in_library),  # InLibrary (0 or 1)
                    str(full_file_path),  # FullFilePath (Directory AND Filename)
                    str(archive_date).split(' ')[0],  # ArchiveDate (YYYY-MM-DD)
                ])
                holdPrior = [int(file_id), int(in_library), str(full_file_path)] # file_id, in_library, full_file_path


    except mdb.Error as err:
        result["error"] = 1
        result["errormsg"] = str(err)
        print(f"Database error: {err}")  # Or use logging
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return result


def fileSearch(searchCriteria):
    """
    Searches for files based on filename and directory,
    returning data compatible with validateFileSearch.
    """
    result = {"error": 0, "errormsg": "", "data": []}
    conn = None
    cursor = None

    try:
        conn = mdb.connect(
            host=configProperties()["host"],
            user=configProperties()["user"],
            password=configProperties()["password"],
            database=configProperties()["database"]
        )
        cursor = conn.cursor()

        where_clauses = []
        parameters = []

        if searchCriteria['file']:
            where_clauses.append("Files.FileName LIKE %s")
            parameters.append('%' + searchCriteria['file'] + '%')
        if searchCriteria['directory']:
            where_clauses.append("Directories.FullName LIKE %s")
            parameters.append('%' + searchCriteria['directory'] + '%')

        sql = """
            SELECT Files.FileId, Files.FileName, LTOTapes.TapeUID, LTOTapes.InLibrary,
                   CONCAT(Directories.FullName, '/', Files.FileName) as FullFilePath, Files.ArchiveDate
            FROM Files
            INNER JOIN Directories ON (Files.DirectoryId = Directories.DirectoryId)
            INNER JOIN TapeFiles ON (Files.FileId = TapeFiles.FileId)
            INNER JOIN LTOTapes ON (TapeFiles.TapeUID = LTOTapes.TapeUID)
        """  # Construct the full file path.
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY Files.FileName ASC, Directories.FullName ASC, LTOTapes.InLibrary DESC" # Order by clause

        cursor.execute(sql, tuple(parameters))
        rows = cursor.fetchall()

        holdPrior = [0, 0, "xxxxx"]
        for row in rows:
            file_id, file_name, tape_uid, in_library, full_file_path, archive_date = row  # Unpack correctly
            if not (holdPrior[1] == 1 and int(file_id) == holdPrior[0] and str(full_file_path) == holdPrior[2]):
                result['data'].append([
                    int(file_id),       # FileId
                    str(file_name),    # FileName
                    str(tape_uid),    # TapeUID
                    int(in_library),   # InLibrary
                    str(full_file_path),  # FullFilePath (Directory AND Filename)
                    str(archive_date).split(' ')[0]  # ArchiveDate (YYYY-MM-DD)
                ])
                holdPrior = [int(file_id), int(in_library), str(full_file_path)]  # file_id, in_library, full_file_path

    except mdb.Error as err:
        result["error"] = 1
        result["errormsg"] = str(err)
        print(f"Database error: {err}")  # Use consistent logging
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return result
