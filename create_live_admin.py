import firebase_admin
from firebase_admin import credentials, auth
import sys

# 1. Initialize Firebase Admin
cred_path = r"C:\src\code8\slo-combine\code8-vue-app\service-account.json"
try:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"Failed to initialize Firebase Admin. Check your service account path.\n{e}")
    sys.exit(1)

email = "chrisw@code8training.com"
password = "Code8!"
name = "Chris White"

try:
    user = auth.create_user(email=email, password=password, display_name=name)
    auth.set_custom_user_claims(user.uid, {"role": "admin"})
    print(f"Successfully created Live Admin user: {email}")
except firebase_admin.auth.EmailAlreadyExistsError:
    user = auth.get_user_by_email(email)
    auth.set_custom_user_claims(user.uid, {"role": "admin"})
    print(f"User {email} already existed. Upgraded claims to Admin!")
except Exception as e:
    print(f"Error creating admin user: {e}")