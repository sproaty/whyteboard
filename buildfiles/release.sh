if test -z "$1"
then
  echo "USAGE: release.sh [version number]"
  exit
fi

BUILDFILES=$(cd `dirname $0` && pwd)/buildfiles

pushd $BUILDFILES

# build
./binaries.sh $1

# upload to launchpad
dput whyteboard whyteboard\_$1\_source.changes

python write-latest-update-file.py $1 linux
python upload-latest-update-file.py