import os
from PIL import Image

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_png = os.path.join(base_dir, "assets", "logo2.png")
    out_ico = os.path.join(base_dir, "assets", "app_icon.ico")
    sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
    img = Image.open(src_png).convert("RGBA")
    img.save(out_ico, sizes=sizes)

if __name__ == "__main__":
    main()
