# PostgreSQL Docker Setup for Django Football App

This guide explains how to set up and use PostgreSQL with Docker for your Django football application.

## Prerequisites

- Docker and Docker Compose installed on your system
- Python virtual environment activated

## Setup Instructions

### 1. Install Dependencies

First, install the new Python dependencies:

```bash
pip install -r requirements.txt
```

### 2. Start PostgreSQL Container

Start the PostgreSQL container using Docker Compose:

```bash
docker-compose up -d
```

This will:
- Build the PostgreSQL container
- Start the database server
- Create the `football_stats` database
- Expose PostgreSQL on port 5432

### 3. Verify Container is Running

Check if the container is running:

```bash
docker ps
```

You should see a container named `football_postgres` running.

### 4. Run Django Migrations

Since you're switching from SQLite to PostgreSQL, you'll need to run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser (Optional)

Create a Django superuser:

```bash
python manage.py createsuperuser
```

### 6. Start Django Development Server

```bash
python manage.py runserver
```

## Database Configuration

The database configuration is stored in `database.env` and loaded by Django settings:

- **Database Name**: football_stats
- **Username**: football_user
- **Password**: football_password
- **Host**: localhost
- **Port**: 5432

## Useful Docker Commands

### Stop the Database
```bash
docker-compose down
```

### View Database Logs
```bash
docker-compose logs db
```

### Access PostgreSQL Shell
```bash
docker exec -it football_postgres psql -U football_user -d football_stats
```

### Remove Everything (including data)
```bash
docker-compose down -v
```

## Troubleshooting

1. **Port 5432 already in use**: Make sure no other PostgreSQL instance is running on port 5432
2. **Connection refused**: Ensure the Docker container is running with `docker ps`
3. **Permission denied**: Make sure your user has Docker permissions

## Data Persistence

The PostgreSQL data is persisted in a Docker volume named `postgres_data`. This means your data will survive container restarts. To completely remove all data, use `docker-compose down -v`.
