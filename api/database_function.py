from fastapi import FastAPI, HTTPException, Body
from fastapi.encoders import jsonable_encoder
import logging
import os
import hashlib
import traceback
import json
import httpx
from typing import List, Dict, Any
from collections import deque

app = FastAPI()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EMAIL_FUNCTION_URL = os.environ.get("EMAIL_FUNCTION_URL")

print(f"DEBUG: EMAIL_FUNCTION_URL = {EMAIL_FUNCTION_URL}")

if not EMAIL_FUNCTION_URL:
    print("DEBUG: EMAIL_FUNCTION_URL environment variable is not set")
    logger.error("EMAIL_FUNCTION_URL environment variable is not set")
    raise EnvironmentError("Missing required environment variable: EMAIL_FUNCTION_URL")

# Queue to hold incoming posts
post_queue = deque(maxlen=5)

@app.post("/api/database")
async def save_to_database(data: Dict[str, List[Dict[str, Any]]] = Body(...)):
    try:
        print("DEBUG: Entering save_to_database function")
        posts = data.get("posts", [])
        print(f"DEBUG: Number of posts received: {len(posts)}")
        logger.info(f"Received data to save to database. Number of posts: {len(posts)}")
        logger.debug(f"Received data: {json.dumps(posts, indent=2)}")

        if not isinstance(posts, list):
            print(f"DEBUG: Invalid posts data type: {type(posts)}")
            raise HTTPException(status_code=422, detail=f"Expected a list of posts, but received {type(posts)}")

        # Add posts to the queue
        for post in posts:
            post_queue.append(post)

        # Process the queue
        new_posts = await process_queue()
        print(f"DEBUG: Number of new posts saved: {len(new_posts)}")
        logger.info(f"Saved {len(new_posts)} new posts to database")
        
        # Send email notifications for new posts
        for post in new_posts:
            print(f"DEBUG: Sending email notification for post: {post.get('post_link')}")
            await send_email_notification(post)
        
        return {"new_posts": new_posts}
    except HTTPException as he:
        print(f"DEBUG: HTTPException in save_to_database: {str(he)}")
        raise he
    except Exception as e:
        print(f"DEBUG: Unexpected error in save_to_database: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        logger.error(f"Error saving to database: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def process_queue():
    new_posts = []
    try:
        print(f"DEBUG: Processing queue with {len(post_queue)} posts")
        while post_queue:
            post = post_queue.popleft()
            post_link = post.get('post_link')
            if post_link:
                doc_id = hashlib.md5(post_link.encode()).hexdigest()
                doc_ref = db.collection('posts').document(doc_id)
                doc = doc_ref.get()
                if not doc.exists:
                    print(f"DEBUG: Saving new post: {post_link}")
                    doc_ref.set(post)
                    new_posts.append(post)
                    logger.info(f"Saved new post: {post_link}")
                else:
                    print(f"DEBUG: Post already exists, skipping: {post_link}")
                    logger.info(f"Post already exists, skipping: {post_link}")
            else:
                print(f"DEBUG: Skipping post without post_link: {post}")
                logger.warning(f"Skipping post without post_link: {post}")
        return new_posts
    except Exception as e:
        print(f"DEBUG: Error in process_queue: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        logger.error(f"Error in process_queue: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def send_email_notification(post: Dict[str, Any]):
    try:
        print(f"DEBUG: Sending email notification for post: {post.get('post_link')}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                EMAIL_FUNCTION_URL,
                json={"subject": "New Car Listed", "car_info": post},
                timeout=30.0
            )
            response.raise_for_status()
            print(f"DEBUG: Email notification sent successfully for post: {post.get('post_link')}")
            logger.info(f"Email notification sent for post: {post.get('post_link')}")
    except Exception as e:
        print(f"DEBUG: Failed to send email notification: {str(e)}")
        logger.error(f"Failed to send email notification: {str(e)}")
        # We don't want to raise an exception here, as it would stop the database function
        # Instead, we log the error and continue

import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

def initialize_firebase():
    try:
        print("DEBUG: Initializing Firebase")
        if not firebase_admin._apps:
            cred_dict = {
                "type": os.environ.get("FIREBASE_TYPE"),
                "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
                "auth_uri": os.environ.get("FIREBASE_AUTH_URI"),
                "token_uri": os.environ.get("FIREBASE_TOKEN_URI"),
                "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
                "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_X509_CERT_URL"),
                "universe_domain": os.environ.get("FIREBASE_UNIVERSE_DOMAIN")
            }
            
            print("DEBUG: Firebase credentials loaded from environment variables")
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        print("DEBUG: Firebase initialized successfully")
        logger.info("Firebase initialized successfully")
        return db
    except Exception as e:
        print(f"DEBUG: Failed to initialize Firebase: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        raise

# Initialize Firebase when this module is imported
print("DEBUG: About to initialize Firebase")
db = initialize_firebase()
print("DEBUG: Firebase initialization complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)