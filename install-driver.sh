#!/usr/bin/bash

declare -A chrome_versions

chrome_versions=( ['89.0.4389.47']='843831' )
chrome_drivers=( "89.0.4389.23" )

# Download Chrome
for br in "${!chrome_versions[@]}"
do
    echo "Downloading Chrome version $br"
    mkdir -p "/opt/chrome/"
    curl -Lo "/opt/chrome/chrome-linux.zip" "https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F${chrome_versions[$br]}%2Fchrome-linux.zip?alt=media"
    unzip -q "/opt/chrome/chrome-linux.zip" -d "/opt/chrome/"
    mv /opt/chrome/chrome-linux/* /opt/chrome/
    rm -rf /opt/chrome/chrome-linux "/opt/chrome/chrome-linux.zip"
done
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