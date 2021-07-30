#!/usr/bin/bash

declare -A chrome_versions

chrome_drivers=( "92.0.4515.107" )

# Download Chromedriver
for dr in ${chrome_drivers[@]}
do
    echo "Downloading Chromedriver version $dr"
    mkdir -p "/opt/chromedriver"
    curl -Lo "/opt/chromedriver/chromedriver_linux64.zip" "https://chromedriver.storage.googleapis.com/$dr/chromedriver_linux64.zip"
    unzip -q "/opt/chromedriver/chromedriver_linux64.zip" -d "/opt/chromedriver/"
    chmod +x "/opt/chromedriver/chromedriver"
    rm -rf "/opt/chromedriver/chromedriver_linux64.zip"
done