from PIL import Image, ImageDraw

# size of the base image
size = 1024
img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)

# outer circle (Poké Ball)
draw.ellipse((0, 0, size, size), fill="white", outline="black", width=20)

# top half (red)
draw.pieslice((0, 0, size, size), start=180, end=360, fill="red", outline="black", width=20)

# horizontal line
draw.line((0, size//2, size, size//2), fill="black", width=40)

# center circle (black outer, white inner)
r_outer = size//6
r_inner = size//9
center = (size//2, size//2)
draw.ellipse((center[0]-r_outer, center[1]-r_outer, center[0]+r_outer, center[1]+r_outer), fill="black")
draw.ellipse((center[0]-r_inner, center[1]-r_inner, center[0]+r_inner, center[1]+r_inner), fill="white")

# save PNG and ICO
img.save("icon.png")
img.save("icon.ico")
print("✅ Saved icon.png and icon.ico")
