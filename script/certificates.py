#50 - 1000
#8 - 345
from PIL import Image as Img
from wand.image import Image
import os,sys,shutil
import multiprocessing as mp
import exceptions
from timeit import default_timer as timer
import logging
import threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('Logs/certificate.log')
logger.addHandler(handler)

workingDIR = ''
# workingDIR = './utils/script/'

def editCertificate(inputPath, file, example):

	global res
	global size
	global outputPath

	logger.info('Editing certificate:' + inputPath + file)

	try :
		with Image(filename=inputPath + file, resolution=res) as img:
			img.save(filename=outputPath+'/temp_' + os.path.splitext(file)[0] + '.jpg')

		with Image(filename=outputPath+'/temp_' + os.path.splitext(file)[0] + '.jpg', resolution=res) as img:
			img.resize(size[0],size[1])
			img.save(filename=outputPath+'/final_' + os.path.splitext(file)[0] + '.jpg')

		os.remove(outputPath+'/temp_' + os.path.splitext(file)[0] + '.jpg')

		base = Img.open(outputPath + '/final_' + os.path.splitext(file)[0] + '.jpg')

		box = (1010,1100,1750,1516)
		roi = example.crop(box)
		# roi.show()
		base.paste(roi, box)

		name = file.split('.')[0]

		newFile = outputPath + '/' +  name + '.jpg'
		base.save(newFile)
		logger.info('Certificate edited:' + inputPath + file)

		os.remove(outputPath + '/final_' + os.path.splitext(file)[0] + '.jpg')

	except:
		logger.exception(sys.exc_info())
		# print sys.exc_info()

	return 1

def thread_func(inputPath , outputPath , start_count , end_count) :
	example_img = Img.open(outputPath+'/final_ex.jpg')
	files = os.listdir(inputPath)
	print("Hello from thread : " , start_count/len(files))
	for file in range (start_count , end_count):
		if not files[file].startswith('.'):
			editCertificate(inputPath, files[file], example_img)

def processCertificates(inputPath, errFolder, notFound):

	global res
	global size
	global outputPath

	res = 300
	size = (2339,1653)

	logger.info('Received Folder to edit:' + inputPath)

	try:
		# inputPath = sys.argv[1]

		# print inputPath

		if not os.path.exists(inputPath):
			print 'Invalid Input folder path'
		else:
			outputFolder = os.path.basename(os.path.normpath(inputPath))
			# outputPath = workingDIR + 'Output/' + outputFolder
			outputPath = 'Output/' + outputFolder

			if not os.path.exists(outputPath):
				os.makedirs(outputPath)
				logger.info('Output folder created')

			if errFolder and not notFound.empty:
				errFile = outputPath + '/' + 'Error.csv'
				notFound.to_csv(errFile)
				shutil.move(errFolder, outputPath+'/')

			with Image(filename=workingDIR + 'Example.pdf', resolution=res) as img:
				img.save(filename=outputPath+'/temp_ex.jpg')

			with Image(filename=outputPath+'/temp_ex.jpg', resolution=res) as img:
				img.resize(size[0],size[1])
				img.save(filename=outputPath+'/final_ex.jpg')

			os.remove(outputPath+'/temp_ex.jpg')


			# files = os.listdir(workingDIR+inputPath)
			files = os.listdir(inputPath)

			"""logger.info('Creating process pool')
			pool = mp.Pool(processes=4)
			results = [pool.apply_async(editCertificate, args=(inputPath, file, example)) for file in files if not file.startswith('.')]
			output = [p.get() for p in results]"""

			print("File size : " + str(len(files)))
			print("div : " + str(len(files)/4))
			counter = len(files)/4
			print("Counter : " , str(counter))
			threads = []
			for thd in range (4) :
				if thd != 3 :
					print(thd)
					rt = threading.Thread(target=thread_func , args=(inputPath , outputPath , thd*counter , (thd+1)*counter))
					threads.append(rt)
				else :
					print(str(thd) , " In else")
					rt = threading.Thread(target=thread_func , args=(inputPath , outputPath , thd*counter , len(files)))
					threads.append(rt)

			for thd in threads :
				thd.start()
			for thd in threads :
				thd.join()


			"""for file in files:
				if not file.startswith('.'):
					editCertificate(inputPath, file, example)"""

			os.remove(outputPath+'/final_ex.jpg')
			return outputPath

			"""if len(results) == len(output):
				os.remove(outputPath+'/final_ex.jpg')
				return outputPath
			else:
				print False"""

	except:
		logger.exception(sys.exc_info())
		# print sys.exc_info()
		# print err
