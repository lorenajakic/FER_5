import requests
import time
import json
import psycopg2
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
API_KEY = "cd0426af-297d-42d6-af84-e91c10dc12fa"    # change to your key
BASE_URL = "https://content.guardianapis.com/search"
JSON_FILE = "guardian_articles_vectors.json"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" # 384-dimensional vector model

DB_CONFIG = {
    "dbname": "ankanePgVector",  # change to your database name
    "user": "postgres",
    "password": "bazepodataka",         # change to your password
    "host": "localhost",
    "port": "55432"              # change to port used at your computer
}

# --- 2. HELPER FUNCTIONS ---

def month_range(start_date, end_date):
    """Generator that yields (from_date, to_date) pairs for months between the specified dates."""
    current = start_date.replace(day=1)
    while current <= end_date:
        # Calculate the end of the month, avoiding issues with shorter months
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        # Limit the date to the actual end date if necessary
        to_dt = min(next_month - timedelta(days=1), end_date)
        yield current, to_dt
        current = next_month
        # Break if the next month is past the end date
        if current > end_date:
            break

# --- 3. MAIN FUNCTION (Single-pass ETL) ---

def fetch_process_and_insert(query, max_articles, start_date, end_date, model, conn, cur):
    """
    Fetches, vectorizes, and inserts articles into the database in a single step (streaming).
    Saves all processed articles (with vectors) to a JSON file at the end.
    """
    articles_processed = []
    
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("ERROR: Invalid date format. Use 'YYYY-MM-DD'.")
        return

    print(f"--- Starting ETL process for '{query}' (max {max_articles} articles) ---")

    for from_dt, to_dt in month_range(start_dt, end_dt):
        page = 1
        month_str = from_dt.strftime('%Y-%m')
        
        if len(articles_processed) >= max_articles:
             break
             
        while len(articles_processed) < max_articles:
            params = {
                "api-key": API_KEY,
                "q": query,
                "page": page,
                "page-size": 50, # Using 50 as page_size for the API
                "from-date": from_dt.strftime("%Y-%m-%d"),
                "to-date": to_dt.strftime("%Y-%m-%d"),
                "show-fields": "bodyText,trailText,byline"
            }
            
            # 1. API FETCH
            try:
                response = requests.get(BASE_URL, params=params)
                response.raise_for_status() 
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f"ERROR: API request failed in {month_str}, page {page}: {e}")
                time.sleep(5) 
                break 

            resp_info = data.get("response", {})
            results = resp_info.get("results", [])
            total_pages = resp_info.get("pages", 1)

            if not results:
                print(f"No more results found for {month_str}.")
                break

            # 2. ITERATION, VECTORIZATION, AND INSERTION
            for item in results:
                if len(articles_processed) >= max_articles:
                    break
                    
                fields = item.get("fields", {})
                
                # A. Data preparation
                article_id = item.get("id")
                title = item.get("webTitle")
                trailText = item.get("trailText")
                body = item.get("body")
                # Concatenate title, trailText, and body for embedding
                text_to_embed = (title or "") + "\n" + (fields.get("trailText") or "") + "\n" + (fields.get("bodyText") or "")

                # B. Create embedding
                try:
                    vector = model.encode(text_to_embed, convert_to_tensor=False).tolist()
                except Exception as e:
                    print(f"WARNING: Error during vectorization for article {article_id}. Skipping. Details: {e}")
                    continue
                
                # C. Insert into PostgreSQL (One transaction per row)
                try:
                    cur.execute(
                        "INSERT INTO articles_vectors (article_id, title, trailText, body, text_to_embed, embedding) VALUES (%s, %s, %s, %s, %s, %s)",
                        (article_id, title, trailText, body, text_to_embed, vector)
                    )
                    conn.commit() # COMMIT after every row
                    
                    # D. Add to list for JSON
                    article = {
                        "id": article_id,
                        "title": title,
                        "body": fields.get("bodyText", ""),
                        "trailText": fields.get("trailText", ""),
                        "byline": fields.get("byline", ""),
                        "date": item.get("webPublicationDate"),
                        "url": item.get("webUrl"),
                        "embedding": vector # adding the vector
                    }
                    articles_processed.append(article)
                    
                    if len(articles_processed) % 10 == 0:
                         print(f"Inserted article {len(articles_processed)}/{max_articles}: {title[:70]}...")

                except psycopg2.Error as e:
                    print(f"ERROR: Failed to insert article {article_id} into the database. Details: {e}")
                    conn.rollback() # Rollback transaction in case of error
            
            # 3. Page and limit control
            if len(articles_processed) >= max_articles or page >= total_pages:
                break

            page += 1
            time.sleep(0.5) # Wait to respect the API rate limit (12 req/s)

    # 4. Save the complete data to the JSON file at the end
    try:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(articles_processed, f, ensure_ascii=False, indent=2)
        print(f"\nDone! Saved {len(articles_processed)} articles (with vectors) to {JSON_FILE}")
    except Exception as e:
        print(f"ERROR: Could not save data to JSON file. Details: {e}")
            
    print("\n--- Download and processing complete. ---")


# --- 4. MAIN INITIALIZATION LOGIC ---

if __name__ == "__main__":
    
    # --- Download settings ---
    NUM_ARTICLES = 20500                        # change to total number of articles to download
    SEARCH_QUERY = "animals"   # change to search topic eg. "peace in world"
    START_DATE = "2000-1-1"                    # change to valid date here
    END_DATE = "2025-10-10"                     # change to valid date here
    
    # Database and model initialization
    conn, cur, model = None, None, None
    
    try:
        # Initialize model
        print(f"\n--- Loading vectorization model: {EMBEDDING_MODEL_NAME} ---")
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        # Connect to PostgreSQL
        print("--- Connecting to the PostgreSQL database ---")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Step 1-3: Fetch, vectorize, and insert
        fetch_process_and_insert(
            query=SEARCH_QUERY,
            max_articles=NUM_ARTICLES,
            start_date=START_DATE,
            end_date=END_DATE,
            model=model,
            conn=conn,
            cur=cur
        )

    except psycopg2.Error as e:
        print(f"FATAL ERROR: Failed to connect to PostgreSQL. Details: {e}")
    except Exception as e:
        print(f"FATAL ERROR: An unexpected error occurred in the program. Details: {e}")
    finally:
        # Closing the connection
        if cur: cur.close()
        if conn: conn.close()
        if conn: print("PostgreSQL connection closed.")

    print("\n--- Program finished. ---")
