import os, sys
import xlrd
import csv
import time
import pandas as pd
from certificates import processCertificates
import exceptions
import logging
import codecs
import shutil
import openpyxl as px
from xlrd import open_workbook
from openpyxl import load_workbook
import json
from pprint import pprint
import numpy as np
import re
import urllib, json
import requests
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('Logs/scan.log')
logger.addHandler(handler)


# creates a csv from excel file and returns its name
def csv_from_excel(file):

	global inputPath

	wb = xlrd.open_workbook(inputPath+file)
	sh = wb.sheet_by_name('Sheet1')
	name = os.path.splitext(file)[0] + '.csv'
	csv_file = open(inputPath+name, 'wb')
	wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

	for rownum in xrange(sh.nrows):
	    wr.writerow(sh.row_values(rownum))

	csv_file.close()
	return name

def getDataFile(files):

	data = None
	for file in files:
		name, ext = os.path.splitext(file)
		if ext == '.xlsx':
			print("Got excel file")
			data = csv_from_excel(file)
			break
	print(data)
	return data

# returns certificate count and a list of all the certificate files
def getCertificates(files):

	count = 0
	certificates = []
	for file in files:
		if os.path.splitext(file)[1] == '.pdf':
			certificates.append(file)
			count += 1
	return count, certificates

# checks if two certificates are there for same sid and returns only unique files
def checkDuplicates(certificates):

	ids = []
	uniqueCertificates = []
	for certificate in certificates:
		filename = os.path.splitext(certificate)[0]
		sid = filename.split('_')[5]
		if sid not in ids:
			ids.append(sid)
			uniqueCertificates.append(certificate)
		else:
			print 'Duplicate found'
			pass

	return uniqueCertificates

# adds Training center, SDMS Batch Id, SDMS Candidate Id, Starting Date, Assessment Date
def getData(batchData, detailed_data):

	for index,value in batchData['Concat'].iteritems():
		for record in detailed_data :
			if record['concatName'] == value.lower().replace(' ','').replace('.','') :
				batchData.loc[index, 'Training center'] = record['centreID']
				batchData.loc[index, 'SDMS Candidate Id'] = record['sdmsenrolmentNumber']
				batchData.loc[index, 'SDMS Batch Id'] = record['batchId']
				batchData.loc[index, 'Starting Date'] = record['batchStartDate']
				batchData.loc[index, 'Assessment Date'] = record['assessmentDate']
				batchData.loc[index, 'Subsidiary'] = record['subsidiary']
				batchData.loc[index, 'Location'] = record['location']
				break;


# mapping certificate files to sids in batch data
def mapCertificates(batchData, certificates, skip):

	for certificate in certificates:
		filename = os.path.splitext(certificate)[0]
		sid = filename.split('_')[5]
		if not skip.empty and int(sid) in skip['Sid'].values:
			skip.loc[skip['Sid']==int(sid), 'Certificate'] = certificate
			continue

		batchData.loc[batchData['Sid']==int(sid), 'Certificate'] = certificate

	logger.info('Mapped certificate files')

# function to check if value is nan
def isNan(num):
	return num != num

# moves all the certificates of batch to a new folder for processing and makes a folder called Error and moves it to output directory
def makeBatchFolder(batchData, notFound):

	global inputPath

	dstPath = inputPath + os.path.basename(os.path.normpath(inputPath)) + '_certificateFiles/' # not requried for folder creation
	if not os.path.exists(dstPath):
		os.makedirs(dstPath)
	for certificate in batchData['Certificate'].values:
		os.rename(inputPath+certificate, dstPath+certificate)

	errFolder = None
	if not notFound.empty:
		errFolder = inputPath + 'Error/'
		if not os.path.exists(errFolder):
			os.makedirs(errFolder)

		for certificate in notFound['Certificate'].values:
			os.rename(inputPath+certificate, errFolder+certificate)

	return dstPath, errFolder

def addLoc(batchData, folder) :
	for certificate in os.listdir(folder) :
		filename = os.path.splitext(certificate)[0]
		fileExt = os.path.splitext(certificate)[1]
		if fileExt == '.jpg':
			sid = filename.split('_')[5]
			subsidary , location = batchData.loc[batchData['Sid'] == int(sid), ['Subsidiary' , 'Location']].values[0]
			institute_name = subsidary + ", " + location
			img = Image.open(folder + "/" +certificate)
			draw = ImageDraw.Draw(img)
			font = ImageFont.truetype("arial.ttf", 28)
			if len(institute_name) <= 38 :
				draw.text((1240, 1195),institute_name,(0,0,0),font=font)
			else :
				draw.text((1240, 1165),institute_name[:37]+"-",(0,0,0),font=font)
				draw.text((1240, 1195),institute_name[37:],(0,0,0),font=font)
			img.save(folder + "/" +certificate)

