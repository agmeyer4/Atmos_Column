#!/bin/bash

# Retrieve data from the earthdata download creation
# run with two arguments as follows:
# < ./tropomi_download.sh /path/to/txt_file/with/urls.txt /path/to/download/location >
# Where urls.txt is a file with a url to download on each line, likely obtained from the download creation in earthdata
# Enter your earthdata login and password
# Should download the files in urls.txt to the input download folder. 

#agm added
# Check if the number of arguments is correct
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <urls_txt_file> <download_to_path>"
    exit 1
fi

urls_txt_file=$1
download_to_path=$2

# Check if the first argument is a file
if [ ! -f "$urls_txt_file" ]; then
    echo "Error: $urls_txt_file is not a valid file."
    exit 1
fi

# Check if the second argument is a valid directory path
if [ ! -d "$download_to_path" ]; then
    echo "Error: $download_to_path is not a valid directory path."
    exit 1
fi

echo "Downloading to $download_to_path"
cd $download_to_path
file_urls=($(cat $urls_txt_file))



GREP_OPTIONS=''

cookiejar=$(mktemp cookies.XXXXXXXXXX)
netrc=$(mktemp netrc.XXXXXXXXXX)
chmod 0600 "$cookiejar" "$netrc"
function finish {
  rm -rf "$cookiejar" "$netrc"
}

trap finish EXIT
WGETRC="$wgetrc"

prompt_credentials() {
    echo "Enter your Earthdata Login or other provider supplied credentials"
    read -p "Username (agmeyer4): " username
    username=${username:-agmeyer4}
    read -s -p "Password: " password
    echo "machine urs.earthdata.nasa.gov login $username password $password" >> $netrc
    echo
}

exit_with_error() {
    echo
    echo "Unable to Retrieve Data"
    echo
    echo $1
    echo
    echo "https://data.gesdisc.earthdata.nasa.gov/data/S5P_TROPOMI_Level2/S5P_L2__CH4____HiR.2/2023/189/S5P_OFFL_L2__CH4____20230708T201000_20230708T215129_29715_03_020500_20230710T121253.nc"
    echo
    exit 1
}

prompt_credentials
  detect_app_approval() {
    approved=`curl -s -b "$cookiejar" -c "$cookiejar" -L --max-redirs 5 --netrc-file "$netrc" https://data.gesdisc.earthdata.nasa.gov/data/S5P_TROPOMI_Level2/S5P_L2__CH4____HiR.2/2023/189/S5P_OFFL_L2__CH4____20230708T201000_20230708T215129_29715_03_020500_20230710T121253.nc -w '\n%{http_code}' | tail  -1`
    if [ "$approved" -ne "200" ] && [ "$approved" -ne "301" ] && [ "$approved" -ne "302" ]; then
        # User didn't approve the app. Direct users to approve the app in URS
        exit_with_error "Please ensure that you have authorized the remote application by visiting the link below "
    fi
}

setup_auth_curl() {
    # Firstly, check if it require URS authentication
    status=$(curl -s -z "$(date)" -w '\n%{http_code}' https://data.gesdisc.earthdata.nasa.gov/data/S5P_TROPOMI_Level2/S5P_L2__CH4____HiR.2/2023/189/S5P_OFFL_L2__CH4____20230708T201000_20230708T215129_29715_03_020500_20230710T121253.nc | tail -1)
    if [[ "$status" -ne "200" && "$status" -ne "304" ]]; then
        # URS authentication is required. Now further check if the application/remote service is approved.
        detect_app_approval
    fi
}

setup_auth_wget() {
    # The safest way to auth via curl is netrc. Note: there's no checking or feedback
    # if login is unsuccessful
    touch ~/.netrc
    chmod 0600 ~/.netrc
    credentials=$(grep 'machine urs.earthdata.nasa.gov' ~/.netrc)
    if [ -z "$credentials" ]; then
        cat "$netrc" >> ~/.netrc
    fi
}


fetch_urls() {
    local urls=("$@")  # Accept an array of URLs as arguments

    if command -v curl >/dev/null 2>&1; then
        setup_auth_curl
        for line in "${urls[@]}"; do  # Loop through the array of URLs
            filename="${line##*/}"
            stripped_query_params="${filename%%\?*}"

            curl -f -b "$cookiejar" -c "$cookiejar" -L --netrc-file "$netrc" -g -o "$stripped_query_params" -- "$line" || exit_with_error "Command failed with error. Please retrieve the data manually."
        done
    elif command -v wget >/dev/null 2>&1; then
        echo "WARNING: Can't find curl, use wget instead."
        echo "WARNING: Script may not correctly identify Earthdata Login integrations."
        setup_auth_wget

        for line in "${urls[@]}"; do  # Loop through the array of URLs
            filename="${line##*/}"
            stripped_query_params="${filename%%\?*}"

            wget --load-cookies "$cookiejar" --save-cookies "$cookiejar" --output-document "$stripped_query_params" --keep-session-cookies -- "$line" || exit_with_error "Command failed with error. Please retrieve the data manually."
        done
    else
        exit_with_error "Error: Could not find a command-line downloader.  Please install curl or wget"
    fi
}

# Call fetch_urls with the file_urls array
fetch_urls "${file_urls[@]}"
