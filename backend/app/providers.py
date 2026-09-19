"""Four-digit codes are generated here, never by the client. Configure live providers."""
import os,smtplib,ssl
from email.message import EmailMessage
import httpx
from .config import OTP_MODE

def send_code(to,code):
    if OTP_MODE=='console':
        print(f'DEVELOPMENT OTP for {to}: {code}',flush=True)
        return
    if '@' in to:
        m=EmailMessage();m['Subject']='EscapeArrow verification code';m['From']=os.environ['SMTP_FROM'];m['To']=to
        m.set_content(f'Your EscapeArrow code is {code}. It expires in 5 minutes. Do not share it.')
        with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587')),timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context());smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(m)
    else:
        sid=os.environ['TWILIO_ACCOUNT_SID']
        r=httpx.post(f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',auth=(sid,os.environ['TWILIO_AUTH_TOKEN']),data={'To':to,'From':os.environ['TWILIO_FROM'],'Body':f'EscapeArrow code: {code}. Expires in 5 minutes.'},timeout=15)
        r.raise_for_status()
