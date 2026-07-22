import colorsys

# thanks to stackoverflow: http://stackoverflow.com/questions/27650712/python-time-in-format-dayshoursminutesseconds-to-seconds
def timeToSeconds(time):
   multi = [1,60,3600,86400]
   try:
      time = [float(x) for x in time.split(":")]
      t_ret = 0
      for i,t in enumerate(reversed(time)):
         t_ret += multi[i] * t
      return t_ret
   except ValueError:
      return None

def volumeColor(value, vmax=200):
   # Map slider value to a hue from 270° (purple) at 0 to 0° (red) at vmax
   hue = 270.0 * (1 - max(0, min(value, vmax)) / vmax) / 360.0
   r, g, b = colorsys.hsv_to_rgb(hue, 0.4, 0.8)
   return '#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255))

def main():
   print(timeToSeconds("1:30"))
   print(timeToSeconds("0:40"))

if __name__ == '__main__':
   main()