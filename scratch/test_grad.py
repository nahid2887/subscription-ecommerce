import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_gradient_canvas(width, height, c1, c2, c3=None, angle=45):
    """Creates a smooth multi-stop linear/radial gradient background."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    
    # Simple linear interpolation along angle
    max_dist = width * abs(cos_a) + height * abs(sin_a)
    
    for y in range(height):
        for x in range(0, width, 2):  # step by 2 for speed then resize or smooth
            proj = (x * cos_a + y * sin_a) / max_dist
            t = max(0.0, min(1.0, proj))
            if c3 and t > 0.5:
                sub_t = (t - 0.5) * 2.0
                r = int(c2[0] + (c3[0] - c2[0]) * sub_t)
                g = int(c2[1] + (c3[1] - c2[1]) * sub_t)
                b = int(c2[2] + (c3[2] - c2[2]) * sub_t)
            elif c3:
                sub_t = t * 2.0
                r = int(c1[0] + (c2[0] - c1[0]) * sub_t)
                g = int(c1[1] + (c2[1] - c1[1]) * sub_t)
                b = int(c1[2] + (c2[2] - c1[2]) * sub_t)
            else:
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.rectangle([x, y, x+1, y], fill=(r, g, b, 255))
    return img

print("Gradient function defined")
