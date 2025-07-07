# Setting Up PostgreSQL on Ubuntu

Installing and configuring a PostgreSQL database on Ubuntu (e.g., within WSL or a native environment).

## Step 1: Install PostgreSQL

The following instructions were taken from:
https://www.postgresql.org/download/linux/ubuntu/


```bash
sudo apt update
sudo apt install postgresql
```

## Step 2: Create a New Database

```bash
sudo -u postgres createdb summative
```

## Step 3: Create a New User and Password

Log into the PostgreSQL shell:

```bash
sudo -u postgres psql
```

Inside `psql`, run:

```sql
CREATE USER user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE summative TO user;
GRANT ALL ON SCHEMA public TO adam;
```

## Step 4: Configure PostgreSQL

The PostgreSQL config file can be edited with:

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

This allows changing the default port from `5432` and setting listen addresses.

## Step 5: Accessing PostgreSQL

The database can be viewed and accessed in [**HeidiSQL**](https://www.heidisql.com/) and entering the configuration details.


## Starting PostgreSQL

Use the following:

```bash
sudo systemctl start postgresql
```

Verify PostgreSQL is running:

```bash
sudo systemctl status postgresql
```