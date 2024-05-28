import csv
import requests

# Define your TMDb API base URL and your API key
base_url = "https://api.themoviedb.org/3"
api_key = "%%%%"

# Define the endpoints you want to query
endpoints = [
    "/movie/popular",       # Popular movies
    "/tv/popular",          # Popular TV shows
    "/movie/top_rated",     # Top rated movies
    "/tv/top_rated",        # Top rated TV shows
    "/movie/upcoming",      # Upcoming movies
    "/movie/now_playing",   # Now playing movies
]

# Initialize an empty list to store all data
all_data = []

# Function to fetch data from a single endpoint with pagination
def fetch_data(endpoint, max_pages=5):
    page = 1
    while page <= max_pages:
        url = f"{base_url}{endpoint}?api_key={api_key}&page={page}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json().get("results", [])
            if not data:
                break
            all_data.extend(data)
            page += 1
        else:
            print(f"Error fetching data from {endpoint}: {response.text}")
            break

# Fetch data from each endpoint
for endpoint in endpoints:
    fetch_data(endpoint, max_pages=10)  # Adjust max_pages as needed

# Fetch genres separately since they are structured differently
genre_url = f"{base_url}/genre/movie/list?api_key={api_key}"
response = requests.get(genre_url)
if response.status_code == 200:
    genres = response.json().get("genres", [])
    all_data.extend(genres)
else:
    print(f"Error fetching data from /genre/movie/list: {response.text}")

# Extract fieldnames from the first dictionary in all_data
fieldnames = set()
for entry in all_data:
    fieldnames.update(entry.keys())
fieldnames = list(fieldnames)

# Remove rows with NaN values in specific columns
# Assuming "title" is one of the columns where NaN values should be removed
all_data = [entry for entry in all_data if isinstance(entry.get("title"), str)]

# Write all data to a CSV file
csv_file_path = "newtmdb.csv"
with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_data)

print(f"Data written to {csv_file_path}")