# Posting certificates
def postCertificates(batchData, folder) :
	global inputPath
	#http://52.11.242.228:8080/api/public/saveSscCertificate?name=asdsad&dispatchName=15-07-2017
	url = 'http://52.11.242.228:8080/api/public/saveSscCertificate?'
	for certificate in os.listdir(folder) :
		filename = os.path.splitext(certificate)[0]
		fileExt = os.path.splitext(certificate)[1]
		if fileExt == '.jpg':
			sid = filename.split('_')[5]
			location , concat = batchData.loc[batchData['Sid'] == int(sid), ['Location' , 'Concat']].values[0]
			concat = concat.replace(' ','').replace('.','')
			data = {'name' : concat , 'dispatchName' : inputPath.replace("Input",'').replace("/",'')}
			files = {'file' : open(folder+'/'+certificate , 'rb')}
			try :
				x = requests.post(url , data=data , files=files)
				print (x)
			except :
				print (concat + " is not posted")

# make seperate folders for subsidiary->location
def seperateSubsidiaries(batchData, folder):

	try:
		certificatePaths = pd.DataFrame([], columns=['Concat','Path'])
		for certificate in os.listdir(folder):
			filename = os.path.splitext(certificate)[0]
			fileExt = os.path.splitext(certificate)[1]
			if fileExt == '.jpg':
				sid = filename.split('_')[5]
				location, subsidiary, concat = batchData.loc[batchData['Sid'] == int(sid), ['Location', 'Subsidiary', 'Concat']].values[0]

				if isNan(location) or isNan(subsidiary):
					continue

				subFolder = folder + '/' + str(subsidiary) + '/'
				if not os.path.exists(subFolder):
					os.makedirs(subFolder)

				# creating subsidiaries folder if it does not exists
				locFolder = subFolder + str(location) + '/'
				# creating location folder under subsidiary if it does not exists
				if not os.path.exists(locFolder):
					os.makedirs(locFolder)
				os.rename(folder + '/' + certificate, locFolder+certificate)
				# certificatePaths.loc[i,['Concat','Path']] = concat,locFolder+certificate
				# i += 1

		# filename = folder+'/certificatePaths.csv'
		# certificatePaths.to_csv(filename, index=False)
		logger.info('Certificates filtered into subsidiaries')
	except:
		logger.exception(sys.exc_info())



def makeCoveringLetters(data,path):
	summary_folder = path+"/summary"
	if not os.path.exists(summary_folder):
		os.makedirs(summary_folder)

	data['SDMS Candidate Id'] = data['SDMS Candidate Id'].astype(int)
	data['Training center'] = data['Training center'].astype(int)
	data['SDMS Batch Id'] = data['SDMS Batch Id'].astype(int)
	for sub in data['Subsidiary'].unique():
		if not os.path.exists(summary_folder+"/"+sub):
			os.makedirs(summary_folder+"/"+sub)

		locations = data.loc[data['Subsidiary'] == sub, 'Location'].unique()
		summaryFile = summary_folder + "/" + sub + '/' + sub + ' summary' + '.csv'
		summaryCol = ['Starting Date','Assessment Date','Location','Count']
		summary_data = pd.DataFrame(columns=summaryCol)
		for location in locations:
			filename = summary_folder + "/" + sub + '/' + str(sub) + ' ' + str(location) + '.csv'
			columns = ['Subsidiary', 'Training center', 'SDMS Candidate Id', 'SDMS Batch Id', 'Starting Date', 'Assessment Date', 'Course Name', 'Location', 'Name', 'Name Of Father/Husband']
			letterData = data.loc[(data['Subsidiary'] == sub) & (data['Location'] == location)]
			letterData.index += 1
			letterData.to_csv(filename, columns=columns, index=True, index_label='S.No')

			for sd in data.loc[(data['Subsidiary'] == sub) & (data['Location'] == location), 'Starting Date'].unique():
				batchData = data.loc[(data['Subsidiary'] == sub) & (data['Location'] == location) & (data['Starting Date'] == sd), summaryCol]
				batchData['Count'] = len(batchData)
				summary_data = summary_data.append(batchData.iloc[0], ignore_index=True)

		summary_data.index += 1
		summary_data['Count'] = summary_data['Count'].astype(int)
		summary_data.to_csv(summaryFile, columns=summaryCol, index_label='S.No')
		logger.info('Covering letters prepared')


