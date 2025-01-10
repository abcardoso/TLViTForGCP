import os
import urllib.request
from pyunpack import Archive
from google.cloud import storage
from utils.display import display_progress_bar

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

def download_file_toGCP(url_base, url_suffix, bucket_name="vittogcp-bucket01-ds", dataset_name="default_dataset", chunk_size=32 * 1024 * 1024, workers=8):
    """
    Downloads a file from a URL and uploads it directly to a GCP bucket in chunks concurrently, without saving locally.

    Parameters:
    - url_base (str): The base URL where the file is located.
    - url_suffix (str): The part of the URL that specifies the file to be downloaded.
    - bucket_name (str): The GCP bucket name where the file will be uploaded.
    - dataset_name (str): The name of the dataset being processed.
    - chunk_size (int): The size of each chunk in bytes for concurrent uploading.
    - workers (int): The number of concurrent workers for the upload.
    """
    try:
        # Full URL of the file
        full_url = url_base + url_suffix

        # Generate dynamic blob name
        #destination_blob_name = generate_dynamic_blob_name(dataset_name, url_suffix)
        destination_blob_name = dataset_name

        # Initialize the GCP storage client and the bucket
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        print(f"Downloading from {full_url} and uploading directly to GCP bucket: {bucket_name}/{destination_blob_name}")

        # Stream the data from the URL and use a custom upload handler with concurrent chunking
        with urllib.request.urlopen(full_url) as response:
            storage.transfer_manager.upload_chunks_concurrently(
                blob, response, chunk_size=chunk_size, max_workers=workers
            )

        print(f"File successfully uploaded to GCP bucket: {bucket_name}/{destination_blob_name}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


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

def download_chunks_concurrently(
    bucket_name, blob_name, filename, chunk_size=32 * 1024 * 1024, workers=8):
    """Download a single file in chunks, concurrently in a process pool."""

    # The ID of your GCS bucket
    # bucket_name = "your-bucket-name" vittogcp-bucket01-ds

    # The file to be downloaded
    # blob_name = "target-file"

    # The destination filename or path
    # filename = ""

    # The size of each chunk. The performance impact of this value depends on
    # the use case. The remote service has a minimum of 5 MiB and a maximum of
    # 5 GiB.
    # chunk_size = 32 * 1024 * 1024 (32 MiB)

    # The maximum number of processes to use for the operation. The performance
    # impact of this value depends on the use case, but smaller files usually
    # benefit from a higher number of processes. Each additional process occupies
    # some CPU and memory resources until finished. Threads can be used instead
    # of processes by passing `worker_type=transfer_manager.THREAD`.
    # workers=8


    storage_client = Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    transfer_manager.download_chunks_concurrently(
        blob, filename, chunk_size=chunk_size, max_workers=workers
    )

    print("Downloaded {} to {}.".format(blob_name, filename))