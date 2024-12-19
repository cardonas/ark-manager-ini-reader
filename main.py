import configparser
import json

import functions_framework
from flask import jsonify
from google.cloud import storage


@functions_framework.http
def main(request):
    print("RUNNING FUNCTION!!!")
    data = json.loads(request.get_data())

    storage_client = storage.Client(project="ark-manager-shadow-dev")
    bucket_name = data["bucket_name"]

    files = ["Game.ini", "GameUserSettings.ini"]

    all_settings = {}
    for file_name in files:
        print(file_name)
        file = storage_client.get_bucket(bucket_name).get_blob(file_name)

        with file.open("r") as f:
            ini_content = f.read()

        # Parse the INI content
        config = configparser.ConfigParser()
        config.read_string(ini_content)

        for section in config.sections():
            settings = dict(config.items(section))
            if file_name == "GameUserSettings.ini":
                if file_name not in all_settings:
                    all_settings[file_name] = {}
                game_user_settings = all_settings[file_name]
                if "." in section:
                    section = section.split(".")[1]
                game_user_settings[section] = settings
            else:
                all_settings[file_name] = settings

    return jsonify(all_settings)
