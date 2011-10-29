if test -z "$1"
then
  echo "USAGE: binaries.sh [version number]"
  exit
fi

PROGRAM=whyteboard-$1
SRC=$(cd `dirname $0` && pwd)
BUILDFILES=$SRC/buildfiles

pushd $BUILDFILES
pushd scripts

python update-version.py $1

# run pylint and save output
python run-pylint.py

popd
popd
pushd ..

# create tar from all needed program code; exclude unneeded stuff
tar czf $PROGRAM.tar.gz whyteboard/ images/ locale/ whyteboard-help/ whyteboard.py CHANGELOG.txt DEVELOPING.txt LICENSE.txt README.txt TODO.txt --exclude=*.pyc --exclude=.bzr*

# create the debian 'package' directory for this build
mkdir ../sb/$PROGRAM
pushd ../sb/$PROGRAM
mkdir debian

# extract the source tar into the directory and copy over needed files from source 'build' directory
tar xf $SRC/$PROGRAM.tar.gz
cp $SRC$PROGRAM.tar.gz .

cp $BUILDFILES/debian/* debian
cp $BUILDFILES/whyteboard.png .
cp $BUILDFILES/whyteboard.xml .
cp $BUILDFILES/whyteboard.desktop .

# now build the debian package
debuild -S

popd
popd