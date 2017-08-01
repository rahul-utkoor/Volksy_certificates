from __future__ import print_function
import io
import os
import sys
import pip
import httplib2
import shlex , shutil
import subprocess as sp
from mimetypes import MimeTypes

try:
	import oauth2client
	from oauth2client import tools
	from apiclient import discovery
	from oauth2client import client
	from googleapiclient.errors import HttpError
	from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
except ImportError:
    print('goole-api-python-client is not installed. Try:')
    print('sudo pip install --upgrade google-api-python-client')
    sys.exit(1)

class Flag:
    auth_host_name = 'localhost'
    noauth_local_webserver = False
    auth_host_port = [8080, 8090]
    logging_level = 'ERROR'

try:
    import argparse
    flags = Flag()
except ImportError:
    flags = None

SCOPES = ['https://www.googleapis.com/auth/drive' , 'https://www.googleapis.com/auth/drive.file' , 'https://www.googleapis.com/auth/drive.metadata']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'GDrive'

def children_ids(service, folder_id):
  ids = []
  page_token = None
  while True:
    try:
      param = {}
      if page_token:
        param['pageToken'] = page_token
      children = service.children().list(folderId=folder_id, **param).execute()

      for child in children.get('items', []):
        ids.append(child['id'])
      page_token = children.get('nextPageToken')
      if not page_token:
        break
    except errors.HttpError, error:
      print ('An error occurred: %s' % error)
      break
  return ids

def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir , 'drive-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

def download(service , fid , batchName):
    request = service.files().get_media(fileId=fid)
    name = service.files().get(fileId=fid).execute()['name']
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

    f = open(batchName + "/" + name , 'wb')
    f.write(fh.getvalue())
    print('File downloaded')
    f.close()

def upload(path, parent_id=None):
    mime = MimeTypes()
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    file_metadata = {
        'name': os.path.basename(path)
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    media = MediaFileUpload(path,mimetype=mime.guess_type(os.path.basename(path))[0],resumable=True)
    try:
        file = service.files().create(body=file_metadata,media_body=media,fields='id').execute()
    except HttpError:
        print('corrupted file')
        pass


def createfolder(service2 , folder, fid):
	ids = {}
	for root, sub, files in os.walk(folder):
		par = os.path.dirname(root)
		file_metadata = {
			'name': os.path.basename(root),
			'mimeType': 'application/vnd.google-apps.folder'
		}
		if par in ids.keys():
			file_metadata['parents'] = [ids[par]]
		else:
			file_metadata['parents'] = [fid]
		file = service2.files().create(body=file_metadata,fields='id').execute()
		id = file.get('id')
		ids[root] = id
		for f in files:
			print ("*************")
			upload(root + '/' + f, id)

def main() :
	drive_folders = {"ToBeEdited" : "" , "Archive" : "" , "ToBePrinted" : ""}
	credentials = get_credentials()
	http = credentials.authorize(httplib2.Http())
	service2 = discovery.build('drive', 'v3', http=http)
	service1 = discovery.build('drive', 'v2', http=http)

	# Drive ID
	drive_folders["ToBeEdited"] = "0BymgpyLZUXukRUJFcHUwVUt4QVE"
	drive_folders["ToBePrinted"] = "0BymgpyLZUXukVFU3N1dkZ0dWNlE"

	child_ids = children_ids(service1 , drive_folders["ToBeEdited"])
	batch_name = ""
	for sub_id in child_ids :
		name = service2.files().get(fileId=sub_id).execute()['name']
		if name in drive_folders :
			drive_folders[name] = sub_id
		else :
			batch_name = name
			drive_folders[name] = sub_id

	child_ids = children_ids(service1 , drive_folders[batch_name])

	download_path = "script/Input/" + batch_name
	"""if os.path.exists(download_path) :
		shutil.rmtree(download_path)
	os.makedirs(download_path)

	print ("Downloading Started...")
	for c in range (len(child_ids)) :
		print ("...")
		try :
			download(service2 , child_ids[c] , download_path)
		except :
			print ("This one is excluded")
	print ("Downloading Completed...")"""

	print ("\nExecuting python shell")
	args = shlex.split("python scan.py " + download_path.replace("script/" , "") + "/")
	p = sp.Popen(args , cwd = r"script/")
	p.wait()
	print ("Python shell execution completed...")

	upload_path = "script/Output/" + batch_name + "_certificateFiles"

	print ("\nUploading to drive")
	if os.path.isdir(upload_path) :
		createfolder(service2 , upload_path , drive_folders["ToBePrinted"])

	print ("\nUploading Completed")

	print ("\nMoving batch folder in ToBeEdited to Archive")
	"""file = service2.files().get(fileId=drive_folders[batch_name] , fields='parents').execute()
	previous_parents = ",".join(file.get('parents'))
	file = service2.files().update(fileId=drive_folders[batch_name],
										addParents=drive_folders['Archive'],
										removeParents=previous_parents,
										fields='id, parents').execute()"""

if __name__ == '__main__' :
	main()
