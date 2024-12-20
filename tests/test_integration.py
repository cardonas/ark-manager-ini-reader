import os
import sys

import requests
from flask import Flask
from flask.cli import load_dotenv
from google.cloud import storage
from pytest import fixture, mark

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()


@fixture
def gcs_client():
    """
Create and return a Google Cloud Storage client for interacting with the test bucket.
    """
    return storage.Client(project=os.getenv("PROJECT"))


@fixture
def setup_test_bucket(gcs_client):
    """
Set up a test bucket with mock files for integration testing.
    """
    bucket = gcs_client.create_bucket(bucket_or_name='ark-manager-test', project='ark-manager-shadow-dev',
                                      location='us-central1')

    # Upload test files (e.g., Game.ini, GameUserSettings.ini) to the test bucket
    files = {
        "Game.ini": """
[ServerSettings]
DifficultyOffset=0.5
MaxPlayers=16
        """,
        "GameUserSettings.ini": """
[Scalability]
ResolutionQuality=100
ViewDistanceQuality=3

[/Script/Engine.GameUserSettings]
bUseVSync=False
FullscreenMode=2
            """
    }

    for file_name, content in files.items():
        blob = bucket.blob(file_name)
        blob.upload_from_string(content)

    yield bucket

    # Clean up: Remove files after the test
    for file_name in files.keys():
        blob = bucket.blob(file_name)
        blob.delete()
    bucket.delete()


@mark.integration
def test_main_integration(setup_test_bucket):
    """
Integration test to validate the main function interacting with Google Cloud Storage.
    """
    # Ensure the test bucket is available

    assert setup_test_bucket.exists()

    # Test data for the request
    request_data = {"bucket_name": setup_test_bucket.name}

    response = requests.post(os.getenv('HTTPS_TRIGGER_URL'), json=request_data,
                             headers={"Content-Type": "application/json"})

    assert response.status_code == 200

    response_data = response.json()

    # Check the contents from the test files uploaded to GCS
    assert response_data["Game.ini"]["difficultyoffset"] == "0.5"
    assert response_data["GameUserSettings.ini"]["Scalability"]["resolutionquality"] == "100"
    assert response_data["GameUserSettings.ini"]["GameUserSettings"]["fullscreenmode"] == "2"