def scan():

	try:
		global inputPath

		files = os.listdir(inputPath)
		batchDataFile = getDataFile(files)
		print("Got batch Data File")
		if not batchDataFile:
			raise ValueError('Data file not found')
			return

		logger.info('Got batch data file')
		numCertificates, certificates = getCertificates(files)

		batchData = pd.read_csv(inputPath+batchDataFile, low_memory=False)
		batchData['Concat'] = batchData['Name'] + batchData['Name Of Father/Husband']

		# verify count of number of certificates with number of rows in excel data file
		if not numCertificates == len(batchData):
			print 'Count mismatch'
			pass

		uniqueCertificates = checkDuplicates(certificates)
		detailed_data = []

		temp1 = ((batchData['Concat'].str.lower()).str.replace(' ','')).str.replace('.','')
		temp = list(temp1)

		if ((len(temp))%250) == 0 :
			limit = len(temp)/200
		else :
			limit = (len(temp)/200) + 1

		print("temp length : " , len(temp))
		for i in range (limit) :
			if i != (limit-1) :
				url="http://52.11.242.228:8080/api/public/getBySscConcatNames?names="+(",".join(temp[(i*200):((i+1)*200)]))
				response = urllib.urlopen(url)
				temp_detailed_data = json.loads(response.read())
				detailed_data += temp_detailed_data['sscs']
				print("temp_detailed_data : " , len(temp_detailed_data['sscs']))
			else :
				url="http://52.11.242.228:8080/api/public/getBySscConcatNames?names="+(",".join(temp[(i*200):]))
				#print(url)
				response = urllib.urlopen(url)
				temp_detailed_data = json.loads(response.read())
				detailed_data += temp_detailed_data['sscs']
				print("temp_detailed_data : " , len(temp_detailed_data['sscs']))

		detailed_data = pd.read_json(detailed_data , orient='records')
		#detailed_data = df1.to_json(orient='records')

		key = ((detailed_data.loc[:,'concatName'].str.lower()).str.replace(' ','')).str.replace('.','')

		"""detailed_key_values = []
		for dky in detailed_data :
			detailed_key_values.append(dky['concatName'])

		# comparing batch data with master data
		check = []
		notFound = pd.DataFrame([])
		print("Hello")
		for i in range (len(temp)) :
			if temp[i] in detailed_key_values :
				check.append(True)
			else :
				check.append(False)
				notFound = batchData.loc[i]
				print("in loop : " , notFound)"""

		# check = batchData['Concat'].isin(key.values)
		check = temp.isin(key.values)

		# number of found records
		checkSum = sum(check)

		print("checkSum : " , checkSum)
		# placeholder for records not found in master data

		# placeholder for records not found in master data
		notFound = pd.DataFrame([])
		if checkSum != len(batchData):
			notFound = batchData.loc[check == False, :]
			print 'Some certificates not found'
			pass

		if not notFound.empty:
			# drop rows in batchData which are present in notFound
			batchData = batchData.drop(notFound.index.values)

		print("Hello 1")
		getData(batchData, detailed_data)
		mapCertificates(batchData, uniqueCertificates, notFound)

		editedFolder = None
		if not batchData.empty:
			print (notFound)
			folder, errFolder = makeBatchFolder(batchData, notFound)
			#editedFolder = processCertificates(folder, errFolder, notFound)
			print("error Folder : " + errFolder)

		"""if editedFolder:
			addLoc(batchData, editedFolder)
			postCertificates(batchData, editedFolder)
			seperateSubsidiaries(batchData, editedFolder)
			makeCoveringLetters(batchData, editedFolder)
			return editedFolder
		else:
			print 'Edited folder not found'"""

	except:
		logger.exception(sys.exc_info())
		# print sys.exc_info()

if __name__ == '__main__':
	inputPath = sys.argv[1]
	start_time = time.time()
	scan()
	print("--- %s seconds ---" % (time.time() - start_time))
