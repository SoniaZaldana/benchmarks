#!/bin/bash

# download dacapo
sudo dnf install perf maven wget unzip -y
(cd dacapo && wget https://download.dacapobench.org/chopin/dacapo-23.11-chopin.zip && unzip dacapo-23.11-chopin.zip && rm dacapo-23.11-chopin.zip)

jdk_depts="autoconf tar zipexe zip java-23-openjdk-devel alsa-lib-devel cups-devel fontconfig-devel libXtst-devel libXt-devel libXrender-devel libXrandr-devel libXi-devel"

# download and build jdk
cd ..
# git clone git@github.com:openjdk/jdk.git
cd jdk
sudo dnf install -y $jdk_depts
git fetch
git checkout pr/20677
sudo yum install -y $jdk_depts
bash configure
make images

# do maven setup
cd ../benchmarks/dacapocallback
mvn install:install-file -Dfile=../dacapo/dacapo-23.11-chopin.jar -DgroupId=org.dacapo -DartifactId=dacapo -Dversion=1.0 -Dpackaging=jar
mvn clean install


