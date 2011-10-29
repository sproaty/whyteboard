if test -z "$1"
then
  echo "USAGE: release.sh [version number]"
  exit
fi

PROGRAM=whyteboard-$1
SRC_DIRECTORY=$(cd `dirname $0` && pwd)

# biuld
./binaries.sh $1

# upload to launchpad
dput whyteboard whyteboard\_$1\_source.changes

# update data file for latest version
python write-latest-update-file.py $1 linux

python upload-latest-update-file.py