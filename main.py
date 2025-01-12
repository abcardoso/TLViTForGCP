from scripts.download_rawfile import download_rawfile
from scripts.spectrograms import generate_spectrogram, generate_spectrogram_GCP
from scripts.copy_spectrogram_to_folds import copy_spectrogram_to_folds
from src.data_processing.dataset_manager import DatasetManager
from utils import load_yaml
from utils.dual_output import DualOutput  # Import the class from dual_output.py
from experimenter_vitclassifier_kfold import experimenter_vitclassifier_kfold
from run_pretrain import experimenter
import sys
from datetime import datetime
import os
from google.cloud import storage
from io import StringIO
from google.oauth2 import service_account


class GCPLogger:
    def __init__(self, bucket_name, log_filename, project_id=None):
        """
        GCP Logger to write logs to a Google Cloud Storage bucket.

        Parameters:
        - bucket_name (str): Name of the GCP bucket for storing logs.
        - log_filename (str): Name of the log file to store.
        - project_id (str): Project ID for the GCP client (optional).
        """
        # Initialize the GCP storage client using Application Default Credentials (ADC)
        storage_client = storage.Client(project=project_id)
        self.bucket = storage_client.bucket(bucket_name)
        self.log_filename = log_filename
        self.log_buffer = StringIO()

    def write(self, message):
        """Write log messages to the buffer and stdout."""
        self.log_buffer.write(message)
        sys.__stdout__.write(message)

    def flush(self):
        """Upload log buffer content to GCP bucket."""
        blob = self.bucket.blob(self.log_filename)
        blob.upload_from_string(self.log_buffer.getvalue(), content_type="text/plain")
        self.log_buffer.seek(0)



# Create logs directory if it doesn't exist
os.makedirs("results", exist_ok=True)

project_id = "transferlearncwru01" 
bucket_ds = "vittogcp-bucket01-ds"
bucket_spectrogram = "vittogcp-bucket01-spectrogram"
bucket_logs = "vittogcp-bucket01-logs"
bucket_savedmodels = "vittogcp-bucket01-savedmodels"

# Redirect stdout
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
log_filename = f"results/experiment_log_{timestamp}.txt"
sys.stdout = GCPLogger(bucket_logs, log_filename, project_id=project_id)

# DOWNLOAD RAW FILES
def download():
    for dataset in ["CWRU", "UORED"]:
        download_rawfile(dataset)

# SPECTROGRAMS
def create_spectrograms():

    # Sets the number of segments
    num_segments = 20

    # Load the configuration files
    spectrogram_config = load_yaml('config/spectrogram_config.yaml')
    filter_config = load_yaml('config/filters_config.yaml')
    
    # Instantiate the data manager
        
    for dataset_name in spectrogram_config.keys():
        print(f"Starting the creation of the {dataset_name} spectrograms.")
        filter = filter_config[dataset_name]
        data_manager = DatasetManager(dataset_name)
        metainfo = data_manager.filter_data(filter)
        signal_length = spectrogram_config[dataset_name]["Split"]["signal_length"]
        spectrogram_setup = spectrogram_config[dataset_name]["Spectrogram"]
        
        # Creation of spectrograms    
        generate_spectrogram_GCP(metainfo, spectrogram_setup, signal_length, num_segments, project_id=project_id, bucket_ds=bucket_ds, bucket_spectrogram=bucket_spectrogram) 

# EXPERIMENTERS
def run_experimenter():
    #model = ResNet18() 
    use_vit = True #ViT or DeiT
    pretrain_model=False # pretrain or use saved 
    base_model=True # base model with no pre-train strategy
    
    experimenter_vitclassifier_kfold(use_vit, pretrain_model, base_model, project_id=project_id, bucket_savedmodels=bucket_savedmodels, bucket_spectrogram=bucket_spectrogram) #pre train and test


if __name__ == '__main__':
    try:
        # Listen on the port defined by the PORT environment variable
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)

        print("Study: Enhancing Bearing Fault Diagnosis with Vision Transformers: Addressing Similarity Bias through Spectrograms")
        
        #download()
        #create_spectrograms()
        run_experimenter()
    finally:
        # Close the log file
        sys.stdout.flush()
        sys.stdout = sys.__stdout__  # Reset stdout to the original