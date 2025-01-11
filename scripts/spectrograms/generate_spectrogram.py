import os
import numpy as np
from scipy import signal
from matplotlib import pyplot as plt
from datasets import CWRU, Paderborn, Hust, UORED
from google.oauth2 import service_account
from google.cloud import storage
from io import BytesIO

def generate_spectrogram(metainfo, spectrogram_setup, signal_length, num_segments=None):
    dataset_name = metainfo[0]["dataset_name"]
    dataset = eval(dataset_name + "()")

    for info in metainfo:
        basename = info["filename"]
        filepath = os.path.join('data/raw/', dataset_name.lower(), basename + '.mat')

        # Load signal and label
        data, label = dataset.load_signal_by_path(filepath)

        # Normalize and detrend the signal
        data = (data - np.mean(data)) / np.std(data)  # Z-score normalization
        detrended_data = signal.detrend(data)

        # Determine the number of segments
        total_samples = detrended_data.shape[0]
        n_segments = total_samples // signal_length
        n_max_segments = min([num_segments or n_segments, n_segments])

        for i in range(n_max_segments):
            start_idx = i * signal_length
            end_idx = start_idx + signal_length
            segment = detrended_data[start_idx:end_idx]

            # Compute STFT
            f, t, Sxx = signal.stft(segment, **spectrogram_setup)

            # Convert to decibels for better scaling
            Sxx_dB = 10 * np.log10(np.abs(Sxx[:382, :]**2) + 1e-8)  # Add epsilon to avoid log(0)

            # Plot the spectrogram
            fig, ax = plt.subplots(figsize=(10, 6))
            im = ax.imshow(Sxx_dB, cmap='jet', aspect='auto', origin='lower',
                           extent=[t.min(), t.max(), f.min(), f.max()])
            ax.axis('off')

            # Save the spectrogram
            output = os.path.join('data/spectrograms', dataset_name.lower(), label,
                                   f"{basename}#{i+1}.png")
            
            #output = os.path.join('data/spectrograms', dataset_name.lower(), label, basename+'#{}.png'.format(int((i+1)/signal_length)))
            plt.savefig(output, bbox_inches='tight', pad_inches=0)
            print(f"Spectrogram {output} - created.")
            plt.close(fig)
            

    print(f"Completed spectrogram generation for {dataset_name}.")
    
def generate_spectrogram_GCP(metainfo, spectrogram_setup, signal_length, num_segments=None, credentials_path=None, project_id=None, bucket_ds=None, bucket_spectrogram=None):
    """
    Generates spectrograms from signals stored in a GCP bucket and saves them directly to another GCP bucket.

    Parameters:
    - metainfo (list): Metadata containing dataset information, including filenames and labels.
    - spectrogram_setup (dict): Parameters for the STFT (e.g., window size, overlap).
    - signal_length (int): The length of each segment for spectrogram generation.
    - num_segments (int): The maximum number of segments to generate per signal. Defaults to all segments.
    - credentials_path (str): Path to the Google Cloud service account JSON key file.
    - project_id (str): The Google Cloud project ID.
    """
    # Define GCP buckets
    dataset_bucket_name = bucket_ds
    spectrogram_bucket_name = bucket_spectrogram

    # Initialize GCP storage client with explicit credentials and project ID
    client_options = {"credentials": None, "project": project_id}
    if credentials_path:
        from google.oauth2 import service_account
        client_options["credentials"] = service_account.Credentials.from_service_account_file(credentials_path)

    storage_client = storage.Client(**client_options)
    dataset_bucket = storage_client.bucket(dataset_bucket_name)
    spectrogram_bucket = storage_client.bucket(spectrogram_bucket_name)

    dataset_name = metainfo[0]["dataset_name"]
    dataset = eval(dataset_name + "()")

    for info in metainfo:
        basename = info["filename"]
        label = info["label"]

        # Construct the GCP blob path for the dataset file
        dataset_blob_path = f"{dataset_name.lower()}/{basename}.mat"
        dataset_blob = dataset_bucket.blob(dataset_blob_path)

        try:
            # Read the dataset file from GCP
            print(f"Downloading {dataset_blob_path} from bucket {dataset_bucket_name}")
            data_stream = BytesIO()
            dataset_blob.download_to_file(data_stream)
            data_stream.seek(0)

            # Load signal and label from the dataset
            data, label = dataset.load_signal_by_path_GCP(data_stream, filename=basename)

            # Normalize and detrend the signal
            data = (data - np.mean(data)) / np.std(data)  # Z-score normalization
            detrended_data = signal.detrend(data)

            # Determine the number of segments
            total_samples = detrended_data.shape[0]
            n_segments = total_samples // signal_length
            n_max_segments = min([num_segments or n_segments, n_segments])

            for i in range(n_max_segments):
                start_idx = i * signal_length
                end_idx = start_idx + signal_length
                segment = detrended_data[start_idx:end_idx]

                # Compute STFT
                f, t, Sxx = signal.stft(segment, **spectrogram_setup)

                # Convert to decibels for better scaling
                Sxx_dB = 10 * np.log10(np.abs(Sxx[:382, :]**2) + 1e-8)  # Add epsilon to avoid log(0)

                # Plot the spectrogram
                fig, ax = plt.subplots(figsize=(10, 6))
                im = ax.imshow(Sxx_dB, cmap='jet', aspect='auto', origin='lower',
                               extent=[t.min(), t.max(), f.min(), f.max()])
                ax.axis('off')

                # Define nested structure for spectrogram storage
                spectrogram_blob_path = f"data/spectrograms/{dataset_name.lower()}/{label}/{basename}#{i+1}.png"
                spectrogram_blob = spectrogram_bucket.blob(spectrogram_blob_path)

                # Save the plot to a BytesIO buffer
                image_stream = BytesIO()
                plt.savefig(image_stream, format='png', bbox_inches='tight', pad_inches=0)
                image_stream.seek(0)

                # Upload the spectrogram to the GCP bucket
                spectrogram_blob.upload_from_file(image_stream, content_type="image/png")
                print(f"Spectrogram uploaded to {spectrogram_bucket_name}/{spectrogram_blob_path}")

                plt.close(fig)

        except Exception as e:
            print(f"An error occurred while processing {basename}: {str(e)}")

    print(f"Completed spectrogram generation for {dataset_name}.")