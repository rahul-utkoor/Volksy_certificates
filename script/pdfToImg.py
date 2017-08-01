#/usr/bin/python2.7
from wand.image import Image

res = 300
size = (2339,1653)

with Image(filename='Data/Example.pdf', resolution=res) as img:
	img.save(filename='temp.jpg')

with Image(filename='temp.jpg', resolution=res) as img:
	img.resize(size[0],size[1])
	img.save(filename='final.jpg')