from flask import Flask, render_template, request, jsonify, send_from_directory
from pytube import YouTube
import json
import os
import uuid
from google.oauth2 import service_account
from googleapiclient.discovery import build
from tqdm import tqdm
from googleapiclient.http import MediaFileUpload
import requests
from progress.bar import Bar
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import random
import base64

app = Flask(__name__)

credentials_file = 'data/json/client_secrets.json'
# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Your GitHub personal access token
access_token = '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'

# The owner of the repository (your GitHub username or organization)
owner = 'nitikshh'

# The name of the existing repository
repo_name = 'moviedata'


# Set up a route to serve the 'data' folder
@app.route('/data/<path:filename>')
def download_file(filename):
  return send_from_directory('data', filename)


# Set up a route to serve the 'assets' folder for static files (CSS, JS, etc.)
@app.route('/assets/<path:filename>')
def assets(filename):
  return send_from_directory('assets', filename)


@app.route('/')
def index():
  return render_template('moviz.html')


@app.route('/youtube')
def youtube():
  return render_template('youtube.html')


@app.route('/demo')
def demo():
  return render_template('demo.html')


@app.route('/upload')
def upload_video():
  return render_template('upload.html')


@app.route('/moviedetails')
def moviedetails():
  return render_template('moviedetails.html')


@app.route('/upload', methods=['POST'])
def upload():
  title = request.form['title']
  description = request.form['description']
  release_date = request.form['release_date']
  rating = int(request.form['rating'])
  studios = request.form['studios']
  tags = [tag.strip() for tag in request.form['tags'].split(',')]

  # Generate unique ID using UUID
  unique_id = str(uuid.uuid4())

  # Save thumbnail
  thumbnail_file = request.files['thumbnail']
  thumbnail_filename = f"{unique_id}.jpg"
  thumbnail_path = os.path.join('data/videos', thumbnail_filename)
  thumbnail_file.save(thumbnail_path)

  # Save video
  video_file = request.files['video']
  video_filename = f"{unique_id}.mp4"
  video_path = os.path.join('data/videos', video_filename)
  video_file.save(video_path)

  # Optionally, specify a folder ID if you want to upload to a specific folder
  folder_id_to_upload = '1GTDJcJDOhp7xcodBJWusV6tUYFWkdmjQ'  # Replace with the actual folder ID

  drive_service = authenticate_drive()
  video_drive_id = upload_video_to_drive(drive_service, video_path,
                                         folder_id_to_upload)

  # Save information to data/json/data.json
  data = {
      'id': unique_id,
      'title': title,
      'thumbnail': thumbnail_path,
      'video_path': video_drive_id,
      'duration': 0,  # You can calculate this based on the video file
      'type': 'movie',
      'description': description,
      'release_date': release_date,
      'rating': rating,
      'studios': studios,
      'tags': tags,
  }

  save_to_json_uploaded(data)

  return jsonify({
      'success': True,
      'message': 'Data uploaded successfully.',
      'id': unique_id
  })


def authenticate_and_upload_video(video_path, folder_id):
  # Authenticate using service account credentials
  scope = [
      'https://spreadsheets.google.com/feeds',
      'https://www.googleapis.com/auth/drive'
  ]
  creds = ServiceAccountCredentials.from_json_keyfile_name(
      'client_secrets.json', scope)

  # Build Google Drive API service
  drive_service = build('drive', 'v3', credentials=creds)

  print('Uploading video to Google Drive............')

  # Upload video without progress bar
  media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=False)
  file_metadata = {'name': video_path.split('/')[-1], 'parents': [folder_id]}
  file = drive_service.files().create(body=file_metadata,
                                      media_body=media,
                                      fields='id').execute()

  print('Video uploaded successfully.')

  return file.get('id')


def save_to_json_uploaded(data):
  # Load existing data
  with open('data/json/data.json', 'r') as json_file:
    existing_data = json.load(json_file)

  # Append new data
  existing_data.append(data)

  # Save updated data
  with open('data/json/data.json', 'w') as json_file:
    json.dump(existing_data, json_file, indent=2)


