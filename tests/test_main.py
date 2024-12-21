import os
import sys

from pytest import fixture, mark
import json
from flask import Flask

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import main


@fixture
def mock_request():
    """
A helper to create a mocked Flask request object.
    """

    def _mock_request(data):
        app = Flask(__name__)
        with app.test_request_context(json=data):
            return app.test_request_context(json=data).request

    return _mock_request


@fixture(autouse=True)
def mock_storage(monkeypatch):
    """
Mock the Google Cloud Storage Client for testing.
    """
    from google.cloud.storage import Client

    class MockBlob:
        def __init__(self, content):
            self.content = content
            self.iterator = None

        def open(self, mode):
            return self

        def __enter__(self):
            self.iterator = iter(self.content.splitlines(keepends=True))
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.iterator = None  # Clean up the iterator

        def read(self):
            return self.content

        def readline(self):
            if self.iterator is None:
                raise ValueError("I/O operation on closed file.")
            return next(self.iterator, "")

    class MockBucket:
        def __init__(self, blobs):
            self.blobs = blobs

        def get_blob(self, blob_name):
            return self.blobs.get(blob_name)

    class MockStorageClient:
        def __init__(self, buckets):
            self.buckets = buckets

        def get_bucket(self, bucket_name):
            return self.buckets.get(bucket_name)

    mock_client = MockStorageClient(
        {
            "test-bucket": MockBucket(
                {
                    "Game.ini": MockBlob(
                        """
[ServerSettings]
DifficultyOffset=0.5
MaxPlayers=16
                        """
                    ),
                    "GameUserSettings.ini": MockBlob(
                        """
[Scalability]
ResolutionQuality=100
ViewDistanceQuality=3

[/Script/Engine.GameUserSettings]
bUseVSync=False
FullscreenMode=2
                        """
                    ),
                }
            )
        }
    )

    monkeypatch.setattr("google.cloud.storage.Client", lambda *args, **kwargs: mock_client)


@mark.unit
def test_main_success(mock_request):
    """
Test the main function for successful response.
    """
    from flask import Flask

    # Create a Flask app and push the application context
    app = Flask(__name__)
    with app.app_context():
        request_data = {"bucket_name": "test-bucket"}
        request = mock_request(request_data)
        response = main(request)

        assert response.status_code == 200

        response_data = json.loads(response.get_data(as_text=True))

        assert response_data["Game.ini"]["difficultyoffset"] == "0.5"
        assert response_data["GameUserSettings.ini"]["Scalability"]["viewdistancequality"] == "3"
        assert response_data["GameUserSettings.ini"]["GameUserSettings"]["fullscreenmode"] == "2"
