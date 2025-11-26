import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import config


class LoginAlertMailer:
    def __init__(self):
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port   = config.SMTP_PORT
        self.username    = config.SMTP_USERNAME
        self.password    = config.SMTP_PASSWORD

    def send_alert(self, to_email):
        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        body = f"""
                Hello,

                A login to your Honeycomb account was detected on:
                {login_time}

                If this was you, no action is required.
                If not, please reset your password immediately.

                Regards,
                Honeycomb Security Team
                """

        msg = MIMEText(body)
        msg["Subject"] = "LOGIN ALERT - Honeycomb Platform"
        msg["From"] = self.username
        msg["To"] = to_email

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)

        print("LOGIN ALERT sent")

    def send_password_reset(self, to_email, reset_link):
            body = f"""
                    Hello,

                    We received a request to reset your Honeycomb account password.

                    Click the link below to reset your password:
                    {reset_link}

                    If you did not request this, you can safely ignore this email.

                    Regards,
                    Honeycomb Security Team
                    """

            msg = MIMEText(body)
            msg["Subject"] = "Honeycomb Password Reset"
            msg["From"] = self.username
            msg["To"] = to_email

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            print("PASSWORD RESET EMAIL sent")
            
    def send_mfa_reset(self, to_email, reset_link):
            body = f"""
                    Hello,

                    We received a request to reset your Honeycomb account MFA settings.

                    Click the link below to reset your MFA:
                    {reset_link}

                    If you did not request this, you can safely ignore this email.

                    Regards,
                    Honeycomb Security Team
                    """

            msg = MIMEText(body)
            msg["Subject"] = "Honeycomb MFA Reset"
            msg["From"] = self.username
            msg["To"] = to_email

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            print("MFA RESET EMAIL sent")

# test the functionality
if __name__ == "__main__":
    
    mailer_system = LoginAlertMailer()
    mailer_system.send_alert("akhilesh@meridiandatalabs.com")
    mailer_system.send_password_reset(
        "akhilesh@meridiandatalabs.com",
        "https://your-frontend.com/reset-password?token=TEST"
    )
    mailer_system.send_mfa_reset(
        "akhilesh@meridiandatalabs.com",
        "https://your-frontend.com/reset-mfa?token=TEST"
    )