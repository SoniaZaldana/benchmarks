# How to resolve dacapo dependency in this repository

### 1. Install the dacapo JAR file into your local maven repository 

`mvn install:install-file -Dfile=/path/to/your/file.jar -DgroupId=com.example -DartifactId=your-artifact -Dversion=1.0 -Dpackaging=jar`

### Build the project 

`mvn clean install`
