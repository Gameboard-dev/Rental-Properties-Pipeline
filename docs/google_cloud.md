

# Setting Up Google Cloud Translation API

This explains how to set up and use the Google Cloud Translation API to translate addresses in a pandas column Series.

---

The `googletrans` wrapper library while free and easy to setup, is unofficial. In testing, the official Google Cloud API was more accurate and reliable.

---

## Free Tier Eligibility

- The total number of characters in the unique addresses was **162,439**.
- Google Cloud Translation offers **500,000 characters/month** free.

---

## Setup

### 1. Create a Google Cloud Project

- Go to the [Google Cloud Console](https://console.cloud.google.com/)
- Click **"Select a project"** and **"New Project"**
- Give it a name and click **Create**

---

### 2. Link Billing Account

- Navigate to **Billing**
- Link an existing billing account or create a new one
- There are no charges on the free trial

---

### 3. Enable the Cloud Translation API

- Go to **APIs & Services > Library**
- Search for **"Cloud Translation API"**
- Click **Enable**

---

### 4. Create Credentials

- Go to **APIs & Services > Credentials**
- Click **"Create Credentials"** → **"Service Account"**
- Fill in a name and description
- Click **Create and Continue**
- On the final step, click **Done**

---

### 5. Generate a Service Account Key

- In **Service Accounts**, click your account
- Go to **"Keys"**
- Click **"Add Key"** → **"Create New Key"**
- Choose **JSON**.
- This will download a `.json` key file

---

### 6. Set the Environment Variable

The Google Cloud client library uses the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to locate your key file. This variable was added to the `.env` file which was secured using `.gitignore`.

---

## Cleanup

- Go to **Billing > Account Settings** and **close the billing account**
- Go to **IAM & Admin > Settings** and **delete the project**


