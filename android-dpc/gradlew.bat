@if "%DEBUG%" == "" @echo off
@rem
@rem Copyright 2015 the original authors.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem      https://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.
@rem

if "%OS%"=="Windows_NT" setlocal

set DIRNAME=%~dp0
if "%DIRNAME%" == "" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%

if exist "%APP_HOME%\gradle\wrapper\gradle-wrapper.jar" goto execute

echo Error: gradle-wrapper.jar could not be found in %APP_HOME%\gradle\wrapper
goto fail

:execute
set CLASSPATH=
set JAVACMD=
if "%JAVA_HOME%" == "" goto gnuJavacmd
if exist "%JAVA_HOME%\bin\java.exe" set JAVACMD=%JAVA_HOME%\bin\java.exe

:gnuJavacmd
if "%JAVACMD%" == "" set JAVACMD=java

cd /d "%APP_HOME%"
"%JAVACMD%" "-Dorg.gradle.appname=%APP_BASE_NAME%" -classpath "%CLASSPATH%" -jar "%APP_HOME%\gradle\wrapper\gradle-wrapper.jar" %*

if ERRORLEVEL 1 goto fail
goto end

:fail
exit /b 1

:end
if "%OS%"=="Windows_NT" endlocal
:finish
endlocal
