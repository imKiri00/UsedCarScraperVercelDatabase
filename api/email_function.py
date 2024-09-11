from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailRequest(BaseModel):
    subject: str
    car_info: dict

@app.post("/api/email")
async def send_email_endpoint(email_request: EmailRequest):
    print(f"DEBUG: Received email request with subject: {email_request.subject}")
    return await send_email(email_request)

async def send_email(email_request: EmailRequest):
    try:
        print("DEBUG: Entering send_email function")
        from_email = os.environ.get("EMAIL_ADDRESS")
        password = os.environ.get("EMAIL_PASSWORD")
        smtp_server = os.environ.get("SMTP_SERVER")
        smtp_port = int(os.environ.get("SMTP_PORT"))
        to_email = os.environ.get("NOTIFICATION_EMAIL")

        print(f"DEBUG: Email configuration - SMTP Server: {smtp_server}, Port: {smtp_port}")
        print(f"DEBUG: Sending email from {from_email} to {to_email}")

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = email_request.subject

        # Create the email body with all car information, nicely formatted
        body = "A new car has been added:\n\n"
        body += "=" * 40 + "\n\n"  # Separator line
        for key, value in email_request.car_info.items():
            if value:  # Only include non-None values
                formatted_key = key.replace('_', ' ').title()
                if key == "post_link":
                    body += f"{formatted_key}:\n{value}\n\n"
                else:
                    body += f"{formatted_key}: {value}\n"
        body += "\n" + "=" * 40 + "\n"  # Separator line at the end
        body += "This is an automated notification. Please do not reply to this email."

        print("DEBUG: Email body constructed")
        print(f"DEBUG: Email body preview:\n{body[:500]}...")  # Print first 500 characters of the email body

        msg.attach(MIMEText(body, 'plain'))
       
        print("DEBUG: Attempting to connect to SMTP server")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("DEBUG: Connection to SMTP server established")
            server.starttls()
            print("DEBUG: TLS started")
            server.login(from_email, password)
            print("DEBUG: Logged in to SMTP server")
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            print("DEBUG: Email sent successfully")
        
        logger.info(f"Email notification sent to {to_email}")
        return {"message": "Email sent successfully"}
    except smtplib.SMTPAuthenticationError as e:
        print(f"DEBUG: SMTP Authentication Error: {str(e)}")
        logger.error(f"SMTP Authentication Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to authenticate with the SMTP server")
    except smtplib.SMTPException as e:
        print(f"DEBUG: SMTP Error: {str(e)}")
        logger.error(f"SMTP Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"SMTP Error: {str(e)}")
    except Exception as e:
        print(f"DEBUG: Unexpected error in send_email: {str(e)}")
        logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)