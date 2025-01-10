import os
import urllib.request
from io import BytesIO
from pyunpack import Archive
from google.cloud import storage
from utils.display import display_progress_bar
from http.client import IncompleteRead

def download_file(url_base, url_suffix, output_path):
    """
    Downloads a file from the specified URL and displays a progress bar during the download.
    
    Parameters:
    - url (str): The base URL where the file is located.
    - url_suffix (str): The part of the URL that specifies the file to be downloaded.
    - output_path (str): The name to save the file as in the specified directory.
    """
    print(f"Downloading the file: {os.path.basename(output_path)}")
    
    try:
        # Request the file size with a HEAD request
        req = urllib.request.Request(url_base + url_suffix, method='HEAD')
        f = urllib.request.urlopen(req)
        file_size = int(f.headers['Content-Length'])

        # Check if the file already exists and if not, download it
        if not os.path.exists(output_path):
            # Open the connection and the file in write-binary mode
            with urllib.request.urlopen(url_base + url_suffix) as response, open(output_path, 'wb') as out_file:
                block_size = 8192  # Define the block size for downloading in chunks
                progress = 0       # Initialize the progress counter
                
                # Download the file in chunks and write each chunk to the file
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    progress += len(chunk)
                    display_progress_bar(progress, file_size)  # Update the progress bar

            # After the download is complete, display final progress bar with "Download complete"
            display_progress_bar(progress, file_size, done=True)

            # Verify if the downloaded file size matches the expected size
            downloaded_file_size = os.stat(output_path).st_size
        else:
            downloaded_file_size = os.stat(output_path).st_size
        
        # If the file size doesn't match, remove the file and try downloading again
        if file_size != downloaded_file_size:
            os.remove(output_path)
            print("File size incorrect. Downloading again.")
            download_file(url_base, url_suffix, output_path)
    
    except Exception as e:
        print("Error occurs when downloading file: " + str(e))
        print("Trying to download again")
        download_file(url_base, url_suffix, output_path)


def generate_dynamic_blob_name(dataset_name, url_suffix):
    """
    Generates a dynamic blob name for the dataset based on its name, current timestamp, and a hash of the URL suffix.

    Parameters:
    - dataset_name (str): The name of the dataset being processed.
    - url_suffix (str): The suffix of the URL being downloaded.

    Returns:
    - str: A dynamically generated blob name.
    """
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    url_hash = hashlib.md5(url_suffix.encode()).hexdigest()[:8]  # Short hash for uniqueness
    return f"{dataset_name}/{timestamp}_{url_hash}"

def download_file_toGCP(
    url_base, 
    url_suffix, 
    bucket_name="vittogcp-bucket01-ds", 
    dataset_name="default_dataset", 
    destination_name="destination_name", 
    project_id="your-project-id", 
    chunk_size=32 * 1024 * 1024, 
    workers=8, 
    retries=3
):
    """
    Downloads a file from a URL and uploads it directly to a GCP bucket with retry logic.

    Parameters:
    - url_base (str): The base URL where the file is located.
    - url_suffix (str): The part of the URL that specifies the file to be downloaded.
    - bucket_name (str): The GCP bucket name where the file will be uploaded.
    - dataset_name (str): The name of the dataset being processed.
    - destination_name (str): The name of the destination blob in the bucket.
    - chunk_size (int): The size of each chunk in bytes for concurrent uploading.
    - workers (int): The number of concurrent workers for the upload.
    - retries (int): The number of retry attempts for failed downloads.
    """
    attempt = 0
    while attempt < retries:
        try:
            # Full URL of the file
            full_url = url_base + url_suffix

            # Generate dynamic blob name
            destination_blob_name = destination_name

            # Initialize the GCP storage client and the bucket
            client = storage.Client(project=project_id)  # Specify the project ID
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)

            print(f"Downloading from {full_url} and uploading directly to GCP bucket: {bucket_name}/{destination_blob_name}")

            # Stream data from the URL and upload it
            with urllib.request.urlopen(full_url) as response:
                data = response.read()  # Read the entire file into memory
                blob.upload_from_file(BytesIO(data))  # Upload data using BytesIO as a file-like object

            print(f"File successfully uploaded to GCP bucket: {bucket_name}/{destination_blob_name}")
            return  # Exit the function if successful

        except (IncompleteRead, urllib.error.URLError) as e:
            attempt += 1
            print(f"Attempt {attempt}/{retries} failed: {str(e)}. Retrying...")

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise  # Raise non-retryable exceptions

    # If all retries fail, raise an exception
    raise Exception(f"Failed to download {url_suffix} after {retries} attempts.")


def extract_rar(file_path, output_dir):
    """ Extract a .rar archive to the specified output directory.

    Parameters:
    - file_path (str): The path to the .rar file to extract.
    - output_dir (str): The directory where the extracted files will be saved.
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        Archive(file_path).extractall(output_dir)
        print(f"Extraction successful! Files extracted to: {file_path[:-4]}")
    except Exception as e:
        print(f"An error occurred during extraction: {str(e)}")
