from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
img = Image.open("eg1.jpg")
draw = ImageDraw.Draw(img)
font = ImageFont.truetype("arial.ttf", 28)
institute_name = "SECL, GVTC, Churcha, Baikunthpur Area"
if len(institute_name) <= 38 :
    draw.text((1240, 1195),institute_name,(0,0,0),font=font)
else :
    draw.text((1240, 1165),institute_name[:37]+"-",(0,0,0),font=font)
    draw.text((1240, 1195),institute_name[37:],(0,0,0),font=font)
img.save('sample-out1.jpg')