@app.route('/download', methods=['GET', 'POST'])
def download():
  try:
    video_url = request.form['video_url']
    description = request.form['description']
    release_date = request.form['release_date']
    rating = int(request.form['rating'])
    studios = request.form['studios']
    title = request.form['title']
    tags = [tag.strip() for tag in request.form['tags'].split(',')]

    # New field from the select dropdown
    type = request.form['genre']

    # Download the video
    yt = YouTube(video_url)
    video_stream = yt.streams.get_highest_resolution()

    # Generate unique filename using UUID
    unique_filename = f"{str(uuid.uuid4())}"
    video_title_modified = title.replace(" ", "_")

    if type == 'movie':
      # Generate a unique ID using UUID
      unique_id = str(uuid.uuid4())

      # Save video to the "data/videos" folder with the same name
      video_filename = f"{unique_filename}.mp4"
      video_path = os.path.join('data/videos', video_filename)
      video_stream.download('data/videos', filename=video_filename)

      # Save thumbnail to the "data/videos" folder with the same name
      thumbnail_filename = f"{unique_filename}.jpg"
      thumbnail_url = yt.thumbnail_url
      thumbnail_data = requests.get(thumbnail_url).content
      thumbnail_path = os.path.join('data/videos', thumbnail_filename)
      with open(thumbnail_path, 'wb') as thumbnail_file:
        thumbnail_file.write(thumbnail_data)

      # Optionally, specify a folder ID if you want to upload to a specific folder
      folder_id_to_upload = '1GTDJcJDOhp7xcodBJWusV6tUYFWkdmjQ'  # Replace with the actual folder ID
      video_path2 = "videoo.mp4"
      video_drive_id = authenticate_and_upload_video(video_path2,
                                                     folder_id_to_upload)

      # Save information to data/json/data.json
      data = {
          'id': unique_id,
          'title': title,
          'thumbnail': thumbnail_path,
          'video_path': video_drive_id,
          'duration': yt.length,
          'type': type,
          'description': description,
          'release_date': release_date,
          'rating': rating,
          'studios': studios,
          'tags': tags,
      }
      save_to_json(data)

      return jsonify({
          'success': True,
          'message': 'Video downloaded and uploaded successfully.',
          'id': unique_id
      })
  except Exception as e:
    return jsonify({'success': False, 'message': f'Error: {str(e)}'})


def get_file_size(file_path):
  # Get the size of the file in bytes
  size_in_bytes = os.path.getsize(file_path)

  # Convert size to megabytes
  size_in_mb = size_in_bytes / (1024 * 1024)

  return size_in_mb


def save_to_json(data):
  json_path = 'data/json/data.json'

  if os.path.exists(json_path):
    with open(json_path, 'r') as json_file:
      try:
        existing_data = json.load(json_file)
      except json.JSONDecodeError:
        existing_data = []
  else:
    existing_data = []

  existing_data.append(data)

  with open(json_path, 'w') as json_file:
    json.dump(existing_data, json_file, indent=2)


@app.route('/subscribe', methods=['POST'])
def subscribe():
  email = request.form['email']

  try:
    # Save the email to data/emails/emails.json
    save_email_to_json(email)

    return jsonify({
        'success': True,
        'message': 'Email subscribed successfully.',
        'reload': True  # Add this key to indicate a reload
    })

  except Exception as e:
    return jsonify({'success': False, 'message': f'Error: {str(e)}'})


def save_email_to_json(email):
  json_path = 'data/emails/emails.json'

  if os.path.exists(json_path):
    with open(json_path, 'r') as json_file:
      try:
        existing_emails = json.load(json_file)
      except json.JSONDecodeError:
        existing_emails = []
  else:
    existing_emails = []

  existing_emails.append({'email': email})

  with open(json_path, 'w') as json_file:
    json.dump(existing_emails, json_file, indent=2)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=random.randint(2000, 9000), debug=True)
