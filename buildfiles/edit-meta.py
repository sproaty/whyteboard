import os
import sys

lines = []
meta = os.path.abspath("whyteboard/misc/meta.py")

for line in open(meta):
    if "version =" in line:
        current = line[line.find(" = u") : -1]
        line = line.replace("version" + current, "version = u\"" + sys.argv[1] + "\"")
    lines.append(line)


_file = open(meta, "w")
for item in lines:
  _file.write(item)