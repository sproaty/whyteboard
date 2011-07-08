if test -z "$1"
then
  echo "Please provide a version number."
  exit
fi


PROGRAM=whyteboard-$1
SRC_DIRECTORY=$(cd `dirname $0` && pwd)

# create tar from all needed program code; exclude unneeded stuff
tar czf $PROGRAM.tar.gz whyteboard/ images/ locale/ whyteboard-help/ whyteboard.py CHANGELOG.txt DEVELOPING.txt LICENSE.txt README.txt TODO.txt --exclude=*.pyc --exclude=.bzr*

# create the debian 'package' directory for this build
mkdir ../sb/$PROGRAM
cd ../sb/$PROGRAM
mkdir debian

# extract the source tar into the directory and copy over needed files from source 'build' directory
tar xf $SRC_DIRECTORY/$PROGRAM.tar.gz
cp $SRC_DIRECTORY/$PROGRAM.tar.gz .

cp $SRC_DIRECTORY/build/debian/* debian
cp $SRC_DIRECTORY/build/whyteboard.png .
cp $SRC_DIRECTORY/build/whyteboard.xml .
cp $SRC_DIRECTORY/build/whyteboard.desktop .

# now build the debian package
debuild -S

# upload file to launchpad
cd ..
#dput whyteboard whyteboard\_$1\_source.changes
